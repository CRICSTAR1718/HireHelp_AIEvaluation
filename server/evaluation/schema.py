from pydantic import BaseModel
from typing import List


class EvaluationRequest(BaseModel):
    application_id: str
    candidate_id: str
    job_id: str
    resume_url: str
    job_description: str


class EvaluationResponse(BaseModel):
    application_id: str
    fitment_score: float
    recommendation: str
    matched_skills: List[str]
    missing_skills: List[str]
    strengths: List[str]
    weaknesses: List[str]