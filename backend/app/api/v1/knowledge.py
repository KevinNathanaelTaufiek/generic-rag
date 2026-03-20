from fastapi import APIRouter, UploadFile, File, HTTPException

from app.schemas.knowledge import (
    AddTextRequest,
    DocumentInfo,
    DocumentListResponse,
    ReindexResponse,
)
from app.services import ingestion, retrieval

router = APIRouter(prefix="/knowledge", tags=["knowledge"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


@router.post("/text", response_model=DocumentInfo)
def add_text(body: AddTextRequest):
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty.")

    result = ingestion.ingest_text(body.content, body.title)
    docs = retrieval.list_documents()
    doc = next((d for d in docs if d.doc_id == result["doc_id"]), None)

    if not doc:
        # Build a minimal response if not found immediately (edge case)
        from datetime import datetime, timezone
        doc = DocumentInfo(
            doc_id=result["doc_id"],
            title=result["title"],
            source_type="text",
            created_at=datetime.now(timezone.utc).isoformat(),
            chunk_count=result["chunk_count"],
        )
    return doc


@router.post("/upload", response_model=DocumentInfo)
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()

    if ext == ".pdf":
        import io
        result = ingestion.ingest_pdf(io.BytesIO(content), filename)
    else:
        result = ingestion.ingest_text_file(content, filename)

    docs = retrieval.list_documents()
    doc = next((d for d in docs if d.doc_id == result["doc_id"]), None)

    if not doc:
        from datetime import datetime, timezone
        doc = DocumentInfo(
            doc_id=result["doc_id"],
            title=result["title"],
            source_type="pdf" if ext == ".pdf" else "file",
            created_at=datetime.now(timezone.utc).isoformat(),
            chunk_count=result["chunk_count"],
        )
    return doc


@router.get("", response_model=DocumentListResponse)
def list_documents():
    docs = retrieval.list_documents()
    return DocumentListResponse(documents=docs, total=len(docs))


@router.delete("/{doc_id}")
def delete_document(doc_id: str):
    found = retrieval.delete_document(doc_id)
    if not found:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"detail": "Document deleted successfully."}


@router.post("/reindex", response_model=ReindexResponse)
def reindex():
    count = ingestion.reindex_all()
    return ReindexResponse(
        reindexed_count=count,
        message=f"Reindexed {count} chunks with provider '{__import__('app.config', fromlist=['settings']).settings.embedding_provider}'.",
    )
