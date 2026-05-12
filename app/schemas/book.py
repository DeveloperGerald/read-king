from __future__ import annotations

from pydantic import BaseModel


class UploadBookResponse(BaseModel):
    book_id: str
    original_filename: str
    stored_filename: str
    stored_path: str
    content_type: str | None = None
    status: str = "uploaded"


class ExtractTextResponse(BaseModel):
    book_id: str
    file_type: str
    char_count: int
    line_count: int
    preview: str


class ChunkPreviewItem(BaseModel):
    index: int
    chunk_id: str
    char_count: int
    head: str
    tail: str


class ChunkPreviewResponse(BaseModel):
    book_id: str
    file_type: str
    total_chunks: int
    max_chars: int
    overlap_chars: int
    items: list[ChunkPreviewItem]


class IndexStatusResponse(BaseModel):
    book_id: str
    status: str
    updated_at: str
    total_chars: int | None = None
    total_chunks: int | None = None
    error: str | None = None


class GenerateReportRequest(BaseModel):
    user_requirements: str | None = None
    user_feelings: str | None = None
    report_style: str | None = "读书博主风"


class ReportStatusResponse(BaseModel):
    book_id: str
    status: str
    updated_at: str
    error: str | None = None
    report_path: str | None = None
    outline_path: str | None = None
    current_step: str | None = None
    total_steps: int | None = None
    completed_steps: int | None = None


class BookMetaItem(BaseModel):
    book_id: str
    title: str | None = None
    author: str | None = None
    original_filename: str | None = None
    created_at: str | None = None


class BookListResponse(BaseModel):
    items: list[BookMetaItem]
    total: int
