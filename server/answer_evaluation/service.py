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
from ..database.models import AnswerEvaluation
from .schema import EvaluateAnswerRequest, AnswerEvaluationResponse

logger = logging.getLogger(__name__)


class AnswerEvaluationService:
    """Service for evaluating interview answers using LLM."""
    
    def __init__(self):
        self.llm_client = LLMClient()
    
    def _load_prompt_template(self) -> str:
        """Load the answer evaluation prompt template."""
        return """
You are an expert interview evaluator. Evaluate the candidate's answer to the following interview question.

Question:
{{question}}

Question Category: {{category}}

Candidate's Answer:
{{answer}}

{% if rubric %}
Evaluation Rubric:
Excellent: {{rubric.get('excellent', 'N/A')}}
Good: {{rubric.get('good', 'N/A')}}
Fair: {{rubric.get('fair', 'N/A')}}
Poor: {{rubric.get('poor', 'N/A')}}
{% endif %}

Evaluate the answer on a scale of 0.0 to 1.0 and provide:
1. A score (0.0-1.0)
2. Detailed reasoning for the score
3. Strengths identified in the answer
4. Weaknesses or areas for improvement
5. Suggested follow-up questions

Respond in JSON format:
{
  "score": 0.75,
  "reasoning": "The candidate demonstrated good understanding but missed some key points...",
  "strengths": ["Clear explanation", "Good examples"],
  "weaknesses": ["Lack of depth", "Missed key concept"],
  "follow_up_suggestions": ["Can you elaborate on...", "How would you handle..."]
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
        evaluation_id: str,
        request: EvaluateAnswerRequest,
        evaluation_metadata: Dict[str, Any]
    ) -> AnswerEvaluationResponse:
        """Convert parsed LLM response to Pydantic schema."""
        return AnswerEvaluationResponse(
            id=evaluation_id,
            interview_id=request.interview_id,
            question_index=request.question_index,
            score=parsed_data.get("score", 0.0),
            reasoning=parsed_data.get("reasoning", ""),
            strengths=parsed_data.get("strengths", []),
            weaknesses=parsed_data.get("weaknesses", []),
            follow_up_suggestions=parsed_data.get("follow_up_suggestions", []),
            evaluation_model=evaluation_metadata.get("model"),
            evaluation_timestamp=evaluation_metadata.get("timestamp"),
            evaluation_duration_ms=evaluation_metadata.get("duration_ms"),
            token_usage=evaluation_metadata.get("token_usage")
        )
    
    def _save_to_database(self, db: Session, evaluation_response: AnswerEvaluationResponse) -> Optional[AnswerEvaluation]:
        """Save answer evaluation to database. Returns None if save fails (e.g., foreign key violation)."""
        try:
            db_evaluation = AnswerEvaluation(
                id=evaluation_response.id,
                interview_id=evaluation_response.interview_id,
                question_index=evaluation_response.question_index,
                score=evaluation_response.score,
                reasoning=evaluation_response.reasoning,
                strengths=evaluation_response.strengths,
                weaknesses=evaluation_response.weaknesses,
                follow_up_suggestions=evaluation_response.follow_up_suggestions,
                evaluation_model=evaluation_response.evaluation_model,
                evaluation_duration_ms=evaluation_response.evaluation_duration_ms,
                token_usage=evaluation_response.token_usage
            )
            
            db.add(db_evaluation)
            db.commit()
            db.refresh(db_evaluation)
            
            return db_evaluation
        except Exception as e:
            logger.warning(f"Failed to save answer evaluation to database (interview_id may not exist): {str(e)}")
            db.rollback()
            return None
    
    async def evaluate_answer(
        self,
        request: EvaluateAnswerRequest,
        db: Optional[Session] = None
    ) -> AnswerEvaluationResponse:
        """
        Evaluate an interview answer.
        
        Args:
            request: Answer evaluation request
            db: Database session
        
        Returns:
            AnswerEvaluationResponse with evaluation results
        """
        start_time = time.time()
        evaluation_id = f"evaluation_{uuid.uuid4().hex}"
        
        try:
            # Load and render prompt
            template_str = self._load_prompt_template()
            template = Template(template_str)
            prompt = template.render(
                question=request.question,
                category=request.question_category,
                answer=request.answer,
                rubric=request.evaluation_rubric
            )
            
            # Call LLM
            llm_response = self.llm_client.chat_completion(
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse LLM response
            parsed_data = self._parse_llm_response(llm_response["content"])
            
            # Build response
            evaluation_metadata = {
                "model": settings.LLM_MODEL,
                "timestamp": time.time(),
                "duration_ms": llm_response.get("latency_ms", 0),
                "token_usage": llm_response.get("token_usage", {}).get("total_tokens", 0)
            }
            
            evaluation_response = self._convert_to_schema(
                parsed_data, evaluation_id, request, evaluation_metadata
            )
            
            # Save to database
            if db:
                self._save_to_database(db, evaluation_response)
            
            logger.info(f"Successfully evaluated answer for interview {request.interview_id}, question {request.question_index}")
            return evaluation_response
            
        except Exception as e:
            logger.error(f"Failed to evaluate answer: {str(e)}")
            raise LLMProviderError(f"Failed to evaluate answer: {str(e)}")
    
    def get_answer_evaluation(self, evaluation_id: str, db: Session) -> Optional[AnswerEvaluationResponse]:
        """
        Retrieve an answer evaluation from database.
        
        Args:
            evaluation_id: Evaluation identifier
            db: Database session
        
        Returns:
            AnswerEvaluationResponse or None if not found
        """
        try:
            db_evaluation = db.query(AnswerEvaluation).filter(
                AnswerEvaluation.id == evaluation_id
            ).first()
            
            if not db_evaluation:
                return None
            
            return AnswerEvaluationResponse(
                id=db_evaluation.id,
                interview_id=db_evaluation.interview_id,
                question_index=db_evaluation.question_index,
                score=db_evaluation.score,
                reasoning=db_evaluation.reasoning,
                strengths=db_evaluation.strengths or [],
                weaknesses=db_evaluation.weaknesses or [],
                follow_up_suggestions=db_evaluation.follow_up_suggestions or [],
                evaluation_model=db_evaluation.evaluation_model,
                evaluation_timestamp=db_evaluation.evaluation_timestamp,
                evaluation_duration_ms=db_evaluation.evaluation_duration_ms or 0,
                token_usage=db_evaluation.token_usage or 0
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve answer evaluation {evaluation_id}: {str(e)}")
            raise
