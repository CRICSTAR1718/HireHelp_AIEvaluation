from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class MatchJobRequest(BaseModel):
    """Request to match job description to candidates."""
    job_id: str
    job_description: str
    required_skills: List[str]
    required_experience_years: Optional[float] = None
    required_education: Optional[str] = None
    max_results: int = Field(default=10, ge=1, le=50)


class CandidateMatch(BaseModel):
    """Single candidate match result."""
    candidate_id: str
    resume_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    skills_match_score: float = Field(ge=0.0, le=1.0)
    experience_match_score: float = Field(ge=0.0, le=1.0)
    overall_match_score: float = Field(ge=0.0, le=1.0)
    match_reasoning: str


class JobMatchResponse(BaseModel):
    """Response from job matching."""
    job_id: str
    matches: List[CandidateMatch]
    total_candidates_evaluated: int
    matching_model: str
    matching_timestamp: datetime
