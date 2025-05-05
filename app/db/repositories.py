# Data access layer
import logging
from typing import Any, Dict, List, Optional, Tuple
import json

from psycopg2.extras import Json

from app.db.database import get_db_connection
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class CandidateRepository:
    """Repository for candidate-related database operations."""
    
    @staticmethod
    def perform_hybrid_search(
        query_mn: str,
        query_en: str,
        query_vector: List[float],
        min_years_exp: Optional[int] = None,
        max_years_exp: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Perform a hybrid search using all three methods:
        - Mongolian keyword search with pg_trgm
        - English keyword search with full-text search
        - Semantic search with vector embeddings
        
        Args:
            query_mn: Original Mongolian query
            query_en: Translated English query
            query_vector: Embedding vector of the query
            min_years_exp: Minimum years of experience filter
            max_years_exp: Maximum years of experience filter
            limit: Maximum number of candidates to return
            
        Returns:
            List of candidates with their scores
        """
        logger.info(f"Performing hybrid search for query: {query_mn}")
        
        # Clean and prepare the queries
        # For Mongolian trigram search
        mn_terms = [term.strip() for term in query_mn.split() if len(term.strip()) > 2]
        mn_patterns = [f"%{term}%" for term in mn_terms]
        
        # For English full-text search
        en_terms = [term.strip() for term in query_en.split() if len(term.strip()) > 2]
        en_terms = [term.replace("'", "") for term in en_terms]  # Remove apostrophes
        en_tsquery = " | ".join(en_terms) if en_terms else ""
        
        # For vector search - convert to string format
        vector_str = f"[{','.join(str(x) for x in query_vector)}]"
        
        # Build filter conditions for experience
        experience_filters = []
        if min_years_exp is not None:
            experience_filters.append(f"c.total_years_experience >= {min_years_exp}")
        if max_years_exp is not None:
            experience_filters.append(f"c.total_years_experience <= {max_years_exp}")
        
        experience_filter_clause = " AND ".join(experience_filters)
        where_clause = f"WHERE {experience_filter_clause}" if experience_filters else ""
        
        # Construct the hybrid search query
        query = f"""
        -- Set vector search parameters
        SET LOCAL ivfflat.probes = 100;
        
        WITH candidate_scores AS (
            SELECT
                c.id,
                c.first_name,
                c.last_name,
                c.total_years_experience,
                -- Mongolian keyword search using experience and skills tables
                (
                    SELECT COALESCE(MAX(CASE
                        WHEN ce.position_title ILIKE ANY(%s) THEN 0.8
                        WHEN ce.work_description ILIKE ANY(%s) THEN 0.6
                        ELSE 0
                    END), 0) as mn_position_score
                    FROM candidate_experience ce
                    WHERE ce.candidate_id = c.id
                ) AS mn_keyword_score,
                
                -- English keyword search using tsvector
                CASE
                    WHEN %s != '' THEN COALESCE(ts_rank_cd(c.fts_vector_en, to_tsquery('english', %s)), 0)
                    ELSE 0
                END AS en_keyword_score,
                
                -- Semantic search using vector embedding
                CASE
                    WHEN c.embedding IS NOT NULL THEN 1 - (c.embedding <-> %s::vector)
                    ELSE 0
                END AS semantic_score
            FROM
                candidates c
            {where_clause}
        )
        SELECT
            cs.*,
            -- Get position titles for explanation
            (
                SELECT json_agg(position_title)
                FROM (
                    SELECT position_title
                    FROM candidate_experience
                    WHERE candidate_id = cs.id
                    ORDER BY
                        CASE
                            WHEN position_title ILIKE ANY(%s) THEN 0
                            ELSE 1
                        END,
                        end_date DESC NULLS FIRST
                    LIMIT 3
                ) t
            ) AS position_titles,
            
            -- Get skills for explanation
            (
                SELECT json_agg(skill_name)
                FROM (
                    SELECT skill_name
                    FROM candidate_skills
                    WHERE candidate_id = cs.id
                    LIMIT 5
                ) t
            ) AS skills
        FROM
            candidate_scores cs
        WHERE
            cs.mn_keyword_score > 0 OR cs.en_keyword_score > 0 OR cs.semantic_score > 0
        ORDER BY
            (cs.mn_keyword_score + cs.en_keyword_score + cs.semantic_score) DESC
        LIMIT %s
        """
        
        # Debug the query and parameters
        logger.debug(f"Query parameters count: {query.count('%s')}")
        
        # PostgreSQL needs arrays in a specific format for ANY operator
        # The reason for the error is that we need to pass an actual array, not a tuple of strings
        params = [
            mn_patterns,      # position_title ILIKE ANY - must be a list, not a tuple
            mn_patterns,      # work_description ILIKE ANY - must be a list, not a tuple
            en_tsquery,       # ts_rank_cd condition
            en_tsquery,       # to_tsquery parameter
            vector_str,       # embedding <-> parameter
            mn_patterns,      # For position titles ordering - must be a list, not a tuple
            limit             # LIMIT parameter
        ]
        
        results = []
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(query, params)
                    results = cursor.fetchall()
                    
                    # Convert JSON strings to Python lists
                    for result in results:
                        if result['position_titles'] and isinstance(result['position_titles'], str):
                            result['position_titles'] = json.loads(result['position_titles'])
                        if result['skills'] and isinstance(result['skills'], str):
                            result['skills'] = json.loads(result['skills'])
                    
                    logger.info(f"Hybrid search returned {len(results)} candidates")
                except Exception as e:
                    logger.error(f"Error during hybrid search: {e}")
                    raise
        
        return results
    
    @staticmethod
    def get_candidate_details(candidate_id: int) -> Dict[str, Any]:
        """
        Get detailed information for a specific candidate.
        
        Args:
            candidate_id: The ID of the candidate
            
        Returns:
            Candidate details
        """
        query = """
        SELECT
            c.*,
            (
                SELECT json_agg(row_to_json(e))
                FROM (
                    SELECT * FROM candidate_experience 
                    WHERE candidate_id = c.id
                    ORDER BY end_date DESC NULLS FIRST
                ) e
            ) AS experiences,
            (
                SELECT json_agg(skill_name)
                FROM candidate_skills
                WHERE candidate_id = c.id
            ) AS skills,
            (
                SELECT json_agg(row_to_json(e))
                FROM (
                    SELECT * FROM candidate_education
                    WHERE candidate_id = c.id
                ) e
            ) AS education
        FROM
            candidates c
        WHERE
            c.id = %s
        """
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (candidate_id,))
                result = cursor.fetchone()
                
                if result:
                    # Convert JSON strings to Python objects if needed
                    for key in ['experiences', 'skills', 'education']:
                        if result[key] and isinstance(result[key], str):
                            result[key] = json.loads(result[key])
                
                return result