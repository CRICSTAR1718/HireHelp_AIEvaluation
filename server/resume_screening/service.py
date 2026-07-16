import json
import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from jinja2 import Template
from ..llm.client import LLMClient
from ..config.settings import settings
from ..common.exceptions import LLMProviderError
from ..database.models import ScreenedResume, ParsedResume
from .schema import (
    ScreenedResumeResponse, CriteriaMatch, 
    ScreenResumeRequest
)

logger = logging.getLogger(__name__)


class ResumeScreeningService:
    """Service for screening resumes against job requirements."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def _load_prompt_template(self) -> str:
        """Load the resume screening prompt template."""
        # For now, construct inline prompt (should move to prompts/ in production)
        return """
You are an expert resume screener. Evaluate the following resume against the job requirements.

Resume:
{{resume_text}}

Job Description:
{{job_description}}

Required Skills:
{{required_skills}}

Required Experience: {{required_experience_years}} years
Required Education: {{required_education}}

Evaluate the candidate against the following criteria:
1. Skills match
2. Experience match
3. Education match
4. Overall fit

For each criterion, provide:
- Whether it meets the requirement (true/false)
- Confidence score (0.0-1.0)
- Brief reasoning

Provide an overall screening score (0.0-1.0) and reasoning.

Respond in JSON format:
{
  "meets_requirements": true,
  "screening_reasoning": "Overall assessment...",
  "screening_score": 0.75,
  "criteria_match": [
    {
      "criterion": "skills",
      "meets": true,
      "confidence": 0.85,
      "reasoning": "Candidate has 8 out of 10 required skills"
    },
    {
      "criterion": "experience",
      "meets": true,
      "confidence": 0.90,
      "reasoning": "5 years of experience vs required 3 years"
    },
    {
      "criterion": "education",
      "meets": false,
      "confidence": 0.95,
      "reasoning": "Missing required degree"
    }
  ]
}
"""
    
    def _get_resume_text(self, resume_id: str, db: Session) -> str:
        """Get parsed resume text from database."""
        resume = db.query(ParsedResume).filter(
            ParsedResume.id == resume_id
        ).first()
        
        if not resume:
            raise ValueError(f"Resume not found: {resume_id}")
        
        # Construct a text summary from parsed data
        text_parts = []
        
        if resume.full_name:
            text_parts.append(f"Name: {resume.full_name}")
        
        if resume.email:
            text_parts.append(f"Email: {resume.email}")
        
        if resume.total_experience_years:
            text_parts.append(f"Total Experience: {resume.total_experience_years} years")
        
        if resume.work_history:
            text_parts.append("\nWork History:")
            for entry in resume.work_history:
                text_parts.append(f"- {entry.get('job_title')} at {entry.get('company_name')}")
                text_parts.append(f"  {entry.get('description', '')}")
        
        if resume.skills:
            text_parts.append("\nSkills:")
            for skill in resume.skills:
                text_parts.append(f"- {skill.get('skill_name')} ({skill.get('category')})")
        
        if resume.education:
            text_parts.append("\nEducation:")
            for entry in resume.education:
                text_parts.append(f"- {entry.get('degree')} in {entry.get('field_of_study')} from {entry.get('institution')}")
        
        return "\n".join(text_parts)
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the LLM JSON response."""
        try:
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            raise LLMProviderError(f"Failed to parse LLM response: {str(e)}")
    
    def _convert_to_schema(self, parsed_data: Dict[str, Any], screening_id: str,
                          resume_id: str, job_id: str, screening_metadata: Dict[str, Any]) -> ScreenedResumeResponse:
        """Convert parsed LLM response to Pydantic schema."""
        criteria_match = [
            CriteriaMatch(**criterion) for criterion in parsed_data.get("criteria_match", [])
        ]
        
        return ScreenedResumeResponse(
            id=screening_id,
            resume_id=resume_id,
            job_id=job_id,
            meets_requirements=parsed_data.get("meets_requirements", False),
            screening_reasoning=parsed_data.get("screening_reasoning", ""),
            screening_score=parsed_data.get("screening_score", 0.0),
            criteria_match=criteria_match,
            screening_model=screening_metadata.get("model"),
            screening_timestamp=screening_metadata.get("timestamp"),
            screening_duration_ms=screening_metadata.get("duration_ms"),
            token_usage=screening_metadata.get("token_usage")
        )
    
    def _save_to_database(self, db: Session, screened_response: ScreenedResumeResponse) -> ScreenedResume:
        """Save screening result to database with upsert logic."""
        # Check for existing row
        db_screening = db.query(ScreenedResume).filter(
            ScreenedResume.id == screened_response.id
        ).first()
        
        if db_screening:
            # Update existing row
            db_screening.resume_id = screened_response.resume_id
            db_screening.job_id = screened_response.job_id
            db_screening.meets_requirements = 1 if screened_response.meets_requirements else 0
            db_screening.screening_reasoning = screened_response.screening_reasoning
            db_screening.screening_score = screened_response.screening_score
            db_screening.criteria_match = [criterion.dict() for criterion in screened_response.criteria_match]
            db_screening.screening_model = screened_response.screening_model
            db_screening.screening_duration_ms = screened_response.screening_duration_ms
            db_screening.token_usage = screened_response.token_usage
            db.commit()
            db.refresh(db_screening)
        else:
            # Insert new row
            db_screening = ScreenedResume(
                id=screened_response.id,
                resume_id=screened_response.resume_id,
                job_id=screened_response.job_id,
                meets_requirements=1 if screened_response.meets_requirements else 0,
                screening_reasoning=screened_response.screening_reasoning,
                screening_score=screened_response.screening_score,
                criteria_match=[criterion.dict() for criterion in screened_response.criteria_match],
                screening_model=screened_response.screening_model,
                screening_duration_ms=screened_response.screening_duration_ms,
                token_usage=screened_response.token_usage
            )
            db.add(db_screening)
            db.commit()
            db.refresh(db_screening)
        
        return db_screening
    
    async def screen_resume(
        self,
        resume_id: str,
        job_id: str,
        job_description: str,
        required_skills: list[str],
        required_experience_years: Optional[float] = None,
        required_education: Optional[str] = None,
        db: Optional[Session] = None
    ) -> ScreenedResumeResponse:
        """
        Screen a resume against job requirements.
        
        Args:
            resume_id: Resume identifier
            job_id: Job identifier
            job_description: Job description text
            required_skills: List of required skills
            required_experience_years: Required years of experience
            required_education: Required education level
            db: Database session
        
        Returns:
            ScreenedResumeResponse with screening results
        """
        start_time = time.time()
        screening_id = f"screening_{resume_id}_{job_id}"
        
        try:
            # Get resume text
            if not db:
                raise ValueError("Database session required")
            resume_text = self._get_resume_text(resume_id, db)
            
            # Load and render prompt
            template_str = self._load_prompt_template()
            template = Template(template_str)
            prompt = template.render(
                resume_text=resume_text,
                job_description=job_description,
                required_skills=", ".join(required_skills),
                required_experience_years=required_experience_years or "Not specified",
                required_education=required_education or "Not specified"
            )
            
            # Call LLM
            llm_response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse LLM response
            parsed_data = self._parse_llm_response(llm_response["content"])
            
            # Build response
            screening_metadata = {
                "model": settings.LLM_MODEL,
                "timestamp": time.time(),
                "duration_ms": llm_response.get("latency_ms", 0),
                "token_usage": llm_response.get("token_usage", {}).get("total_tokens", 0)
            }
            
            screened_response = self._convert_to_schema(
                parsed_data, screening_id, resume_id, job_id, screening_metadata
            )
            
            # Save to database
            self._save_to_database(db, screened_response)
            
            logger.info(f"Successfully screened resume {resume_id} against job {job_id}")
            return screened_response
            
        except Exception as e:
            logger.error(f"Failed to screen resume {resume_id}: {str(e)}")
            raise LLMProviderError(f"Failed to screen resume: {str(e)}")
    
    def get_screening(self, screening_id: str, db: Session) -> Optional[ScreenedResumeResponse]:
        """
        Retrieve a screening result from database.
        
        Args:
            screening_id: Screening identifier
            db: Database session
        
        Returns:
            ScreenedResumeResponse or None if not found
        """
        try:
            db_screening = db.query(ScreenedResume).filter(
                ScreenedResume.id == screening_id
            ).first()
            
            if not db_screening:
                return None
            
            return ScreenedResumeResponse(
                id=db_screening.id,
                resume_id=db_screening.resume_id,
                job_id=db_screening.job_id,
                meets_requirements=bool(db_screening.meets_requirements),
                screening_reasoning=db_screening.screening_reasoning,
                screening_score=db_screening.screening_score,
                criteria_match=[CriteriaMatch(**criterion) for criterion in (db_screening.criteria_match or [])],
                screening_model=db_screening.screening_model,
                screening_timestamp=db_screening.screening_timestamp,
                screening_duration_ms=db_screening.screening_duration_ms or 0,
                token_usage=db_screening.token_usage or 0
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve screening {screening_id}: {str(e)}")
            raise
