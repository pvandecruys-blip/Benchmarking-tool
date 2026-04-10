"""
SourceLens Configuration Module
Manages application settings via environment variables and runtime configuration.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    google_api_key: str = Field(default="", env="GOOGLE_API_KEY")

    # LLM Configuration
    llm_provider: str = Field(default="gemini", env="LLM_PROVIDER")
    llm_model: str = Field(default="gemini-3.1-flash-lite", env="LLM_MODEL")
    embedding_model: str = Field(default="models/text-embedding-004", env="EMBEDDING_MODEL")

    # Demo mode (generates realistic mock data without API key)
    demo_mode: bool = Field(default=False, env="DEMO_MODE")

    # Processing Configuration
    chunk_size: int = Field(default=800, env="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, env="CHUNK_OVERLAP")
    max_chunks_per_query: int = Field(default=8, env="MAX_CHUNKS_PER_QUERY")
    verification_strictness: str = Field(default="standard", env="VERIFICATION_STRICTNESS")  # lenient, standard, strict

    # File Limits
    max_pptx_size_mb: int = Field(default=100, env="MAX_PPTX_SIZE_MB")
    max_source_size_mb: int = Field(default=50, env="MAX_SOURCE_SIZE_MB")
    max_total_size_mb: int = Field(default=500, env="MAX_TOTAL_SIZE_MB")

    # Paths
    data_dir: str = Field(default="", env="DATA_DIR")
    upload_dir: str = Field(default="", env="UPLOAD_DIR")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    cors_origins: str = Field(default="http://localhost:5173,http://localhost:3000", env="CORS_ORIGINS")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default paths relative to backend directory
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if not self.data_dir:
            self.data_dir = os.path.join(backend_dir, "data")
        if not self.upload_dir:
            self.upload_dir = os.path.join(self.data_dir, "uploads")
        # Ensure directories exist
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "outputs"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "chromadb"), exist_ok=True)


# Singleton settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def update_settings(**kwargs) -> Settings:
    """Update settings at runtime (e.g., from the UI)."""
    global _settings
    current = get_settings()
    updated = current.model_copy(update=kwargs)
    _settings = updated
    return _settings
