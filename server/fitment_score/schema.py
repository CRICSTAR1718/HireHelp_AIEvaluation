from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AIEvaluationSummary(BaseModel):
    """Candidate-facing AI evaluation summary."""
    fit_verdict: str
    consider_because: List[str] = []
    not_consider_because: List[str] = []
    suitable_roles: List[str] = []


class CalculateFitmentRequest(BaseModel):
    """Request to calculate fitment score."""
    candidate_id: str
    job_id: str
    resume_id: str
    job_description: str
    candidate_skills: List[str]
    required_skills: List[str]
    bonus_skills: Optional[List[str]] = None
    candidate_experience_years: float
    required_experience_years: float
    relevant_experience: Optional[List[dict]] = None
    candidate_education: Optional[List[dict]] = None
    required_education: Optional[str] = None
    preferred_education: Optional[List[str]] = None
    career_trajectory: Optional[List[dict]] = None
    job_stability: Optional[float] = None
    growth_indicators: Optional[List[str]] = None


class FitmentScoreResponse(BaseModel):
    """Response from fitment scoring."""
    id: str
    candidate_id: str
    job_id: str
    resume_id: str
    
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_reasoning: str
    
    skills_score: float = Field(ge=0.0, le=1.0)
    skills_reasoning: str
    
    experience_score: float = Field(ge=0.0, le=1.0)
    experience_reasoning: str
    
    education_score: float = Field(ge=0.0, le=1.0)
    education_reasoning: str
    
    culture_fit_score: float = Field(ge=0.0, le=1.0)
    culture_fit_reasoning: str
    
    strengths: List[str]
    weaknesses: List[str]
    recommendations: str

    fit_verdict: Optional[str] = None
    consider_because: List[str] = []
    not_consider_because: List[str] = []
    suitable_roles: List[str] = []

    scoring_model: str
    scoring_timestamp: datetime
    scoring_duration_ms: int
    token_usage: int


class GetFitmentScoreRequest(BaseModel):
    """Request to get a fitment score."""
    score_id: str
