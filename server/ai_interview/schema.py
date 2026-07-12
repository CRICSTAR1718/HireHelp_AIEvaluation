from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class StartInterviewRequest(BaseModel):
    """Request to start an AI interview."""
    candidate_id: str
    job_id: str
    resume_id: str
    job_description: str
    role_title: str
    experience_level: str = "mid"
    focus_areas: Optional[List[str]] = None
    num_questions: int = Field(default=6, ge=3, le=10)


class SubmitAnswerRequest(BaseModel):
    """Request to submit an interview answer."""
    interview_id: str
    answer: str
    answer_metadata: Optional[Dict[str, Any]] = None


class Question(BaseModel):
    """Interview question."""
    question: str
    category: str
    competency_level: str
    assesses: str
    evaluation_rubric: Dict[str, str]


class InterviewResponse(BaseModel):
    """Response from interview operations."""
    id: str
    candidate_id: str
    job_id: str
    
    status: str
    current_question_index: int
    total_questions: int
    
    questions: List[Question]
    answers: List[Dict[str, Any]]
    
    current_question: Optional[Question] = None
    
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    interview_model: str
    created_at: datetime


class GetInterviewRequest(BaseModel):
    """Request to get an interview."""
    interview_id: str
