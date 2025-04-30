# Search endpoint
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from app.models.search import SearchRequest, SearchResponse
from app.services.search_service import SearchService
from app.services.openai_service import OpenAIService
from app.api.dependencies import get_search_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/search", response_model=SearchResponse)
async def search_candidates(
    request: SearchRequest,
    search_service: SearchService = Depends(get_search_service)
):
    """
    Search for candidates using hybrid search (Mongolian keyword, English keyword, and semantic).
    
    Args:
        request: Search parameters
        search_service: Search service instance
        
    Returns:
        Search results with candidate matches and metadata
    """
    logger.info(f"Received search request: query_mn='{request.query_mn}', "
                f"min_years_exp={request.min_years_exp}, max_years_exp={request.max_years_exp}")
    
    try:
        results = await search_service.search_candidates(request)
        
        logger.info(f"Search completed: {len(results.candidates)} candidates found in "
                    f"{results.processing_time_ms:.2f}ms")
        
        return results
    
    except ValueError as e:
        logger.error(f"Validation error in search: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error in search: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during search: {str(e)}")