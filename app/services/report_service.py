from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.agents.workflow import run_report_workflow
from app.agents.workflow import build_prompt_preview
from app.agents.agentic_workflow import run_agent_report_workflow
from app.core.config import Settings
from app.services.file_service import ensure_storage_dirs


logger = logging.getLogger(__name__)
_status_lock = threading.Lock()


@dataclass(frozen=True)
class ReportStatus:
    book_id: str
    status: str
    updated_at: str
    error: str | None = None
    report_path: str | None = None
    outline_path: str | None = None
    current_step: str | None = None
    total_steps: int = 7  # 默认 7 个步骤
    completed_steps: int = 0


# 获取当前 UTC 时间的 ISO 字符串（用于状态落盘）
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# 获取状态文件路径（每本书一个 json）
def _status_path(settings: Settings, book_id: str) -> Path:
    return settings.report_status_dir / f"{book_id}.json"


# 获取报告 markdown 落盘路径（每本书一个 md）
def _report_path(settings: Settings, book_id: str) -> Path:
    return settings.report_dir / f"{book_id}.md"


# 获取报告大纲 markdown 落盘路径（每本书一个 outline md）
def _outline_path(settings: Settings, book_id: str) -> Path:
    return settings.report_dir / f"{book_id}.outline.md"


def _safe_unlink(p: Path) -> None:
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass


def _looks_like_full_report(md: str) -> bool:
    s = (md or "").strip()
    if len(s) < 1200:
        return False
    if s.count("\n") < 40:
        return False
    return "##" in s or "###" in s


# 读取报告生成状态（不存在则返回 none）
def get_report_status(settings: Settings, book_id: str) -> ReportStatus:
    ensure_storage_dirs(settings)
    p = _status_path(settings, book_id)
    
    with _status_lock:
        if not p.exists():
            report_path = _report_path(settings, book_id)
            outline_path = _outline_path(settings, book_id)
            if report_path.exists() or outline_path.exists():
                status = ReportStatus(
                    book_id=book_id,
                    status="completed" if report_path.exists() else "outlined",
                    updated_at=now_iso(),
                    report_path=str(report_path) if report_path.exists() else None,
                    outline_path=str(outline_path) if outline_path.exists() else None,
                )
                # 注意：update_report_status 内部也会拿锁，但在同一个线程中重入 threading.Lock 会死锁
                # 所以我们这里直接写文件逻辑，或者将 update_report_status 拆分
                _do_update_report_status(settings, status)
                return status
            return ReportStatus(book_id=book_id, status="none", updated_at=now_iso())

        try:
            content = p.read_text("utf-8").strip()
            if not content:
                 return ReportStatus(book_id=book_id, status="none", updated_at=now_iso())
            data = json.loads(content)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to parse status file for {book_id}: {e}")
            # 如果解析失败，可能是并发写入导致的损坏，尝试从文件系统现状恢复一个基础状态
            return ReportStatus(book_id=book_id, status="generating", updated_at=now_iso())

    status = ReportStatus(
        book_id=data.get("book_id", book_id),
        status=data.get("status", "unknown"),
        updated_at=data.get("updated_at", now_iso()),
        error=data.get("error"),
        report_path=data.get("report_path"),
        outline_path=data.get("outline_path"),
        current_step=data.get("current_step"),
        total_steps=data.get("total_steps", 7),
        completed_steps=data.get("completed_steps", 0),
    )

    report_path = Path(status.report_path) if status.report_path else _report_path(settings, book_id)
    outline_path = Path(status.outline_path) if status.outline_path else _outline_path(settings, book_id)

    report_exists = report_path.exists()
    outline_exists = outline_path.exists()
    if report_exists or outline_exists:
        next_status = status.status
        next_error = status.error

        if report_exists and status.status in {"failed", "generating", "outlined"}:
            try:
                report_text = report_path.read_text("utf-8")
                if len((report_text or "").strip()) >= 200:
                    next_status = "completed"
                    next_error = None
                elif _looks_like_full_report(report_text):
                    next_status = "completed"
                    next_error = None
            except Exception:
                pass

        if status.status == "failed" and status.error == "empty report_markdown":
            if not report_exists and outline_exists and _looks_like_full_report(outline_path.read_text("utf-8")):
                try:
                    report_path.write_text(outline_path.read_text("utf-8"), encoding="utf-8")
                    report_exists = report_path.exists()
                except Exception:
                    pass

            if report_exists:
                next_status = "completed"
                next_error = None

        reconciled = ReportStatus(
            book_id=book_id,
            status=next_status,
            updated_at=now_iso(),
            error=next_error,
            report_path=str(report_path) if report_exists else None,
            outline_path=str(outline_path) if outline_exists else None,
        )
        if (
            reconciled.status != status.status
            or reconciled.error != status.error
            or reconciled.report_path != status.report_path
            or reconciled.outline_path != status.outline_path
        ):
            update_report_status(settings, reconciled)
            return reconciled

    return status


# 更新报告生成状态并落盘（内部实现，不带锁）
def _do_update_report_status(settings: Settings, status: ReportStatus) -> None:
    ensure_storage_dirs(settings)
    p = _status_path(settings, status.book_id)
    payload = {
        "book_id": status.book_id,
        "status": status.status,
        "updated_at": status.updated_at,
        "error": status.error,
        "report_path": status.report_path,
        "outline_path": status.outline_path,
        "current_step": status.current_step,
        "total_steps": status.total_steps,
        "completed_steps": status.completed_steps,
    }
    # 使用临时文件 + rename 实现原子写入，防止读取到中间状态
    tmp_p = p.with_suffix(".tmp")
    tmp_p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp_p.replace(p)


