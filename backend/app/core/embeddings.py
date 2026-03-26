from langchain_core.embeddings import Embeddings
from app.config import settings


def get_embeddings() -> Embeddings:
    if settings.embedding_provider == "google":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.google_api_key,
        )

    if settings.embedding_provider == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=settings.openai_api_key,
        )

    if settings.embedding_provider == "lmstudio":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(
            model=settings.lmstudio_embedding_model,
            api_key="lmstudio",
            base_url=settings.lmstudio_base_url,
            check_embedding_ctx_length=False,
        )

    raise ValueError(f"Unsupported embedding provider: {settings.embedding_provider}")
