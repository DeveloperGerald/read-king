from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.agents.workflow import expand_report_from_prompt
from app.agents.workflow import run_report_workflow
from app.agents.workflow import build_prompt_preview
from app.core.config import Settings
from app.services.file_service import ensure_storage_dirs


@dataclass(frozen=True)
class ReportStatus:
    book_id: str
    status: str
    updated_at: str
    error: str | None = None
    report_path: str | None = None
    outline_path: str | None = None


# 获取当前 UTC 时间的 ISO 字符串（用于状态落盘）
def _now_iso() -> str:
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
    if not p.exists():
        report_path = _report_path(settings, book_id)
        outline_path = _outline_path(settings, book_id)
        if report_path.exists() or outline_path.exists():
            status = ReportStatus(
                book_id=book_id,
                status="completed" if report_path.exists() else "outlined",
                updated_at=_now_iso(),
                report_path=str(report_path) if report_path.exists() else None,
                outline_path=str(outline_path) if outline_path.exists() else None,
            )
            _write_report_status(settings, status)
            return status
        return ReportStatus(book_id=book_id, status="none", updated_at=_now_iso())

    data = json.loads(p.read_text("utf-8"))
    status = ReportStatus(
        book_id=data.get("book_id", book_id),
        status=data.get("status", "unknown"),
        updated_at=data.get("updated_at", _now_iso()),
        error=data.get("error"),
        report_path=data.get("report_path"),
        outline_path=data.get("outline_path"),
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
            updated_at=_now_iso(),
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
            _write_report_status(settings, reconciled)
            return reconciled

    return status


def _write_report_status(settings: Settings, status: ReportStatus) -> None:
    ensure_storage_dirs(settings)
    p = _status_path(settings, status.book_id)
    payload = {
        "book_id": status.book_id,
        "status": status.status,
        "updated_at": status.updated_at,
        "error": status.error,
        "report_path": status.report_path,
        "outline_path": status.outline_path,
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


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

    if force:
        _safe_unlink(_report_path(settings, book_id))
        _safe_unlink(_outline_path(settings, book_id))
        _safe_unlink(_status_path(settings, book_id))

    running = ReportStatus(book_id=book_id, status="generating", updated_at=_now_iso())
    _write_report_status(settings, running)

    outline_path: Path | None = None

    try:
        out = run_report_workflow(
            settings=settings,
            book_id=book_id,
            user_requirements=user_requirements,
            user_feelings=user_feelings,
            mode="report",
        )
        if out.get("status") != "completed":
            raise RuntimeError(out.get("error") or "workflow failed")

        outline_md = out.get("outline_markdown")
        if isinstance(outline_md, str) and outline_md.strip():
            outline_path = _outline_path(settings, book_id)
            outline_path.write_text(outline_md, encoding="utf-8")

        md = out.get("report_markdown")
        if not isinstance(md, str) or not md.strip():
            prompt = out.get("prompt")
            if not isinstance(prompt, str) or not prompt.strip():
                preview = build_prompt_preview(
                    settings=settings,
                    book_id=book_id,
                    user_requirements=user_requirements,
                    user_feelings=user_feelings,
                )
                prompt = preview.get("prompt", "")

            outline_json = out.get("outline_json")
            if not isinstance(outline_json, dict):
                outline_json = None

            try:
                md = expand_report_from_prompt(
                    settings=settings,
                    prompt=prompt,
                    outline_markdown=str(outline_md or ""),
                    outline_json=outline_json,
                    max_attempts=3,
                )
            except Exception:
                raise RuntimeError("empty report_markdown")

        report_path = _report_path(settings, book_id)
        report_path.write_text(md, encoding="utf-8")

        done = ReportStatus(
            book_id=book_id,
            status="completed",
            updated_at=_now_iso(),
            report_path=str(report_path),
            outline_path=str(outline_path) if outline_path else None,
        )
        _write_report_status(settings, done)
        return done
    except Exception as e:  # noqa: BLE001
        failed = ReportStatus(
            book_id=book_id,
            status="failed",
            updated_at=_now_iso(),
            error=str(e),
            outline_path=str(outline_path) if outline_path else None,
        )
        _write_report_status(settings, failed)
        return failed


# 删除指定 book_id 的报告文件与状态
def delete_report(settings: Settings, book_id: str) -> None:
    _safe_unlink(_report_path(settings, book_id))
    _safe_unlink(_outline_path(settings, book_id))
    _safe_unlink(_status_path(settings, book_id))
