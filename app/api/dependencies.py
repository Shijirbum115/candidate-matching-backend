
from typing import Generator

from app.db.database import get_db_connection
from app.services.openai_service import OpenAIService
from app.services.query_service import QueryService
from app.services.search_service import SearchService


def get_db():
    """Dependency to get a database connection."""
    with get_db_connection() as conn:
        yield conn


def get_openai_service() -> OpenAIService:
    """Dependency to get an OpenAI service instance."""
    return OpenAIService()


def get_search_service() -> SearchService:
    """Dependency to get a search service instance."""
    openai_service = get_openai_service()
    return SearchService(openai_service)