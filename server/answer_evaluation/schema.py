from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class EvaluateAnswerRequest(BaseModel):
    """Request to evaluate an interview answer."""
    interview_id: str
    question_index: int
    question: str
    answer: str
    question_category: str
    evaluation_rubric: Optional[Dict[str, str]] = None


class AnswerEvaluationResponse(BaseModel):
    """Response from answer evaluation."""
    id: str
    interview_id: str
    question_index: int
    
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    
    strengths: List[str]
    weaknesses: List[str]
    follow_up_suggestions: List[str]
    
    evaluation_model: str
    evaluation_timestamp: datetime
    evaluation_duration_ms: int
    token_usage: int


class GetAnswerEvaluationRequest(BaseModel):
    """Request to get an answer evaluation."""
    evaluation_id: str
