# Custom exceptions
from typing import Any, Dict, Optional

from fastapi import HTTPException, status


class DatabaseError(HTTPException):
    """Exception raised for database errors."""
    
    def __init__(
        self, 
        detail: str = "Database error occurred", 
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
            headers=headers
        )


class OpenAIError(HTTPException):
    """Exception raised for OpenAI API errors."""
    
    def __init__(
        self, 
        detail: str = "OpenAI API error occurred", 
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            headers=headers
        )


class InvalidSearchQueryError(HTTPException):
    """Exception raised for invalid search queries."""
    
    def __init__(
        self, 
        detail: str = "Invalid search query", 
        headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            headers=headers
        )