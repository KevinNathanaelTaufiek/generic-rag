import uuid
from datetime import datetime, timezone
from typing import BinaryIO

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.core.vectorstore import get_vectorstore


def _make_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
    )


def _ingest_documents(docs: list[Document], doc_id: str, title: str, source_type: str) -> int:
    splitter = _make_splitter()
    chunks = splitter.split_documents(docs)

    created_at = datetime.now(timezone.utc).isoformat()
    for i, chunk in enumerate(chunks):
        chunk.metadata.update({
            "doc_id": doc_id,
            "title": title,
            "source_type": source_type,
            "created_at": created_at,
            "chunk_index": i,
        })

    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    return len(chunks)


def ingest_text(content: str, title: str | None = None) -> dict:
    doc_id = str(uuid.uuid4())
    title = title or f"Text {doc_id[:8]}"

    docs = [Document(page_content=content, metadata={})]
    chunk_count = _ingest_documents(docs, doc_id, title, "text")

    return {"doc_id": doc_id, "title": title, "chunk_count": chunk_count}


def ingest_pdf(file: BinaryIO, filename: str) -> dict:
    from pypdf import PdfReader

    doc_id = str(uuid.uuid4())
    title = filename.removesuffix(".pdf")

    reader = PdfReader(file)
    full_text = "\n\n".join(
        page.extract_text() or "" for page in reader.pages
    ).strip()

    if not full_text:
        raise ValueError("No extractable text found in PDF.")

    docs = [Document(page_content=full_text, metadata={})]
    chunk_count = _ingest_documents(docs, doc_id, title, "pdf")

    return {"doc_id": doc_id, "title": title, "chunk_count": chunk_count}


def ingest_text_file(content: bytes, filename: str) -> dict:
    doc_id = str(uuid.uuid4())
    title = filename.rsplit(".", 1)[0]

    text = content.decode("utf-8", errors="replace")
    docs = [Document(page_content=text, metadata={})]
    chunk_count = _ingest_documents(docs, doc_id, title, "file")

    return {"doc_id": doc_id, "title": title, "chunk_count": chunk_count}


def reindex_all() -> int:
    """Re-embed all stored documents using the current embedding provider."""
    from chromadb import PersistentClient
    from app.core.embeddings import get_embeddings
    from langchain_chroma import Chroma

    # Pull all raw documents from ChromaDB
    client = PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(settings.collection_name)
    result = collection.get(include=["documents", "metadatas"])

    if not result["documents"]:
        return 0

    # Delete existing collection and recreate with new embeddings
    client.delete_collection(settings.collection_name)

    embeddings = get_embeddings()
    new_vs = Chroma(
        client=client,
        collection_name=settings.collection_name,
        embedding_function=embeddings,
    )

    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(result["documents"], result["metadatas"])
    ]
    new_vs.add_documents(docs)
    return len(docs)
