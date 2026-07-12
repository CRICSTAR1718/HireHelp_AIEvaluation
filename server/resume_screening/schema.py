from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class CriteriaMatch(BaseModel):
    """Single criteria match result."""
    criterion: str
    meets: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class ScreenResumeRequest(BaseModel):
    """Request to screen a resume against a job."""
    resume_id: str
    job_id: str
    job_description: str
    required_skills: List[str]
    required_experience_years: Optional[float] = None
    required_education: Optional[str] = None


class ScreenedResumeResponse(BaseModel):
    """Response from resume screening."""
    id: str
    resume_id: str
    job_id: str
    
    meets_requirements: bool
    screening_reasoning: str
    screening_score: float = Field(ge=0.0, le=1.0)
    
    criteria_match: List[CriteriaMatch]
    
    screening_model: str
    screening_timestamp: datetime
    screening_duration_ms: int
    token_usage: int


class GetScreeningRequest(BaseModel):
    """Request to get a screening result."""
    screening_id: str
