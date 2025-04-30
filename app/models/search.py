# Search related models
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class SearchRequest(BaseModel):
    """
    Search request model with all query parameters.
    """
    query_mn: str = Field(..., description="Search query in Mongolian")
    min_years_exp: Optional[int] = Field(None, description="Minimum years of experience filter")
    max_years_exp: Optional[int] = Field(None, description="Maximum years of experience filter")
    limit: int = Field(20, description="Maximum number of results to return")
    score_threshold: float = Field(0.3, description="Minimum score threshold for results")
    experience_weight_multiplier: float = Field(2.0, description="Multiplier for candidates with >= 5 years experience")
    mn_keyword_weight: float = Field(1.0, description="Weight for Mongolian keyword search")
    en_keyword_weight: float = Field(1.0, description="Weight for English keyword search")
    semantic_weight: float = Field(1.0, description="Weight for semantic search")
    
    @validator('query_mn')
    def query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Search query cannot be empty')
        return v.strip()
    
    @validator('score_threshold')
    def score_threshold_range(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Score threshold must be between 0 and 1')
        return v


class CandidateScores(BaseModel):
    """
    Component scores for a candidate match.
    """
    mn_keyword_score: float
    en_keyword_score: float
    semantic_score: float
    experience_factor: float
    final_score: float


class CandidateMatch(BaseModel):
    """
    A candidate search result with detailed scoring information.
    """
    id: int
    first_name: str
    last_name: str
    total_years_experience: float
    scores: CandidateScores
    explanation: str
    position_titles: Optional[List[str]] = None
    skills: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """
    Search response with candidates and metadata.
    """
    candidates: List[CandidateMatch]
    query_params: Dict[str, Any]
    total_candidates_processed: int = 0
    total_candidates_after_filtering: int = 0
    processing_time_ms: float


class QueryParameters(BaseModel):
    """
    Structured parameters extracted from a query.
    """
    job_title: Optional[str] = None
    industry: Optional[str] = None
    experience_years: Optional[int] = None