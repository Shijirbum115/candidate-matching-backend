# Health check endpoint
from datetime import datetime
from typing import Dict

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.db.database import get_db_connection

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        Health status information
    """
    db_status = "ok"
    try:
        # Test database connection
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }


@router.get("/")
async def root():
    """
    Root endpoint with API information.
    
    Returns:
        API information
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": settings.APP_DESCRIPTION,
        "endpoints": {
            "/api/search": "Main search endpoint",
            "/api/health": "Health check endpoint"
        }
    }