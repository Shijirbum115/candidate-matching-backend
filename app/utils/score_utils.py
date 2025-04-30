# Score calculation utilities
from typing import Dict, Any, List, Optional
import logging

from app.models.search import CandidateScores, QueryParameters

logger = logging.getLogger(__name__)


def normalize_scores(scores: Dict[int, float]) -> Dict[int, float]:
    """
    Normalize scores to a 0-1 scale.
    
    Args:
        scores: Dictionary mapping candidate IDs to raw scores
        
    Returns:
        Dictionary mapping candidate IDs to normalized scores
    """
    if not scores:
        return {}
    
    # Filter out None values
    values = [v for v in scores.values() if v is not None]
    
    if not values:
        return {k: 0.0 for k in scores.keys()}
    
    min_val = min(values)
    max_val = max(values)
    
    # Avoid division by zero
    if max_val == min_val:
        return {k: 1.0 if v is not None and v > 0 else 0.0 for k, v in scores.items()}
    
    return {
        k: (v - min_val) / (max_val - min_val) if v is not None else 0.0 
        for k, v in scores.items()
    }


def calculate_experience_weight(years: float, max_multiplier: float = 2.0) -> float:
    """
    Calculate experience weight based on years of experience.
    
    Args:
        years: Years of experience
        max_multiplier: Maximum multiplier for candidates with >= 5 years
        
    Returns:
        Experience weight factor
    """
    try:
        years = float(years)
    except (TypeError, ValueError):
        years = 0.0
    
    # Mapping: 0->1.0, 1->1.2, 2->1.4, 3->1.6, 4->1.8, >=5->max_multiplier
    if years >= 5:
        return max_multiplier
    
    # Linear interpolation for values between 0 and 5
    return 1.0 + (years / 5) * (max_multiplier - 1.0)


def generate_position_summary(position_titles: List[str]) -> str:
    """Generate a summary string from position titles."""
    if not position_titles:
        return "Unknown positions"
    
    position_titles = [p for p in position_titles if p]  # Filter out None or empty values
    
    if not position_titles:
        return "Unknown positions"
    
    if len(position_titles) == 1:
        return f"Position: {position_titles[0]}"
    
    if len(position_titles) == 2:
        return f"Positions: {position_titles[0]} and {position_titles[1]}"
    
    return f"Positions include: {', '.join(position_titles[:2])} and {len(position_titles) - 2} more"


def generate_skills_summary(skills: List[str]) -> str:
    """Generate a summary string from skills."""
    if not skills:
        return "Skills: Unknown"
    
    skills = [s for s in skills if s]  # Filter out None or empty values
    
    if not skills:
        return "Skills: Unknown"
    
    if len(skills) <= 3:
        return f"Skills: {', '.join(skills)}"
    
    return f"Skills include: {', '.join(skills[:3])} and {len(skills) - 3} more"

def get_score_quality(score: float) -> str:
    """Get a qualitative description of a score."""
    if score >= 0.8:
        return "excellent"
    if score >= 0.6:
        return "good"
    if score >= 0.4:
        return "moderate"
    return "low"


def generate_explanation(
    candidate: Dict[str, Any], 
    query_params: QueryParameters,
    scores: CandidateScores
) -> str:
    """
    Generate a human-readable explanation for why this candidate matched.
    
    Args:
        candidate: Candidate data
        query_params: Extracted query parameters
        scores: Calculated match scores
        
    Returns:
        Explanation string
    """
    parts = []
    
    # Basic info
    name = f"{str(candidate.get('first_name', 'Unknown') or 'Unknown')} {str(candidate.get('last_name', 'Unknown') or 'Unknown')}"
    experience = float(candidate.get('total_years_experience') or 0)
    
    parts.append(f"{name} has {experience:.1f} years of total experience.")
    
    # Position summary
    position_titles = candidate.get('position_titles')
    if position_titles is not None and position_titles:
        parts.append(generate_position_summary(position_titles))
    
    # Skills summary
    skills = candidate.get('skills')
    if skills is not None and skills:
        parts.append(generate_skills_summary(skills))
    
    # Experience match
    if query_params.experience_years:
        req_exp = query_params.experience_years
        if experience >= req_exp:
            parts.append(f"Meets the required {req_exp}+ years of experience.")
        else:
            parts.append(f"Has less than the requested {req_exp} years of experience.")
    
    # Semantic match quality
    semantic_quality = get_score_quality(scores.semantic_score)
    parts.append(f"Has a {semantic_quality} semantic match ({scores.semantic_score:.2f}) with the search query.")
    
    # Keyword match quality
    if scores.mn_keyword_score > 0.5 or scores.en_keyword_score > 0.5:
        parts.append(f"Contains many of the exact keywords from the query " +
                    f"(MN: {scores.mn_keyword_score:.2f}, EN: {scores.en_keyword_score:.2f}).")
    
    # Job title match - if extracted from query
    if query_params.job_title and position_titles:
        job_title_lower = query_params.job_title.lower()
        matching_titles = [
            title for title in position_titles
            if title and job_title_lower in title.lower()
        ]
        
        if matching_titles:
            parts.append(f"Position title matches the search query: {matching_titles[0]}.")
    
    # Industry match - if extracted from query
    if query_params.industry and position_titles:
        # Simple check for industry match in position titles
        # In a real application, you'd want to check company_industry field
        industry_lower = query_params.industry.lower()
        if any(industry_lower in title.lower() for title in position_titles if title):
            parts.append(f"Experience in the {query_params.industry} industry.")
    
    return " ".join(parts)