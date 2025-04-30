# Core search logic
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from app.db.repositories import CandidateRepository
from app.services.openai_service import OpenAIService
from app.services.query_service import QueryService
from app.models.search import (
    SearchRequest, 
    SearchResponse, 
    CandidateMatch, 
    CandidateScores,
    QueryParameters
)
from app.utils.score_utils import (
    normalize_scores,
    calculate_experience_weight,
    generate_explanation
)
from app.core.logging import log_search_metrics

logger = logging.getLogger(__name__)


class SearchService:
    """Service for handling candidate search operations."""
    
    def __init__(
        self, 
        openai_service: Optional[OpenAIService] = None,
        query_service: Optional[QueryService] = None
    ):
        """
        Initialize the search service.
        
        Args:
            openai_service: OpenAI service instance for translations and embeddings
            query_service: Query service for processing search queries
        """
        self.openai_service = openai_service or OpenAIService()
        self.query_service = query_service or QueryService(self.openai_service)
        self.candidate_repo = CandidateRepository()
    
    async def search_candidates(self, request: SearchRequest) -> SearchResponse:
        """
        Search for candidates using hybrid search approach.
        
        Args:
            request: Search request parameters
            
        Returns:
            Search response with matched candidates
        """
        start_time = datetime.now()
        
        # Step 1: Process query with query service
        logger.info(f"Processing search query: {request.query_mn}")
        processed_query = self.query_service.process_query(request.query_mn)
        
        query_params = processed_query["parameters"]
        query_en = processed_query["query_en"]
        query_vector = processed_query["embedding"]
        
        logger.info(f"Translated query: {query_en}")
        
        # Step 2: Translate query to English
        query_en = self.openai_service.translate_to_english(request.query_mn)
        logger.info(f"Translated query: {query_en}")
        
        # Step 3: Generate embedding for query
        query_vector = self.openai_service.generate_embedding(query_en)
        
        # Step 4: Run hybrid search
        search_results = self.candidate_repo.perform_hybrid_search(
            query_mn=request.query_mn,
            query_en=query_en,
            query_vector=query_vector,
            min_years_exp=request.min_years_exp,
            max_years_exp=request.max_years_exp,
            limit=200  # Get more candidates than needed for post-processing
        )
        
        #Step 5: Normalization ( Convert Decimal to float before normalization )
        mn_scores = {r['id']: float(r['mn_keyword_score']) for r in search_results}
        en_scores = {r['id']: float(r['en_keyword_score']) for r in search_results}
        semantic_scores = {r['id']: float(r['semantic_score']) for r in search_results}
        
        mn_scores_norm = normalize_scores(mn_scores)
        en_scores_norm = normalize_scores(en_scores)
        semantic_scores_norm = normalize_scores(semantic_scores)
        
        # Step 6: Calculate final scores and create results
        candidates = []
        candidate_log_data = []  # For detailed logging
        
        for result in search_results:
            candidate_id = result['id']
            
            # Calculate scores
            mn_score = mn_scores_norm.get(candidate_id, 0.0)
            en_score = en_scores_norm.get(candidate_id, 0.0)
            semantic_score = semantic_scores_norm.get(candidate_id, 0.0)
            
             # Calculate experience weight
            years_exp = 0.0
            if result['total_years_experience'] is not None:
                try:
                    years_exp = float(result['total_years_experience'])
                except (ValueError, TypeError):
                    years_exp = 0.0
                    
            experience_factor = calculate_experience_weight(
                years_exp, 
                request.experience_weight_multiplier
            )
            
            # Calculate final score
            weights = {
                'mn_keyword': request.mn_keyword_weight,
                'en_keyword': request.en_keyword_weight,
                'semantic': request.semantic_weight,
            }
            
            weighted_score = (
                mn_score * weights['mn_keyword'] + 
                en_score * weights['en_keyword'] + 
                semantic_score * weights['semantic']
            )
            
            # Apply experience factor as a multiplier
            final_score = weighted_score * experience_factor
            
            # Create score object
            scores = CandidateScores(
                mn_keyword_score=round(mn_score, 3),
                en_keyword_score=round(en_score, 3),
                semantic_score=round(semantic_score, 3),
                experience_factor=round(experience_factor, 3),
                final_score=round(final_score, 3)
            )
            
            # Skip candidates below threshold
            if final_score < request.score_threshold:
                continue
                
            # Generate explanation
            explanation = generate_explanation(
                candidate=result,
                query_params=query_params,
                scores=scores
            )
            
            # Create candidate match
            candidate = CandidateMatch(
                id=candidate_id,
                first_name=str(result['first_name'] or ""),
                last_name=str(result['last_name'] or ""),
                total_years_experience=years_exp,
                scores=scores,
                explanation=explanation,
                position_titles=result.get('position_titles') or [],
                skills=result.get('skills') or []
            )
            
            candidates.append(candidate)
            
            # Create detailed log data
            candidate_log_data.append({
                "id": candidate_id,
                "name": f"{str(result['first_name'] or '')} {str(result['last_name'] or '')}",
                "experience_years": years_exp,
                "raw_scores": {
                    "mn_keyword": result['mn_keyword_score'],
                    "en_keyword": result['en_keyword_score'],
                    "semantic": result['semantic_score']
                },
                "normalized_scores": {
                    "mn_keyword": mn_score,
                    "en_keyword": en_score,
                    "semantic": semantic_score
                },
                "experience_factor": experience_factor,
                "final_score": final_score,
                "position_titles": result.get('position_titles') or [],
                "skills": result.get('skills') or [],
                "passed_threshold": True
            })
        
        # Sort by final score (descending)
        candidates.sort(key=lambda x: x.scores.final_score, reverse=True)
        
        # Limit results
        candidates = candidates[:request.limit]
        
        # Calculate time taken
        end_time = datetime.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Create response
        response = SearchResponse(
            candidates=candidates,
            query_params={
                "original_query": request.query_mn,
                "translated_query": query_en,
                "extracted_params": query_params.dict()
            },
            total_candidates_processed=len(search_results),
            total_candidates_after_filtering=len(candidates),
            processing_time_ms=processing_time_ms
        )
        
        # Log detailed search metrics
        log_search_metrics(
            query=request.query_mn,
            query_en=query_en,
            num_candidates_processed=len(search_results),
            num_results_returned=len(candidates),
            processing_time_ms=processing_time_ms,
            score_threshold=request.score_threshold,
            weights={
                "mn_keyword": request.mn_keyword_weight,
                "en_keyword": request.en_keyword_weight,
                "semantic": request.semantic_weight,
                "experience_multiplier": request.experience_weight_multiplier
            },
            candidates=candidate_log_data
        )
        
        return response