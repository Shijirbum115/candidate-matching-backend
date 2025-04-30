import logging
import json
import time
from typing import Dict, List, Optional, Any

import requests
from pydantic import ValidationError

from app.core.config import get_settings
from app.models.search import QueryParameters

settings = get_settings()
logger = logging.getLogger(__name__)


class OpenAIService:
    """Service for interacting with OpenAI APIs."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenAI service.
        
        Args:
            api_key: OpenAI API key (defaults to the one in settings)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def translate_to_english(self, text: str) -> str:
        """
        Translate Mongolian text to English using OpenAI.
        
        Args:
            text: Mongolian text to translate
            
        Returns:
            Translated English text
        """
        if not text or not text.strip():
            return ""
        
        logger.info(f"Translating text to English: {text[:50]}...")
        
        try:
            data = {
                "model": settings.TRANSLATION_MODEL,
                "messages": [
                    {"role": "system", "content": "You are a translator. Translate the given Mongolian text to English accurately."},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.3
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            
            response.raise_for_status()
            translated_text = response.json()["choices"][0]["message"]["content"].strip()
            
            logger.info(f"Translation successful: {translated_text[:50]}...")
            return translated_text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Translation API error: {str(e)}")
            # Fallback to returning the original text
            return text
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate an embedding vector for the given text using OpenAI.
        
        Args:
            text: Text to generate an embedding for
            
        Returns:
            Embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Cannot generate embedding for empty text")
        
        logger.info(f"Generating embedding for text: {text[:50]}...")
        
        try:
            data = {
                "model": settings.EMBEDDING_MODEL,
                "input": text
            }
            
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self.headers,
                json=data
            )
            
            response.raise_for_status()
            embedding = response.json()["data"][0]["embedding"]
            
            logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return embedding
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Embedding API error: {str(e)}")
            raise ValueError(f"Failed to generate embedding: {str(e)}")
    
    def extract_query_parameters(self, query_mn: str) -> QueryParameters:
        """
        Parse the Mongolian query to extract structured parameters.
        
        Args:
            query_mn: Search query in Mongolian
            
        Returns:
            Structured query parameters
        """
        logger.info(f"Extracting structured parameters from query: {query_mn}")
        
        try:
            data = {
                "model": settings.TRANSLATION_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": """
                        You are a query understanding expert. Extract the following parameters from the Mongolian language query:
                        - job_title: The position or role being searched for
                        - industry: The industry or sector mentioned (if any)
                        - experience_years: The years of experience mentioned (if any)
                        
                        Return ONLY a JSON object with these fields. If a field is not present in the query, set its value to null.
                        """
                    },
                    {
                        "role": "user", 
                        "content": query_mn
                    }
                ],
                "temperature": 0.1
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=data
            )
            
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            
            # Parse the JSON response
            parameters = json.loads(content)
            logger.info(f"Extracted parameters: {parameters}")
            
             #Process experience_years to handle formats like "5+" 
            if parameters.get('experience_years') and isinstance(parameters['experience_years'], str):
                exp_str = parameters['experience_years']
                if '+' in exp_str:
                    # Extract the number part from strings like "5+"
                    parameters['experience_years'] = int(exp_str.replace('+', ''))
            
            # Attempt to create a validated QueryParameters object
            return QueryParameters(**parameters)
            
        except (requests.exceptions.RequestException, json.JSONDecodeError, ValidationError) as e:
            logger.error(f"Parameter extraction error: {str(e)}")
            logger.warning("Falling back to regex-based extraction")
            
            # Fallback to regex-based extraction
            import re
            
            parameters = QueryParameters()
            
            # Look for patterns like "5+ жил", "5-7 жил", etc.
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
            
            # Try to extract job title - common job titles in Mongolian
            job_title_keywords = ["менежер", "инженер", "хөгжүүлэгч", "зөвлөх", "багш", "нягтлан"]
            job_title_matches = []
            
            for keyword in job_title_keywords:
                if keyword in query_mn.lower():
                    # Get the surrounding context for the keyword
                    match_idx = query_mn.lower().find(keyword)
                    start_idx = max(0, match_idx - 15)
                    end_idx = min(len(query_mn), match_idx + len(keyword) + 15)
                    context = query_mn[start_idx:end_idx]
                    job_title_matches.append(context)
            
            if job_title_matches:
                parameters.job_title = job_title_matches[0]
            
            logger.info(f"Regex extraction results: {parameters}")
            return parameters