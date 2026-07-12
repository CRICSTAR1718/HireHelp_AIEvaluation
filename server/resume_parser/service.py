import json
import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from jinja2 import Template
from ..llm.client import LLMClient
from ..config.settings import settings
from ..common.exceptions import LLMProviderError, ConfidenceThresholdError
from ..database.models import ParsedResume
from ..events.kafka_producer import get_kafka_producer
from .schema import (
    ParsedResumeResponse, PersonalInfo, Experience, 
    EducationEntry, SkillEntry, Skills, ConfidenceField,
    WorkHistoryEntry
)

logger = logging.getLogger(__name__)


class ResumeParserService:
    """Service for parsing resumes using LLM."""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.confidence_threshold = settings.CONFIDENCE_THRESHOLD
    
    def _load_prompt_template(self) -> str:
        """Load the resume parsing prompt template."""
        try:
            with open("server/prompts/resume_parsing.txt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt template: {str(e)}")
            raise LLMProviderError(f"Failed to load prompt template: {str(e)}")
    
    def _extract_text_from_file(self, file_url: str, file_type: str) -> str:
        """
        Extract text from resume file.
        In production, this would use a PDF/text extraction library.
        For now, this is a placeholder.
        """
        # TODO: Implement actual file extraction using PyPDF2, pdfplumber, or similar
        # This would download the file from file_url and extract text
        logger.warning(f"File extraction not implemented for {file_url}")
        return "Sample resume text for parsing"
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse the LLM JSON response."""
        try:
            # Extract JSON from response (in case of extra text)
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in response")
            
            json_str = response_text[start_idx:end_idx]
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            raise LLMProviderError(f"Failed to parse LLM response: {str(e)}")
    
    def _check_confidence_thresholds(self, parsed_data: Dict[str, Any]) -> bool:
        """
        Check if any critical fields are below confidence threshold.
        Returns True if human review is needed.
        """
        needs_review = False
        critical_fields = []
        
        # Check personal info
        personal_info = parsed_data.get("personal_info", {})
        for field, data in personal_info.items():
            if isinstance(data, dict) and data.get("confidence", 1.0) < self.confidence_threshold:
                needs_review = True
                critical_fields.append(f"personal_info.{field}")
        
        # Check skills
        skills = parsed_data.get("skills", {})
        if skills.get("overall_confidence", 1.0) < self.confidence_threshold:
            needs_review = True
            critical_fields.append("skills.overall_confidence")
        
        if needs_review:
            logger.warning(f"Low confidence fields detected: {critical_fields}")
        
        return needs_review
    
    def _convert_to_schema(self, parsed_data: Dict[str, Any], resume_id: str, 
                          candidate_id: str, parsing_metadata: Dict[str, Any]) -> ParsedResumeResponse:
        """Convert parsed LLM response to Pydantic schema."""
        personal_info_data = parsed_data.get("personal_info", {})
        experience_data = parsed_data.get("experience", {})
        education_data = parsed_data.get("education", [])
        skills_data = parsed_data.get("skills", {})
        
        return ParsedResumeResponse(
            id=resume_id,
            candidate_id=candidate_id,
            personal_info=PersonalInfo(
                full_name=ConfidenceField(**personal_info_data.get("full_name", {"value": None, "confidence": 0.0})),
                email=ConfidenceField(**personal_info_data.get("email", {"value": None, "confidence": 0.0})),
                phone=ConfidenceField(**personal_info_data.get("phone", {"value": None, "confidence": 0.0})),
                location=ConfidenceField(**personal_info_data.get("location", {"value": None, "confidence": 0.0}))
            ),
            experience=Experience(
                total_years=ConfidenceField(**experience_data.get("total_years", {"value": None, "confidence": 0.0})),
                work_history=[WorkHistoryEntry(**entry) for entry in experience_data.get("work_history", [])]
            ),
            education=[EducationEntry(**entry) for entry in education_data],
            skills=Skills(
                skills=[SkillEntry(**skill) for skill in skills_data.get("skills", [])],
                overall_confidence=skills_data.get("overall_confidence", 0.0)
            ),
            raw_text=parsing_metadata.get("raw_text"),
            parsing_model=parsing_metadata.get("model"),
            parsing_timestamp=parsing_metadata.get("timestamp"),
            parsing_duration_ms=parsing_metadata.get("duration_ms"),
            token_usage=parsing_metadata.get("token_usage"),
            needs_human_review=parsed_data.get("needs_human_review", False),
            parsing_notes=parsed_data.get("parsing_notes")
        )
    
    def _save_to_database(self, db: Session, parsed_response: ParsedResumeResponse) -> ParsedResume:
        """Save parsed resume to database."""
        db_resume = ParsedResume(
            id=parsed_response.id,
            candidate_id=parsed_response.candidate_id,
            full_name=parsed_response.personal_info.full_name.value,
            full_name_confidence=parsed_response.personal_info.full_name.confidence,
            email=parsed_response.personal_info.email.value,
            email_confidence=parsed_response.personal_info.email.confidence,
            phone=parsed_response.personal_info.phone.value,
            phone_confidence=parsed_response.personal_info.phone.confidence,
            location=parsed_response.personal_info.location.value,
            location_confidence=parsed_response.personal_info.location.confidence,
            total_experience_years=parsed_response.experience.total_years.value,
            total_experience_confidence=parsed_response.experience.total_years.confidence,
            work_history=[entry.dict() for entry in parsed_response.experience.work_history],
            education=[entry.dict() for entry in parsed_response.education],
            skills=[skill.dict() for skill in parsed_response.skills.skills],
            skills_confidence=parsed_response.skills.overall_confidence,
            raw_text=parsed_response.raw_text,
            parsing_model=parsed_response.parsing_model,
            parsing_duration_ms=parsed_response.parsing_duration_ms,
            token_usage=parsed_response.token_usage,
            needs_human_review=1 if parsed_response.needs_human_review else 0
        )
        
        db.add(db_resume)
        db.commit()
        db.refresh(db_resume)
        
        return db_resume
    
    def _publish_event(self, parsed_response: ParsedResumeResponse):
        """Publish ResumeParsed event to Kafka."""
        try:
            producer = get_kafka_producer()
            producer.publish_event(
                topic="resume-parsed",
                event_type="ResumeParsed",
                payload={
                    "resume_id": parsed_response.id,
                    "candidate_id": parsed_response.candidate_id,
                    "needs_human_review": parsed_response.needs_human_review,
                    "parsing_timestamp": parsed_response.parsing_timestamp.isoformat()
                },
                key=parsed_response.id
            )
        except Exception as e:
            logger.error(f"Failed to publish ResumeParsed event: {str(e)}")
    
    async def parse_resume(
        self,
        resume_id: str,
        candidate_id: str,
        file_url: str,
        file_type: str = "pdf",
        db: Optional[Session] = None
    ) -> ParsedResumeResponse:
        """
        Parse a resume using LLM.
        
        Args:
            resume_id: Unique resume identifier
            candidate_id: Candidate identifier
            file_url: URL to resume file
            file_type: File type (pdf, docx, etc.)
            db: Database session (optional)
        
        Returns:
            ParsedResumeResponse with extracted data
        """
        start_time = time.time()
        
        try:
            # Extract text from file
            raw_text = self._extract_text_from_file(file_url, file_type)
            
            # Load and render prompt
            template_str = self._load_prompt_template()
            template = Template(template_str)
            prompt = template.render(resume_text=raw_text)
            
            # Call LLM
            llm_response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse LLM response
            parsed_data = self._parse_llm_response(llm_response["content"])
            
            # Check confidence thresholds
            needs_review = self._check_confidence_thresholds(parsed_data)
            parsed_data["needs_human_review"] = needs_review
            
            # Build response
            parsing_metadata = {
                "raw_text": raw_text,
                "model": settings.LLM_MODEL,
                "timestamp": llm_response.get("timestamp", time.time()),
                "duration_ms": llm_response.get("latency_ms", 0),
                "token_usage": llm_response.get("token_usage", {}).get("total_tokens", 0)
            }
            
            parsed_response = self._convert_to_schema(
                parsed_data, resume_id, candidate_id, parsing_metadata
            )
            
            # Save to database if session provided
            if db:
                self._save_to_database(db, parsed_response)
            
            # Publish event
            self._publish_event(parsed_response)
            
            logger.info(f"Successfully parsed resume {resume_id} for candidate {candidate_id}")
            return parsed_response
            
        except Exception as e:
            logger.error(f"Failed to parse resume {resume_id}: {str(e)}")
            raise LLMProviderError(f"Failed to parse resume: {str(e)}")
    
    def get_parsed_resume(self, resume_id: str, db: Session) -> Optional[ParsedResumeResponse]:
        """
        Retrieve a parsed resume from database.
        
        Args:
            resume_id: Resume identifier
            db: Database session
        
        Returns:
            ParsedResumeResponse or None if not found
        """
        try:
            db_resume = db.query(ParsedResume).filter(
                ParsedResume.id == resume_id
            ).first()
            
            if not db_resume:
                return None
            
            # Convert database model to schema
            return ParsedResumeResponse(
                id=db_resume.id,
                candidate_id=db_resume.candidate_id,
                personal_info=PersonalInfo(
                    full_name=ConfidenceField(value=db_resume.full_name, confidence=db_resume.full_name_confidence or 0.0),
                    email=ConfidenceField(value=db_resume.email, confidence=db_resume.email_confidence or 0.0),
                    phone=ConfidenceField(value=db_resume.phone, confidence=db_resume.phone_confidence or 0.0),
                    location=ConfidenceField(value=db_resume.location, confidence=db_resume.location_confidence or 0.0)
                ),
                experience=Experience(
                    total_years=ConfidenceField(value=db_resume.total_experience_years, confidence=db_resume.total_experience_confidence or 0.0),
                    work_history=[WorkHistoryEntry(**entry) for entry in (db_resume.work_history or [])]
                ),
                education=[EducationEntry(**entry) for entry in (db_resume.education or [])],
                skills=Skills(
                    skills=[SkillEntry(**skill) for skill in (db_resume.skills or [])],
                    overall_confidence=db_resume.skills_confidence or 0.0
                ),
                raw_text=db_resume.raw_text,
                parsing_model=db_resume.parsing_model,
                parsing_timestamp=db_resume.parsing_timestamp,
                parsing_duration_ms=db_resume.parsing_duration_ms or 0,
                token_usage=db_resume.token_usage or 0,
                needs_human_review=bool(db_resume.needs_human_review),
                parsing_notes=None
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve parsed resume {resume_id}: {str(e)}")
            raise
