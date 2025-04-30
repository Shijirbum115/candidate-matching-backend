# Application entry point
import logging
import os
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.database import setup_db_pool, close_db_pool

# Set up logging
logger = setup_logging()
settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router)


@app.middleware("http")
async def log_requests(request: Request, call_next: Callable) -> Response:
    """Middleware to log all requests and responses."""
    logger.info(f"Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response: {request.method} {request.url.path} - Status: {response.status_code}")
    return response


@app.on_event("startup")
async def startup_event():
    """Initialize resources on application startup."""
    logger.info("Starting up application...")
    
    # Initialize DB connection pool
    setup_db_pool()
    
    # Create logs directory if it doesn't exist
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    
    logger.info("Application startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down application...")
    
    # Close DB connection pool
    close_db_pool()
    
    logger.info("Application shutdown complete")


if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )