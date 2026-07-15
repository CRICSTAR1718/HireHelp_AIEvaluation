from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConfidenceField(BaseModel):
    """A field with an associated confidence score."""
    value: Optional[str | float] = None
    confidence: float = Field(ge=0.0, le=1.0)


class WorkHistoryEntry(BaseModel):
    """Single work experience entry."""
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class EducationEntry(BaseModel):
    """Single education entry."""
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    confidence: float = Field(ge=0.0, le=1.0)


class SkillEntry(BaseModel):
    """Single skill entry."""
    skill_name: str
    category: str
    confidence: float = Field(ge=0.0, le=1.0)


class PersonalInfo(BaseModel):
    """Parsed personal information."""
    full_name: ConfidenceField
    email: ConfidenceField
    phone: ConfidenceField
    location: ConfidenceField


class Experience(BaseModel):
    """Parsed experience information."""
    total_years: ConfidenceField
    work_history: List[WorkHistoryEntry]


class Skills(BaseModel):
    """Parsed skills information."""
    skills: List[SkillEntry]
    overall_confidence: float = Field(ge=0.0, le=1.0)


class ParseResumeRequest(BaseModel):
    """Request to parse a resume."""
    resume_id: str
    candidate_id: str
    file_url: str
    file_type: Optional[str] = "pdf"


class ParsedResumeResponse(BaseModel):
    """Response from resume parsing."""
    id: str
    candidate_id: str
    
    personal_info: PersonalInfo
    experience: Experience
    education: List[EducationEntry]
    skills: Skills
    
    raw_text: Optional[str] = None
    parsing_model: str
    parsing_timestamp: datetime
    parsing_duration_ms: int
    token_usage: int
    
    needs_human_review: bool
    parsing_notes: Optional[str] = None


class GetParsedResumeRequest(BaseModel):
    """Request to get a parsed resume."""
    resume_id: str
