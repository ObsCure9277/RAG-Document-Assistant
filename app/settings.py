from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://rag_assistant:change-me@localhost:5432/rag_assistant"
    embedding_dimension: int = Field(default=1536, ge=1)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    upload_root: str = "/data/uploads"
    openai_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = Field(default=32, ge=1)
    max_indexing_attempts: int = Field(default=3, ge=1)
    inngest_event_key: str = ""
    inngest_signing_key: str = ""
    inngest_event_api_url: str = "http://localhost:8288/e"
    retrieval_vector_candidates: int = Field(default=20, ge=1)
    retrieval_text_candidates: int = Field(default=20, ge=1)
    retrieval_context_limit: int = Field(default=8, ge=1)
    retrieval_similarity_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    answer_model: str = "gpt-4o-mini"
    answer_max_tokens: int = Field(default=800, ge=1)
    conversation_history_limit: int = Field(default=10, ge=1)
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()






