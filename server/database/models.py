from sqlalchemy import Column, String, Float, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from server.config.db import Base


class ParsedResume(Base):
    """Stores parsed resume data with confidence scores."""
    __tablename__ = "parsed_resumes"
    
    id = Column(String, primary_key=True)  # Resume ID from candidate-service
    candidate_id = Column(String, nullable=False, index=True)
    
    # Parsed fields with confidence scores
    full_name = Column(String)
    full_name_confidence = Column(Float)
    email = Column(String)
    email_confidence = Column(Float)
    phone = Column(String)
    phone_confidence = Column(Float)
    location = Column(String)
    location_confidence = Column(Float)
    
    # Experience
    total_experience_years = Column(Float)
    total_experience_confidence = Column(Float)
    work_history = Column(JSON)  # Array of experience entries
    
    # Education
    education = Column(JSON)  # Array of education entries
    
    # Skills
    skills = Column(JSON)  # Array of extracted skills with confidence
    skills_confidence = Column(Float)
    
    # Raw parsing metadata
    raw_text = Column(Text)
    parsing_model = Column(String)
    parsing_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    parsing_duration_ms = Column(Integer)
    token_usage = Column(Integer)
    
    # Flags
    needs_human_review = Column(Integer, default=0)  # Boolean as integer
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ScreenedResume(Base):
    """Stores resume screening results."""
    __tablename__ = "screened_resumes"
    
    id = Column(String, primary_key=True)
    resume_id = Column(String, ForeignKey("parsed_resumes.id"), nullable=False)
    job_id = Column(String, nullable=False, index=True)
    
    # Screening criteria
    meets_requirements = Column(Integer)  # Boolean as integer
    screening_reasoning = Column(Text)
    screening_score = Column(Float)
    
    # Criteria breakdown
    criteria_match = Column(JSON)  # Detailed criteria matching
    
    screening_model = Column(String)
    screening_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    screening_duration_ms = Column(Integer)
    token_usage = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    parsed_resume = relationship("ParsedResume", backref="screenings")


class FitmentScore(Base):
    """Stores candidate-job fitment scores with reasoning."""
    __tablename__ = "fitment_scores"
    
    id = Column(String, primary_key=True)
    candidate_id = Column(String, nullable=False, index=True)
    job_id = Column(String, nullable=False, index=True)
    resume_id = Column(String, ForeignKey("parsed_resumes.id"))
    
    # Overall fitment
    overall_score = Column(Float, nullable=False)
    overall_reasoning = Column(Text, nullable=False)
    
    # Dimension scores
    skills_score = Column(Float)
    skills_reasoning = Column(Text)
    experience_score = Column(Float)
    experience_reasoning = Column(Text)
    education_score = Column(Float)
    education_reasoning = Column(Text)
    culture_fit_score = Column(Float)
    culture_fit_reasoning = Column(Text)
    
    # Scoring metadata
    scoring_model = Column(String)
    scoring_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    scoring_duration_ms = Column(Integer)
    token_usage = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship
    parsed_resume = relationship("ParsedResume", backref="fitment_scores")


class AIInterview(Base):
    """Stores AI interview sessions and state."""
    __tablename__ = "ai_interviews"
    
    id = Column(String, primary_key=True)
    candidate_id = Column(String, nullable=False, index=True)
    job_id = Column(String, nullable=False, index=True)
    
    # Interview state
    status = Column(String, default="pending")  # pending, in_progress, completed, failed
    current_question_index = Column(Integer, default=0)
    total_questions = Column(Integer)
    
    # Questions and answers
    questions = Column(JSON)  # Array of question objects
    answers = Column(JSON)  # Array of answer objects
    
    # Interview metadata
    interview_model = Column(String)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    total_duration_ms = Column(Integer)
    token_usage = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class AnswerEvaluation(Base):
    """Stores evaluated answers from AI interviews."""
    __tablename__ = "answer_evaluations"
    
    id = Column(String, primary_key=True)
    interview_id = Column(String, ForeignKey("ai_interviews.id"), nullable=False)
    question_index = Column(Integer, nullable=False)
    
    # Evaluation results
    score = Column(Float, nullable=False)
    reasoning = Column(Text, nullable=False)
    strengths = Column(JSON)  # Array of identified strengths
    weaknesses = Column(JSON)  # Array of identified weaknesses
    follow_up_suggestions = Column(JSON)  # Array of suggested follow-ups
    
    # Evaluation metadata
    evaluation_model = Column(String)
    evaluation_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    evaluation_duration_ms = Column(Integer)
    token_usage = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationship
    interview = relationship("AIInterview", backref="answer_evaluations")


class SkillExtraction(Base):
    """Stores extracted skills from resumes and job descriptions."""
    __tablename__ = "skill_extractions"
    
    id = Column(String, primary_key=True)
    source_type = Column(String, nullable=False)  # resume, job_description
    source_id = Column(String, nullable=False, index=True)
    
    # Extracted skills
    skills = Column(JSON)  # Array of skill objects with categories and confidence
    extraction_model = Column(String)
    extraction_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    extraction_duration_ms = Column(Integer)
    token_usage = Column(Integer)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
