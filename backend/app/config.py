from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: Literal["openai", "gemini"] = "gemini"
    embedding_provider: Literal["google", "openai"] = "google"

    openai_api_key: str = ""
    google_api_key: str = ""
    tavily_api_key: str = ""

    chroma_persist_dir: str = "./data/chroma"
    collection_name: str = "generic_rag"
    top_k_results: int = 5
    chunk_size: int = 500
    chunk_overlap: int = 50
    dummy_services_base_url: str = "http://localhost:8001"


settings = Settings()
