from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, UploadFile, File
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.schemas.knowledge import (
    AddTextRequest,
    DocumentContent,
    DocumentInfo,
    DocumentListResponse,
    PreviewResponse,
    ReindexResponse,
)
from app.services import ingestion, retrieval, audit as audit_svc

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


def _estimate_chunks(text: str) -> int:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    return len(splitter.split_text(text))


def _get_username(x_username: str = Header(default="anonymous")) -> str:
    return x_username


@router.post("/preview/text", response_model=PreviewResponse)
def preview_text(body: AddTextRequest):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")
    content = body.content
    title = body.title or "Text"
    return PreviewResponse(
        title=title,
        source_type="text",
        content=content,
        estimated_chunks=_estimate_chunks(content),
        char_count=len(content),
    )


@router.post("/preview/upload", response_model=PreviewResponse)
async def preview_upload(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content_bytes = await file.read()
    try:
        content, title, source_type = ingestion.extract_file(content_bytes, filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return PreviewResponse(
        title=title,
        source_type=source_type,
        content=content,
        estimated_chunks=_estimate_chunks(content),
        char_count=len(content),
    )


@router.post("/text", response_model=DocumentInfo)
def add_text(body: AddTextRequest, x_username: str = Header(default="anonymous")):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")

    result = ingestion.ingest_text(body.content, body.title)
    docs = retrieval.list_documents()
    doc = next((d for d in docs if d.doc_id == result["doc_id"]), None)

    created_at = datetime.now(timezone.utc).isoformat()
    if not doc:
        doc = DocumentInfo(
            doc_id=result["doc_id"],
            title=result["title"],
            source_type="text",
            created_at=created_at,
            chunk_count=result["chunk_count"],
        )
    else:
        created_at = doc.created_at

    audit_svc.log_knowledge_action(
        username=x_username,
        action="knowledge.add",
        doc_id=result["doc_id"],
        title=result["title"],
        source_type="text",
        chunk_count=result["chunk_count"],
        created_at=created_at,
        content=result["content"],
    )

    return doc


@router.post("/upload", response_model=DocumentInfo)
async def upload_file(file: UploadFile = File(...), x_username: str = Header(default="anonymous")):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    result = ingestion.ingest_file(content, filename)
    source_type = result["source_type"]

    docs = retrieval.list_documents()
    doc = next((d for d in docs if d.doc_id == result["doc_id"]), None)

    created_at = datetime.now(timezone.utc).isoformat()
    if not doc:
        doc = DocumentInfo(
            doc_id=result["doc_id"],
            title=result["title"],
            source_type=source_type,
            created_at=created_at,
            chunk_count=result["chunk_count"],
        )
    else:
        created_at = doc.created_at

    audit_svc.log_knowledge_action(
        username=x_username,
        action="knowledge.add",
        doc_id=result["doc_id"],
        title=result["title"],
        source_type=source_type,
        chunk_count=result["chunk_count"],
        created_at=created_at,
        content=result["content"],
    )

    return doc


@router.get("", response_model=DocumentListResponse)
def list_documents():
    docs = retrieval.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{doc_id}/content", response_model=DocumentContent)
def get_document_content(doc_id: str):
    data = audit_svc.get_knowledge_content(doc_id)
    if not data:
        raise HTTPException(status_code=404, detail="Content not found.")
    return DocumentContent(**data)


@router.delete("/{doc_id}")
def delete_document(doc_id: str, x_username: str = Header(default="anonymous")):
    # Fetch metadata before deletion for audit
    docs = retrieval.list_documents()
    doc = next((d for d in docs if d.doc_id == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    found = retrieval.delete_document(doc_id)
    if not found:
        raise HTTPException(status_code=404, detail="Document not found.")

    audit_svc.log_knowledge_action(
        username=x_username,
        action="knowledge.delete",
        doc_id=doc_id,
        title=doc.title,
        source_type=doc.source_type,
        chunk_count=doc.chunk_count,
        created_at=doc.created_at,
        content="",  # content already in knowledge_content table from when it was added
    )

    return {"detail": "Document deleted successfully."}


@router.post("/reindex", response_model=ReindexResponse)
def reindex():
    count = ingestion.reindex_all()
    return ReindexResponse(
        reindexed_count=count,
        message=f"Reindexed {count} chunks with provider '{settings.embedding_provider}'.",
    )
