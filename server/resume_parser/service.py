import json
import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from jinja2 import Template
import httpx
import pdfplumber
from ..llm.client import LLMClient
from ..config.settings import settings
from ..common.exceptions import LLMProviderError, ConfidenceThresholdError
from ..database.models import ParsedResume
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
        self._last_prompt = None
    
    def _load_prompt_template(self, prompt_name: str = "resume_parsing.txt") -> str:
        """Load a prompt template from the prompts directory."""
        try:
            with open(f"server/prompts/{prompt_name}", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt template {prompt_name}: {str(e)}")
            raise LLMProviderError(f"Failed to load prompt template {prompt_name}: {str(e)}")
    
    def _extract_text_from_file(self, file_url: str, file_type: str) -> str:
        """
        Extract text from resume file.
        
        Downloads the file from the given URL and extracts text based on file type.
        Currently supports PDF via pdfplumber.
        
        Args:
            file_url: Public URL to the resume file (e.g., Supabase storage)
            file_type: File type (currently only 'pdf' supported)
        
        Returns:
            Extracted text content
        
        Raises:
            LLMProviderError: If download fails, file is corrupt, or unsupported type
        """
        if file_type.lower() != "pdf":
            raise LLMProviderError(f"Unsupported file type: {file_type}. Only PDF is currently supported.")
        
        try:
            # Download the file from the public URL
            logger.info(f"Downloading resume from {file_url}")
            response = httpx.get(file_url, timeout=30.0)
            response.raise_for_status()
            
            # Save to temporary file for pdfplumber
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(response.content)
                temp_path = temp_file.name
            
            try:
                # Extract text using pdfplumber
                text_parts = []
                with pdfplumber.open(temp_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text_parts.append(page_text)
                
                extracted_text = "\n".join(text_parts)
                
                logger.info(f"DEBUG: Extracted text length: {len(extracted_text)} characters")
                logger.info(f"DEBUG: Extracted text preview (first 1000 chars): {extracted_text[:1000]}")
                logger.info(f"DEBUG: Extracted text preview (last 500 chars): {extracted_text[-500:]}")
                
                if not extracted_text or len(extracted_text.strip()) < 50:
                    logger.error(f"DEBUG: Extracted text is too short or empty. Length: {len(extracted_text) if extracted_text else 0}")
                    raise LLMProviderError(
                        f"Extracted text is too short or empty. The file may be corrupt or image-based PDF."
                    )
                
                logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF")
                return extracted_text
                
            finally:
                # Clean up temporary file
                os.unlink(temp_path)
                
        except httpx.HTTPStatusError as e:
            raise LLMProviderError(f"Failed to download resume from {file_url}: {str(e)}")
        except Exception as e:
            raise LLMProviderError(f"Failed to extract text from PDF: {str(e)}")
    
    @staticmethod
    def _extract_json(response_text: str) -> Dict[str, Any]:
        """Extract and parse a JSON object from an LLM response."""
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}") + 1
        if start_idx == -1 or end_idx == 0:
            raise ValueError("No JSON object found in response")
        return json.loads(response_text[start_idx:end_idx])
    
    def _get_default_response(self) -> Dict[str, Any]:
        """Return a default response structure when parsing fails completely."""
        return {
            "personal_info": {
                "full_name": {"value": None, "confidence": 0.0},
                "email": {"value": None, "confidence": 0.0},
                "phone": {"value": None, "confidence": 0.0},
                "location": {"value": None, "confidence": 0.0}
            },
            "experience": {
                "total_years": {"value": 0.0, "confidence": 0.0},
                "work_history": []
            },
            "education": [],
            "skills": {
                "skills": [],
                "overall_confidence": 0.0
            },
            "needs_human_review": True,
            "parsing_notes": "Failed to parse LLM response - requires manual review"
        }

    def _parse_llm_response(self, response_text: str, finish_reason: Optional[str] = None) -> Dict[str, Any]:
        """Parse the LLM response, retrying once with a JSON-only repair prompt."""
        logger.info(f"DEBUG: _parse_llm_response called with response_text length: {len(response_text)}, finish_reason={finish_reason}")
        logger.info(f"DEBUG: Full raw response text: {response_text}")

        truncated = bool(finish_reason) and "MAX_TOKENS" in finish_reason.upper()

        if truncated:
            logger.warning(
                "Resume parsing response truncated by Gemini (finish_reason=%s), retrying with larger max_tokens",
                finish_reason,
            )
            try:
                retry_response = self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": self._last_prompt}],
                    max_tokens=settings.LLM_MAX_TOKENS_RESUME_PARSING * 2,
                )
                if retry_response.get("finish_reason") and "MAX_TOKENS" in retry_response["finish_reason"].upper():
                    logger.error("Still truncated after retry with doubled max_tokens — resume content likely too large")
                return self._extract_json(retry_response["content"])
            except Exception as retry_error:
                logger.error("Retry after truncation failed: %s", retry_error)
                return self._get_default_response()

        try:
            parsed = self._extract_json(response_text)
            logger.info(f"DEBUG: Successfully parsed JSON. Keys: {list(parsed.keys())}")
            return parsed
        except (json.JSONDecodeError, ValueError) as initial_error:
            logger.warning("Malformed JSON from resume parser LLM: %s", initial_error)
            logger.error(f"DEBUG: JSON parsing failed. Error type: {type(initial_error).__name__}, Error: {initial_error}")
            try:
                repair_template = Template(self._load_prompt_template("json_repair.txt"))
                repair_prompt = repair_template.render(malformed_response=response_text)
                logger.info("Attempting JSON repair...")
                repair_response = self.llm_client.chat_completion(
                    messages=[{"role": "user", "content": repair_prompt}],
                    temperature=0,
                    max_tokens=settings.LLM_MAX_TOKENS_RESUME_PARSING,
                )
                logger.info(f"Repair response length: {len(repair_response['content'])}")
                return self._extract_json(repair_response["content"])
            except Exception as repair_error:
                logger.error(
                    "Failed to parse LLM response after JSON repair: initial=%s repair=%s",
                    initial_error, repair_error,
                )
                logger.warning("Returning default empty structure due to parsing failure")
                return self._get_default_response()
    
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
        
        # Normalize education data - handle string graduation_year values like "Present"
        normalized_education = []
        for entry in education_data:
            normalized_entry = entry.copy()
            grad_year = normalized_entry.get("graduation_year")
            if isinstance(grad_year, str):
                # Convert "Present" or other non-numeric strings to None
                if grad_year.lower() in ["present", "ongoing", "pursuing", "current"]:
                    normalized_entry["graduation_year"] = None
                else:
                    # Try to parse as integer
                    try:
                        normalized_entry["graduation_year"] = int(grad_year)
                    except (ValueError, TypeError):
                        normalized_entry["graduation_year"] = None
            normalized_education.append(normalized_entry)
        
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
            education=[EducationEntry(**entry) for entry in normalized_education],
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
            self._last_prompt = prompt
            
            logger.info(f"DEBUG: Generated prompt length: {len(prompt)} characters")
            logger.info(f"DEBUG: Generated prompt preview (first 500 chars): {prompt[:500]}")
            logger.info(f"DEBUG: Resume text in prompt length: {len(raw_text)} characters")
            
            # Call LLM
            logger.info(f"DEBUG: Calling LLM with max_tokens={settings.LLM_MAX_TOKENS_RESUME_PARSING}")
            llm_response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=settings.LLM_MAX_TOKENS_RESUME_PARSING,
            )
            logger.info(f"DEBUG: LLM response received. Content length: {len(llm_response.get('content', ''))}")
            logger.info(f"DEBUG: LLM finish_reason: {llm_response.get('finish_reason')}")
            logger.info(f"DEBUG: Raw LLM response preview (first 500 chars): {llm_response.get('content', '')[:500]}")
            
            # Parse LLM response
            parsed_data = self._parse_llm_response(
                llm_response["content"],
                finish_reason=llm_response.get("finish_reason"),
            )
            
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
