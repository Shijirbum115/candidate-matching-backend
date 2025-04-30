# Candidate related models
"""Candidate data models."""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field


class CandidateBase(BaseModel):
    """Base model for candidate data."""
    
    id: int
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    total_years_experience: Optional[float] = None
    

class CandidateExperience(BaseModel):
    """Candidate work experience model."""
    
    id: int
    candidate_id: int
    company_name: Optional[str] = None
    company_industry: Optional[str] = None
    position_title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    duration_years: Optional[float] = None
    work_description: Optional[str] = None
    work_description_english: Optional[str] = None
    work_field: Optional[str] = None


class CandidateSkill(BaseModel):
    """Candidate skill model."""
    
    id: int
    candidate_id: int
    skill_name: str


class CandidateEducation(BaseModel):
    """Candidate education model."""
    
    id: int
    candidate_id: int
    institution: Optional[str] = None
    degree_name: Optional[str] = None
    degree_id: Optional[int] = None
    field_of_study: Optional[str] = None
    gpa: Optional[float] = None
    country_id: Optional[int] = None
    graduation_year: Optional[int] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    university_rank: Optional[int] = None


class CandidateDetail(CandidateBase):
    """Detailed candidate model including related data."""
    
    experiences: List[CandidateExperience] = []
    skills: List[str] = []
    education: List[CandidateEducation] = []