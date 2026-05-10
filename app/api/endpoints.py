from __future__ import annotations

from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Depends
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from fastapi import Query
from fastapi.responses import PlainTextResponse

from pathlib import Path
from fastapi import UploadFile

from app.core.config import Settings
from app.core.config import get_settings
from app.schemas.book import UploadBookResponse
from app.schemas.book import ExtractTextResponse
from app.schemas.book import ChunkPreviewItem
from app.schemas.book import ChunkPreviewResponse
from app.schemas.book import IndexStatusResponse
from app.schemas.book import GenerateReportRequest
from app.schemas.book import ReportStatusResponse
from app.schemas.book import BookListResponse
from app.schemas.book import BookMetaItem
from app.services.book_meta_service import save_book_meta
from app.services.book_meta_service import list_books
from app.services.book_meta_service import get_book_meta
from app.services.book_meta_service import delete_book_meta
from app.services.file_service import find_uploaded_file
from app.services.file_service import save_upload_file
from app.services.file_service import delete_uploaded_file
from app.services.index_service import build_book_index
from app.services.index_service import get_index_status
from app.services.index_service import delete_index
from app.services.index_service import update_index_status, IndexStatus, now_iso
from app.services.report_service import generate_report
from app.services.report_service import get_report_status
from app.services.report_service import delete_report
from app.services.text_extraction import extract_text
from app.rag.chunking import chunk_text
from app.agents.workflow import build_prompt_preview
from app.agents.workflow import run_report_workflow


router = APIRouter(prefix="/api")


# 上传电子书文件到本地存储，返回 book_id 与落盘信息
@router.post("/upload", response_model=UploadBookResponse)
def upload_book(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    author: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
) -> UploadBookResponse:
    try:
        book_id, stored_filename, stored_path = save_upload_file(settings, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    save_book_meta(
        settings,
        book_id=book_id,
        title=title,
        author=author,
        original_filename=file.filename,
    )

    stored_path_str = str(stored_path)
    return UploadBookResponse(
        book_id=book_id,
        original_filename=file.filename or "",
        stored_filename=stored_filename,
        stored_path=stored_path_str,
        content_type=file.content_type,
    )


# 获取所有已上传书籍的元数据列表
@router.get("/books", response_model=BookListResponse)
def get_books(
    settings: Settings = Depends(get_settings),
) -> BookListResponse:
    books = list_books(settings)
    items = [
        BookMetaItem(
            book_id=b.book_id,
            title=b.title,
            author=b.author,
            original_filename=b.original_filename,
            created_at=b.created_at,
        )
        for b in books
    ]
    return BookListResponse(items=items, total=len(items))


# 获取特定书籍的元数据
@router.get("/books/{book_id}/meta", response_model=BookMetaItem)
def get_book_metadata(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> BookMetaItem:
    meta = get_book_meta(settings, book_id)
    return BookMetaItem(
        book_id=meta.book_id,
        title=meta.title,
        author=meta.author,
        original_filename=meta.original_filename,
        created_at=meta.created_at,
    )


# 删除书籍及其关联的所有数据（原文件、索引、元数据、报告）
@router.delete("/books/{book_id}")
def delete_book(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    delete_uploaded_file(settings, book_id)
    delete_index(settings, book_id)
    delete_report(settings, book_id)
    delete_book_meta(settings, book_id)
    return {"status": "ok", "message": f"book {book_id} deleted"}


# 抽取并清洗已上传书籍的全文，返回统计信息与预览
# @router.get("/books/{book_id}/text", response_model=ExtractTextResponse)
# def get_book_text(
#     book_id: str,
#     preview_chars: int = 1500,
#     settings: Settings = Depends(get_settings),
# ) -> ExtractTextResponse:
#     path = find_uploaded_file(settings, book_id)
#     if path is None:
#         raise HTTPException(status_code=404, detail="book not found")

#     try:
#         extracted = extract_text(path)
#     except RuntimeError as e:
#         raise HTTPException(status_code=500, detail=str(e)) from e
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e)) from e

#     preview = extracted.text[: max(0, preview_chars)]
#     return ExtractTextResponse(
#         book_id=book_id,
#         file_type=extracted.file_type,
#         char_count=extracted.char_count,
#         line_count=extracted.line_count,
#         preview=preview,
#     )


# 预览分块结果：返回总 chunk 数与前 N 个 chunk 的头尾片段
# @router.get("/books/{book_id}/chunks", response_model=ChunkPreviewResponse)
# def preview_book_chunks(
#     book_id: str,
#     max_chars: int = 1200,
#     overlap_chars: int = 120,
#     limit: int = 5,
#     head_chars: int = 140,
#     tail_chars: int = 140,
#     settings: Settings = Depends(get_settings),
# ) -> ChunkPreviewResponse:
#     if limit < 1:
#         raise HTTPException(status_code=400, detail="limit must be >= 1")
#     if limit > 50:
#         raise HTTPException(status_code=400, detail="limit must be <= 50")

#     path = find_uploaded_file(settings, book_id)
#     if path is None:
#         raise HTTPException(status_code=404, detail="book not found")

#     try:
#         extracted = extract_text(path)
#         chunks = chunk_text(extracted.text, max_chars=max_chars, overlap_chars=overlap_chars)
#     except RuntimeError as e:
#         raise HTTPException(status_code=500, detail=str(e)) from e
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e)) from e

#     items: list[ChunkPreviewItem] = []
#     for c in chunks[:limit]:
#         t = c.text
#         items.append(
#             ChunkPreviewItem(
#                 index=c.index,
#                 chunk_id=c.chunk_id,
#                 char_count=len(t),
#                 head=t[: max(0, head_chars)],
#                 tail=t[-max(0, tail_chars) :] if tail_chars > 0 else "",
#             )
#         )

