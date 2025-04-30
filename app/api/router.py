# API router
from fastapi import APIRouter

from app.api.endpoints import search, health

api_router = APIRouter()

# Include routers from endpoints
api_router.include_router(search.router, prefix="/api", tags=["search"])
api_router.include_router(health.router, prefix="/api", tags=["system"])