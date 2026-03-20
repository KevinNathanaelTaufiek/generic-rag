import chromadb
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

from app.config import settings
from app.core.embeddings import get_embeddings


def get_vectorstore(embeddings: Embeddings | None = None) -> Chroma:
    if embeddings is None:
        embeddings = get_embeddings()

    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)

    return Chroma(
        client=client,
        collection_name=settings.collection_name,
        embedding_function=embeddings,
    )