#     return ChunkPreviewResponse(
#         book_id=book_id,
#         file_type=extracted.file_type,
#         total_chunks=len(chunks),
#         max_chars=max_chars,
#         overlap_chars=overlap_chars,
#         items=items,
#     )


# 启动索引构建任务（抽取→分块→写入 Chroma），后台执行
@router.post("/books/{book_id}/index", response_model=IndexStatusResponse)
def start_book_index(
    book_id: str,
    background_tasks: BackgroundTasks,
    max_chars: int = 1200,
    overlap_chars: int = 120,
    settings: Settings = Depends(get_settings),
) -> IndexStatusResponse:
    # 立即同步更新状态为 indexing，防止旧状态干扰接口返回
    status = IndexStatus(book_id=book_id, status="indexing", updated_at=now_iso())
    update_index_status(settings, status)

    background_tasks.add_task(
        build_book_index,
        settings,
        book_id=book_id,
        max_chars=max_chars,
        overlap_chars=overlap_chars,
    )
    return IndexStatusResponse(**status.__dict__)


# 查询索引构建状态
@router.get("/books/{book_id}/index/status", response_model=IndexStatusResponse)
def read_book_index_status(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> IndexStatusResponse:
    status = get_index_status(settings, book_id)
    return IndexStatusResponse(**status.__dict__)


# 启动读书报告生成任务（LangGraph 工作流 + Ollama），后台执行并落盘
@router.post("/books/{book_id}/report", response_model=ReportStatusResponse)
def start_report_generation(
    book_id: str,
    body: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    force: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> ReportStatusResponse:
    background_tasks.add_task(
        generate_report,
        settings,
        book_id=book_id,
        user_requirements=body.user_requirements,
        user_feelings=body.user_feelings,
        force=force,
    )
    status = get_report_status(settings, book_id)
    return ReportStatusResponse(**status.__dict__)


# 删除指定书籍的报告文件与状态
@router.delete("/books/{book_id}/report")
def delete_book_report(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    delete_report(settings, book_id)
    return {"status": "ok", "message": f"report for book {book_id} deleted"}


@router.post("/books/{book_id}/report/regenerate", response_model=ReportStatusResponse)
def regenerate_report(
    book_id: str,
    body: GenerateReportRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> ReportStatusResponse:
    background_tasks.add_task(
        generate_report,
        settings,
        book_id=book_id,
        user_requirements=body.user_requirements,
        user_feelings=body.user_feelings,
        force=True,
    )
    status = get_report_status(settings, book_id)
    return ReportStatusResponse(**status.__dict__)


# 查询读书报告生成状态
@router.get("/books/{book_id}/report/status", response_model=ReportStatusResponse)
def read_report_status(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> ReportStatusResponse:
    status = get_report_status(settings, book_id)
    return ReportStatusResponse(**status.__dict__)


# 获取已生成报告的 Markdown 文件内容
@router.get("/books/{book_id}/report/file", response_class=PlainTextResponse)
def read_report_file(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    status = get_report_status(settings, book_id)
    p = Path(status.report_path) if status.report_path else None
    if p is None or not p.exists():
        raise HTTPException(status_code=404, detail="report not found")
    return PlainTextResponse(p.read_text("utf-8"))


# 获取已生成报告大纲的 Markdown 文件内容
@router.get("/books/{book_id}/report/outline", response_class=PlainTextResponse)
def read_report_outline_file(
    book_id: str,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    status = get_report_status(settings, book_id)
    if not status.outline_path:
        raise HTTPException(status_code=404, detail="outline not found")
    p = Path(status.outline_path)
    if not p.exists():
        raise HTTPException(status_code=404, detail="outline file not found")
    return PlainTextResponse(p.read_text("utf-8"))


# 预览工作流抽取到的 context（不调用 LLM）
@router.post("/books/{book_id}/workflow/context", response_class=PlainTextResponse)
def preview_workflow_context(
    book_id: str,
    body: GenerateReportRequest,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    out = run_report_workflow(
        settings=settings,
        book_id=book_id,
        user_requirements=body.user_requirements,
        user_feelings=body.user_feelings,
        mode="context",
    )
    if out.get("status") != "context_ready":
        err = out.get("error") or "workflow context failed"
        if err == "book not found":
            raise HTTPException(status_code=404, detail=err)
        raise HTTPException(status_code=500, detail=err)
    return PlainTextResponse(out.get("context") or "")


# 预览最终 prompt（包含 external_info + context，不调用 LLM）
@router.post("/books/{book_id}/workflow/prompt", response_class=PlainTextResponse)
def preview_workflow_prompt(
    book_id: str,
    body: GenerateReportRequest,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    try:
        preview = build_prompt_preview(
            settings=settings,
            book_id=book_id,
            user_requirements=body.user_requirements,
            user_feelings=body.user_feelings,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e
    return PlainTextResponse(preview.get("prompt", ""))


# 生成并返回大纲（调用 LLM，仅输出 outline，不扩写正文）
@router.post("/books/{book_id}/workflow/outline", response_class=PlainTextResponse)
def generate_outline_only(
    book_id: str,
    body: GenerateReportRequest,
    settings: Settings = Depends(get_settings),
) -> PlainTextResponse:
    out = run_report_workflow(
        settings=settings,
        book_id=book_id,
        user_requirements=body.user_requirements,
        user_feelings=body.user_feelings,
        mode="outline",
    )
    if out.get("status") != "outlined":
        raise HTTPException(status_code=500, detail=out.get("error") or "workflow outline failed")
    return PlainTextResponse(out.get("outline_markdown") or "")
