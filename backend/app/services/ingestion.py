import uuid
from datetime import datetime, timezone

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

    return {"doc_id": doc_id, "title": title, "chunk_count": chunk_count, "content": content}


def extract_file(content: bytes, filename: str) -> tuple[str, str, str]:
    """Extract (text, title, source_type) from raw file bytes without ingesting."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == ".pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        if not text:
            raise ValueError("No extractable text found in PDF.")
        return text, filename.removesuffix(".pdf"), "pdf"
    else:
        return content.decode("utf-8", errors="replace"), filename.rsplit(".", 1)[0], "file"


def ingest_file(content: bytes, filename: str) -> dict:
    """Ingest any supported file type (PDF, TXT, MD) from raw bytes."""
    text, title, source_type = extract_file(content, filename)

    doc_id = str(uuid.uuid4())
    docs = [Document(page_content=text, metadata={})]
    chunk_count = _ingest_documents(docs, doc_id, title, source_type)

    return {"doc_id": doc_id, "title": title, "source_type": source_type, "chunk_count": chunk_count, "content": text}


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

    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(result["documents"], result["metadatas"])
    ]

    # Embed dulu ke collection sementara — jika gagal, collection asli tetap aman
    tmp_name = f"{settings.collection_name}_reindex_tmp"
    try:
        embeddings = get_embeddings()
        tmp_vs = Chroma(
            client=client,
            collection_name=tmp_name,
            embedding_function=embeddings,
        )
        tmp_vs.add_documents(docs)
    except Exception:
        client.delete_collection(tmp_name)
        raise

    # Embedding berhasil — swap collection
    client.delete_collection(settings.collection_name)
    client.get_collection(tmp_name)  # verify exists
    # Rename tidak didukung chromadb, jadi re-embed ke collection final
    final_vs = Chroma(
        client=client,
        collection_name=settings.collection_name,
        embedding_function=embeddings,
    )
    final_vs.add_documents(docs)
    client.delete_collection(tmp_name)
    return len(docs)
