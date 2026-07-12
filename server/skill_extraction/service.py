import json
import time
import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from jinja2 import Template
from ..llm.client import LLMClient
from ..config.settings import settings
from ..common.exceptions import LLMProviderError
from ..database.models import SkillExtraction
from .schema import ExtractSkillsRequest, SkillExtractionResponse, Skill

logger = logging.getLogger(__name__)


class SkillExtractionService:
    """Service for extracting skills from resumes and job descriptions."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def _load_prompt_template(self) -> str:
        """Load the skill extraction prompt template."""
        # Inline prompt for skill extraction
        return """
You are an expert at extracting skills from text.

Extract all skills from the following text and categorize them into:
- technical (programming languages, frameworks, tools)
- soft (communication, leadership, teamwork)
- language (spoken languages)
- certification (certifications, licenses)
- domain (industry-specific knowledge)

For each skill, provide:
- skill_name: The name of the skill
- category: One of the categories above
- confidence: How confident you are (0.0-1.0)
- context: Where in the text this skill was mentioned (optional)

Text:
{{text}}

Respond in JSON format:
{
  "skills": [
    {
      "skill_name": "Python",
      "category": "technical",
      "confidence": 0.95,
      "context": "mentioned in work experience"
    }
  ]
}
"""
    
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
    
    def _convert_to_schema(
        self,
        parsed_data: Dict[str, Any],
        extraction_id: str,
        request: ExtractSkillsRequest,
        extraction_metadata: Dict[str, Any]
    ) -> SkillExtractionResponse:
        """Convert parsed LLM response to Pydantic schema."""
        skills = [Skill(**skill) for skill in parsed_data.get("skills", [])]
        
        # Filter by focus categories if specified
        if request.focus_categories:
            skills = [s for s in skills if s.category in request.focus_categories]
        
        return SkillExtractionResponse(
            id=extraction_id,
            source_type=request.source_type,
            source_id=request.source_id,
            skills=skills,
            total_skills=len(skills),
            extraction_model=extraction_metadata.get("model"),
            extraction_timestamp=extraction_metadata.get("timestamp"),
            extraction_duration_ms=extraction_metadata.get("duration_ms"),
            token_usage=extraction_metadata.get("token_usage")
        )
    
    def _save_to_database(self, db: Session, extraction_response: SkillExtractionResponse) -> SkillExtraction:
        """Save skill extraction to database."""
        db_extraction = SkillExtraction(
            id=extraction_response.id,
            source_type=extraction_response.source_type,
            source_id=extraction_response.source_id,
            skills=[skill.dict() for skill in extraction_response.skills],
            extraction_model=extraction_response.extraction_model,
            extraction_duration_ms=extraction_response.extraction_duration_ms,
            token_usage=extraction_response.token_usage
        )
        
        db.add(db_extraction)
        db.commit()
        db.refresh(db_extraction)
        
        return db_extraction
    
    async def extract_skills(
        self,
        request: ExtractSkillsRequest,
        db: Optional[Session] = None
    ) -> SkillExtractionResponse:
        """
        Extract skills from text.
        
        Args:
            request: Skill extraction request
            db: Database session
        
        Returns:
            SkillExtractionResponse with extracted skills
        """
        start_time = time.time()
        extraction_id = f"skill_extraction_{uuid.uuid4().hex}"
        
        try:
            # Load and render prompt
            template_str = self._load_prompt_template()
            template = Template(template_str)
            prompt = template.render(text=request.text)
            
            # Call LLM
            llm_response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse LLM response
            parsed_data = self._parse_llm_response(llm_response["content"])
            
            # Build response
            extraction_metadata = {
                "model": settings.LLM_MODEL,
                "timestamp": time.time(),
                "duration_ms": llm_response.get("latency_ms", 0),
                "token_usage": llm_response.get("token_usage", {}).get("total_tokens", 0)
            }
            
            extraction_response = self._convert_to_schema(
                parsed_data, extraction_id, request, extraction_metadata
            )
            
            # Save to database
            if db:
                self._save_to_database(db, extraction_response)
            
            logger.info(f"Successfully extracted {len(extraction_response.skills)} skills from {request.source_id}")
            return extraction_response
            
        except Exception as e:
            logger.error(f"Failed to extract skills: {str(e)}")
            raise LLMProviderError(f"Failed to extract skills: {str(e)}")
    
    def get_skill_extraction(self, extraction_id: str, db: Session) -> Optional[SkillExtractionResponse]:
        """
        Retrieve a skill extraction from database.
        
        Args:
            extraction_id: Extraction identifier
            db: Database session
        
        Returns:
            SkillExtractionResponse or None if not found
        """
        try:
            db_extraction = db.query(SkillExtraction).filter(
                SkillExtraction.id == extraction_id
            ).first()
            
            if not db_extraction:
                return None
            
            return SkillExtractionResponse(
                id=db_extraction.id,
                source_type=db_extraction.source_type,
                source_id=db_extraction.source_id,
                skills=[Skill(**skill) for skill in (db_extraction.skills or [])],
                total_skills=len(db_extraction.skills or []),
                extraction_model=db_extraction.extraction_model,
                extraction_timestamp=db_extraction.extraction_timestamp,
                extraction_duration_ms=db_extraction.extraction_duration_ms or 0,
                token_usage=db_extraction.token_usage or 0
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve skill extraction {extraction_id}: {str(e)}")
            raise
