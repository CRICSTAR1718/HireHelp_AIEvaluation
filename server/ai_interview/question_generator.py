import json
import logging
from typing import List, Dict, Any
from jinja2 import Template
from ..llm.client import LLMClient
from ..config.settings import settings
from ..common.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class QuestionGenerator:
    """Generates interview questions based on resume and job description."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def _load_prompt_template(self) -> str:
        """Load the interview questions prompt template."""
        try:
            with open("server/prompts/interview_questions.txt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt template: {str(e)}")
            raise LLMProviderError(f"Failed to load prompt template: {str(e)}")
    
    def generate_questions(
        self,
        resume_text: str,
        job_description: str,
        role_title: str,
        experience_level: str = "mid",
        focus_areas: List[str] = None,
        num_questions: int = 6
    ) -> List[Dict[str, Any]]:
        """
        Generate interview questions.
        
        Args:
            resume_text: Candidate's resume text
            job_description: Job description
            role_title: Job title
            experience_level: junior, mid, senior
            focus_areas: Areas to focus on
            num_questions: Number of questions to generate
        
        Returns:
            List of question objects with metadata
        """
        try:
            template_str = self._load_prompt_template()
            template = Template(template_str)
            
            focus_areas_str = ", ".join(focus_areas) if focus_areas else "technical and behavioral"
            
            prompt = template.render(
                resume_text=resume_text,
                job_description=job_description,
                role_title=role_title,
                experience_level=experience_level,
                focus_areas=focus_areas_str
            )
            
            llm_response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            parsed_response = self._parse_llm_response(llm_response["content"])
            
            questions = parsed_response.get("questions", [])
            
            # Limit to requested number
            if len(questions) > num_questions:
                questions = questions[:num_questions]
            
            logger.info(f"Generated {len(questions)} interview questions for {role_title}")
            return questions
            
        except Exception as e:
            logger.error(f"Failed to generate interview questions: {str(e)}")
            raise LLMProviderError(f"Failed to generate interview questions: {str(e)}")
    
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
