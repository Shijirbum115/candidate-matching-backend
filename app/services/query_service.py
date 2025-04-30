# Query parsing and processing
import logging
import re
from typing import List, Dict, Any, Optional

from app.models.search import QueryParameters
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class QueryService:
    """Service for processing and understanding search queries."""
    
    def __init__(self, openai_service: Optional[OpenAIService] = None):
        """
        Initialize query service.
        
        Args:
            openai_service: OpenAI service instance for translations and embeddings
        """
        self.openai_service = openai_service or OpenAIService()
    
    def process_query(self, query_mn: str) -> Dict[str, Any]:
        """
        Process a Mongolian query and extract all relevant information.
        
        Args:
            query_mn: Mongolian query text
            
        Returns:
            Dictionary with processed query information
        """
        logger.info(f"Processing query: {query_mn}")
        
        # Extract structured parameters from query
        parameters = self.openai_service.extract_query_parameters(query_mn)
        
        # Translate query to English
        query_en = self.openai_service.translate_to_english(query_mn)
        logger.info(f"Translated query: {query_en}")
        
        # Generate embedding
        embedding = self.openai_service.generate_embedding(query_en)
        
        return {
            "query_mn": query_mn,
            "query_en": query_en,
            "parameters": parameters,
            "embedding": embedding
        }
    
    @staticmethod
    def extract_parameters_regex(query_mn: str) -> QueryParameters:
        """
        Extract query parameters using regex patterns as a fallback.
        
        Args:
            query_mn: Mongolian query text
            
        Returns:
            QueryParameters object
        """
        parameters = QueryParameters()
        
        # Look for experience patterns
        exp_patterns = [
            r'(\d+)[\+\-]?\s*жил',  # 5+ жил, 5 жил
            r'(\d+)[\+\-]?\s*жилийн',  # 5+ жилийн, 5 жилийн
            r'(\d+)[\+\-]?\s*[\w\s]+туршлага'  # 5+ жилийн туршлага
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, query_mn)
            if match:
                parameters.experience_years = int(match.group(1))
                break
        
        # Common job title keywords in Mongolian
        job_title_keywords = [
            "менежер", "инженер", "хөгжүүлэгч", "зөвлөх", "багш", 
            "нягтлан", "програмист", "дизайнер", "эмч"
        ]
        
        # Extract job title
        for keyword in job_title_keywords:
            if keyword in query_mn.lower():
                # Get surrounding context
                index = query_mn.lower().find(keyword)
                start = max(0, index - 15)
                end = min(len(query_mn), index + len(keyword) + 15)
                context = query_mn[start:end]
                parameters.job_title = context.strip()
                break
        
        # Common industry keywords in Mongolian
        industry_keywords = [
            "банк", "санхүү", "технологи", "боловсрол", "эрүүл мэнд",
            "барилга", "уул уурхай", "үйлдвэрлэл"
        ]
        
        # Extract industry
        for keyword in industry_keywords:
            if keyword in query_mn.lower():
                parameters.industry = keyword
                break
        
        return parameters
    
    @staticmethod
    def clean_query_for_search(query: str) -> List[str]:
        """
        Clean and tokenize a query for search purposes.
        
        Args:
            query: Query text
            
        Returns:
            List of cleaned query terms
        """
        # Remove special characters
        cleaned = re.sub(r'[^\w\s]', ' ', query.lower())
        
        # Split into terms and filter short words
        terms = [term.strip() for term in cleaned.split() if len(term.strip()) > 2]
        
        return terms