# 更新报告生成状态并落盘
def update_report_status(settings: Settings, status: ReportStatus) -> None:
    with _status_lock:
        _do_update_report_status(settings, status)


# 更新进度信息
def update_report_progress(
    settings: Settings,
    book_id: str,
    current_step: str,
    completed_steps: int,
    total_steps: int = 7,
) -> None:
    status = get_report_status(settings, book_id)
    new_status = ReportStatus(
        book_id=book_id,
        status=status.status,
        updated_at=now_iso(),
        error=status.error,
        report_path=status.report_path,
        outline_path=status.outline_path,
        current_step=current_step,
        completed_steps=completed_steps,
        total_steps=total_steps,
    )
    update_report_status(settings, new_status)


import re

# 清理 LLM 输出的 Markdown 内容
def clean_markdown(content: str) -> str:
    if not content:
        return ""
    # 去除开头的 ```markdown 或 ```
    content = re.sub(r"^```markdown\n?", "", content, flags=re.IGNORECASE)
    content = re.sub(r"^```\n?", "", content)
    # 去除结尾的 ```
    content = re.sub(r"\n?```$", "", content)
    # 去除结尾常见的 LLM 废话
    content = re.sub(r"\n?请确认是否满意.*$", "", content, flags=re.DOTALL)
    content = re.sub(r"\n?确认是否满意.*$", "", content, flags=re.DOTALL)
    return content.strip()


# 生成读书报告：运行 LangGraph 工作流并将 markdown 落盘
def generate_report(
    settings: Settings,
    *,
    book_id: str,
    user_requirements: str | None = None,
    user_feelings: str | None = None,
    force: bool = False,
) -> ReportStatus:
    ensure_storage_dirs(settings)
    logger.info(f"Starting report generation for book {book_id} (force={force})")

    if force:
        _safe_unlink(_report_path(settings, book_id))
        _safe_unlink(_outline_path(settings, book_id))
        _safe_unlink(_status_path(settings, book_id))

    running = ReportStatus(
        book_id=book_id,
        status="generating",
        updated_at=now_iso(),
        current_step="准备生成环境...",
        completed_steps=0,
        total_steps=7,
    )
    update_report_status(settings, running)

    outline_path: Path | None = None

    try:
        # 定义进度回调
        def on_workflow_progress(step: str, completed: int):
            update_report_progress(settings, book_id, step, completed)

        # 使用新的 Agentic 工作流
        logger.info(f"Running agentic workflow for book {book_id}")
        out = run_agent_report_workflow(
            settings=settings,
            book_id=book_id,
            user_requirements=user_requirements,
            user_feelings=user_feelings,
            mode="report",
            on_progress=on_workflow_progress,
        )
        logger.info(f"Workflow finished for book {book_id} with status: {out.get('status')}")

        if out.get("status") != "completed":
            workflow_error = out.get("error")
            status = out.get("status")
            raise RuntimeError(f"Workflow failed with status [{status}]: {workflow_error or 'no error message'}")

        outline_md = out.get("outline_markdown")
        if isinstance(outline_md, str) and outline_md.strip():
            outline_md = clean_markdown(outline_md)
            outline_path = _outline_path(settings, book_id)
            outline_path.write_text(outline_md, encoding="utf-8")
            logger.info(f"Outline saved to {outline_path}")

        # 根据模式验证并获取结果
        mode = out.get("workflow_mode", "report")
        if mode == "outline":
            md = out.get("outline_markdown")
            error_msg = "empty outline_markdown from agentic workflow"
        else:
            md = out.get("report_markdown")
            error_msg = "empty report_markdown from agentic workflow"

        if not isinstance(md, str) or not md.strip():
            raise RuntimeError(error_msg)

        md = clean_markdown(md)

        report_path_str: str | None = None
        if mode == "report":
            report_path = _report_path(settings, book_id)
            report_path.write_text(md, encoding="utf-8")
            report_path_str = str(report_path)
            logger.info(f"Report saved to {report_path}")

        done = ReportStatus(
            book_id=book_id,
            status="completed" if mode == "report" else "outlined",
            updated_at=now_iso(),
            report_path=report_path_str,
            outline_path=str(outline_path) if outline_path else None,
            current_step="生成完成" if mode == "report" else "大纲生成完成",
            completed_steps=7,
            total_steps=7,
        )
        update_report_status(settings, done)
        logger.info(f"Report generation completed for book {book_id}")
        return done
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Exception occurred during report generation for book {book_id}")
        last_status = get_report_status(settings, book_id)
        failed = ReportStatus(
            book_id=book_id,
            status="failed",
            updated_at=now_iso(),
            error=str(e),
            report_path=last_status.report_path,
            outline_path=str(outline_path) if outline_path else last_status.outline_path,
            current_step=last_status.current_step,
            completed_steps=last_status.completed_steps,
            total_steps=last_status.total_steps,
        )
        update_report_status(settings, failed)
        return failed


# 删除指定 book_id 的报告文件与状态
def delete_report(settings: Settings, book_id: str) -> None:
    _safe_unlink(_report_path(settings, book_id))
    _safe_unlink(_outline_path(settings, book_id))
    with _status_lock:
        _safe_unlink(_status_path(settings, book_id))
