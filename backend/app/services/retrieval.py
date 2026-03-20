from collections import defaultdict

from app.core.vectorstore import get_vectorstore
from app.schemas.knowledge import DocumentInfo


def list_documents() -> list[DocumentInfo]:
    """Return one DocumentInfo per unique doc_id stored in ChromaDB."""
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    result = collection.get(include=["metadatas"])

    doc_map: dict[str, dict] = {}
    chunk_counts: dict[str, int] = defaultdict(int)

    for meta in result.get("metadatas") or []:
        doc_id = meta.get("doc_id")
        if not doc_id:
            continue
        chunk_counts[doc_id] += 1
        if doc_id not in doc_map:
            doc_map[doc_id] = meta

    docs = []
    for doc_id, meta in doc_map.items():
        docs.append(DocumentInfo(
            doc_id=doc_id,
            title=meta.get("title", "Unknown"),
            source_type=meta.get("source_type", "unknown"),
            created_at=meta.get("created_at", ""),
            chunk_count=chunk_counts[doc_id],
        ))

    docs.sort(key=lambda d: d.created_at, reverse=True)
    return docs


def delete_document(doc_id: str) -> bool:
    """Delete all chunks belonging to a doc_id. Returns False if not found."""
    vectorstore = get_vectorstore()
    collection = vectorstore._collection
    result = collection.get(where={"doc_id": doc_id}, include=[])

    if not result["ids"]:
        return False

    collection.delete(ids=result["ids"])
    return True
