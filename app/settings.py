from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://rag_assistant:change-me@localhost:5432/rag_assistant"
    embedding_dimension: int = Field(default=1536, ge=1)
    max_upload_bytes: int = Field(default=50 * 1024 * 1024, ge=1)
    upload_root: str = "/data/uploads"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

