from pydantic import BaseModel
from typing import List, Optional


class EvaluationRequest(BaseModel):
    application_id: str
    candidate_id: str
    job_id: str
    resume_url: str
    job_description: str
    required_skills: Optional[List[str]] = None
    required_experience_years: Optional[float] = None


class EvaluationResponse(BaseModel):
    application_id: str
    fitment_score: float
    recommendation: str
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]