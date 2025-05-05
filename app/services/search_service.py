# Core search logic
import logging
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import re

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
        logger.info(f"Extracted parameters: {query_params}")
        
        # Step 2: Enhance the search by extracting specific search terms
        # Similar to your previous implementation
        search_terms = self._extract_search_terms(request.query_mn, query_en)
        logger.info(f"Extracted search terms: {search_terms}")
        
        # Step 3: Run hybrid search
        search_results = self.candidate_repo.perform_hybrid_search(
            query_mn=request.query_mn,
            query_en=query_en,
            query_vector=query_vector,
            min_years_exp=request.min_years_exp,
            max_years_exp=request.max_years_exp,
            limit=200  # Get more candidates than needed for post-processing
        )
        
        # Debug the first result
        if search_results:
            logger.info(f"First search result: {search_results[0]}")
        
        # Step 4: Improved scoring - Fix normalization and enhance relevance
        mn_scores = {}
        en_scores = {}
        semantic_scores = {}
        term_match_scores = {}
        
        # Process raw scores from database results
        for r in search_results:
            candidate_id = r['id']
            
            # Convert to float to avoid Decimal issues
            mn_scores[candidate_id] = float(r['mn_keyword_score']) if r['mn_keyword_score'] is not None else 0.0
            en_scores[candidate_id] = float(r['en_keyword_score']) if r['en_keyword_score'] is not None else 0.0
            semantic_scores[candidate_id] = float(r['semantic_score']) if r['semantic_score'] is not None else 0.0
            
            # Calculate enhanced term matching score
            # This uses a more sophisticated matching approach similar to your previous code
            position_titles = r.get('position_titles') or []
            skills = r.get('skills') or []
            
            # Implement term matching similar to your previous approach
            term_score = self._calculate_term_match(
                position_titles=position_titles,
                skills=skills,
                search_terms=search_terms,
                job_title=query_params.job_title
            )
            term_match_scores[candidate_id] = term_score
        
        # Log some stats about the scores before normalization
        if search_results:
            mn_stats = self._get_score_stats(mn_scores)
            en_stats = self._get_score_stats(en_scores)
            semantic_stats = self._get_score_stats(semantic_scores)
            term_stats = self._get_score_stats(term_match_scores)
            
            logger.info(f"Raw score stats - MN: {mn_stats}, EN: {en_stats}, " 
                        f"Semantic: {semantic_stats}, Term: {term_stats}")
        
        # Normalize scores - but check if all scores are identical first
        mn_scores_norm = normalize_scores(mn_scores)
        en_scores_norm = normalize_scores(en_scores)
        semantic_scores_norm = normalize_scores(semantic_scores)
        term_scores_norm = normalize_scores(term_match_scores)
        
        # Log normalized score samples for debugging
        if search_results:
            candidate_ids = list(mn_scores.keys())[:5]
            score_samples = [(
                cid, 
                mn_scores_norm.get(cid, 0), 
                en_scores_norm.get(cid, 0), 
                semantic_scores_norm.get(cid, 0),
                term_scores_norm.get(cid, 0)
            ) for cid in candidate_ids]
            logger.info(f"Normalized score samples: {score_samples}")
        
        # Step 5: Calculate final scores and create results
        candidates = []
        candidate_log_data = []  # For detailed logging
        
        for result in search_results:
            candidate_id = result['id']
            
            # Calculate scores
            mn_score = mn_scores_norm.get(candidate_id, 0.0)
            en_score = en_scores_norm.get(candidate_id, 0.0)
            semantic_score = semantic_scores_norm.get(candidate_id, 0.0)
            term_score = term_scores_norm.get(candidate_id, 0.0)
            
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
            
            # Calculate final score with balanced weights
            # Add the term score as an additional component
            weights = {
                'mn_keyword': request.mn_keyword_weight * 0.3,  # Reduce weight of general MN match
                'en_keyword': request.en_keyword_weight,
                'semantic': request.semantic_weight,
                'term_match': 0.7,  # Add weight for specific term matching
            }
            
            weighted_score = (
                mn_score * weights['mn_keyword'] + 
                en_score * weights['en_keyword'] + 
                semantic_score * weights['semantic'] +
                term_score * weights['term_match']
            )
            
            # Apply experience factor as a multiplier
            final_score = weighted_score * experience_factor
            
            # Create score object - but use the enhanced term matching for MN score
            # This ensures the front-end visualization still works with 3 components
            scores = CandidateScores(
                mn_keyword_score=round(term_score, 3),  # Use term score instead
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
                    "semantic": result['semantic_score'],
                    "term_match": term_match_scores.get(candidate_id, 0)
                },
                "normalized_scores": {
                    "mn_keyword": mn_score,
                    "en_keyword": en_score,
                    "semantic": semantic_score,
                    "term_match": term_score
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
                "extracted_params": query_params.dict(),
                "search_terms": search_terms
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
                "term_match": 0.7,
                "experience_multiplier": request.experience_weight_multiplier
            },
            candidates=candidate_log_data
        )
        
        return response
    
    def _extract_search_terms(self, query_mn: str, query_en: str) -> List[str]:
        """Extract specific search terms from query."""
        terms = []
        
        # Extract from Mongolian query
        mn_terms = re.findall(r'\b\w{3,}\b', query_mn.lower())
        for term in mn_terms:
            if len(term) > 2 and term not in terms:
                terms.append(term)
        
        # Extract from English query
        en_terms = re.findall(r'\b\w{3,}\b', query_en.lower())
        for term in en_terms:
            if len(term) > 2 and term not in terms:
                terms.append(term)
        
        return terms
    
    def _calculate_term_match(
        self, 
        position_titles: List[str], 
        skills: List[str],
        search_terms: List[str],
        job_title: Optional[str]
    ) -> float:
        """
        Calculate a more precise term match score based on how well
        the candidate's profile matches specific search terms.
        """
        score = 0.0
        exact_match_bonus = 0.0
        
        # Process titles and skills to a single list of text
        candidate_text = []
        
        for title in position_titles:
            if title:
                candidate_text.append(title.lower())
        
        for skill in skills:
            if skill:
                candidate_text.append(skill.lower())
        
        if not candidate_text:
            return 0.0
            
        # Check for matches with search terms
        matched_terms = 0
        for term in search_terms:
            term_matched = False
            for text in candidate_text:
                if term in text:
                    matched_terms += 1
                    term_matched = True
                    break
            
            # Exact match bonus for job title
            if job_title and term_matched and term in job_title.lower():
                exact_match_bonus += 0.2
        
        # Calculate base score as proportion of matched terms
        if search_terms:
            score = matched_terms / len(search_terms)
        
        # Add exact match bonus (capped at 1.0)
        score = min(1.0, score + exact_match_bonus)
        
        return score
    
    def _get_score_stats(self, scores: Dict[int, float]) -> Dict[str, float]:
        """Get basic statistics for a set of scores."""
        if not scores:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}
        
        values = list(scores.values())
        return {
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "count": len(values)
        }