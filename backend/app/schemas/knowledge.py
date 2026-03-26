from pydantic import BaseModel
from typing import Optional


class AddTextRequest(BaseModel):
    content: str
    title: Optional[str] = None


class DocumentInfo(BaseModel):
    doc_id: str
    title: str
    source_type: str  # "text" | "pdf" | "file"
    created_at: str
    chunk_count: int


class DocumentListResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


class DocumentContent(BaseModel):
    doc_id: str
    title: str
    source_type: str
    content: str
    created_at: str


class PreviewResponse(BaseModel):
    title: str
    source_type: str
    content: str
    estimated_chunks: int
    char_count: int


class ReindexResponse(BaseModel):
    reindexed_count: int
    message: str
