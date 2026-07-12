from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class Skill(BaseModel):
    """Extracted skill with metadata."""
    skill_name: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)
    context: Optional[str] = None


class ExtractSkillsRequest(BaseModel):
    """Request to extract skills from text."""
    source_type: str  # resume, job_description
    source_id: str
    text: str
    focus_categories: Optional[List[str]] = None


class SkillExtractionResponse(BaseModel):
    """Response from skill extraction."""
    id: str
    source_type: str
    source_id: str
    
    skills: List[Skill]
    total_skills: int
    
    extraction_model: str
    extraction_timestamp: datetime
    extraction_duration_ms: int
    token_usage: int


class GetSkillExtractionRequest(BaseModel):
    """Request to get skill extraction."""
    extraction_id: str
