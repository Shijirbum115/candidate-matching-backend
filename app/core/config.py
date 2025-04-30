import os
from typing import Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings."""

    # API Configuration
    APP_NAME: str = "Hybrid Candidate Search API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Advanced candidate search system with hybrid semantic and keyword search"
    
    # Database configuration
    PG_DB_HOST: str = "localhost"
    PG_DB_PORT: str = "5432"
    PG_DB_NAME: str = "hmcs_db"
    PG_DB_USER: str = "postgres"
    PG_DB_PASSWORD: str = ""
    
    # OpenAI configuration
    OPENAI_API_KEY: str
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    TRANSLATION_MODEL: str = "gpt-3.5-turbo"
    
    # Search configuration
    DEFAULT_SEARCH_LIMIT: int = 20
    DEFAULT_SCORE_THRESHOLD: float = 0.3
    DEFAULT_EXPERIENCE_WEIGHT_MULTIPLIER: float = 2.0
    DEFAULT_MN_KEYWORD_WEIGHT: float = 1.0
    DEFAULT_EN_KEYWORD_WEIGHT: float = 1.0
    DEFAULT_SEMANTIC_WEIGHT: float = 1.0
    
    # Vector search configuration
    VECTOR_PROBES: int = 100
    
    # Logging configuration
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    
    # CORS configuration
    CORS_ORIGINS: str = "*"

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        case_sensitive=True, 
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()