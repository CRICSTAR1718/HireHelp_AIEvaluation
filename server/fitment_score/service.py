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
from ..database.models import FitmentScore
from ..events.kafka_producer import get_kafka_producer
from .schema import CalculateFitmentRequest, FitmentScoreResponse
from .scoring_engine import ScoringEngine, DimensionScore

logger = logging.getLogger(__name__)


class FitmentScoreService:
    """Service for calculating candidate-job fitment scores."""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.scoring_engine = ScoringEngine()
    
    def _load_prompt_template(self) -> str:
        """Load the fitment scoring prompt template."""
        try:
            with open("server/prompts/fitment_scoring.txt", "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to load prompt template: {str(e)}")
            raise LLMProviderError(f"Failed to load prompt template: {str(e)}")
    
    def _calculate_dimension_scores(
        self,
        request: CalculateFitmentRequest
    ) -> Dict[str, DimensionScore]:
        """Calculate scores for each dimension using scoring engine."""
        dimensions = {}
        
        # Skills score
        dimensions["skills"] = self.scoring_engine.calculate_skills_score(
            candidate_skills=request.candidate_skills,
            required_skills=request.required_skills,
            bonus_skills=request.bonus_skills
        )
        
        # Experience score
        dimensions["experience"] = self.scoring_engine.calculate_experience_score(
            candidate_years=request.candidate_experience_years,
            required_years=request.required_experience_years,
            relevant_experience=request.relevant_experience
        )
        
        # Education score
        dimensions["education"] = self.scoring_engine.calculate_education_score(
            candidate_education=request.candidate_education or [],
            required_education=request.required_education,
            preferred_education=request.preferred_education
        )
        
        # Culture fit score
        dimensions["culture_fit"] = self.scoring_engine.calculate_culture_fit_score(
            career_trajectory=request.career_trajectory,
            job_stability=request.job_stability,
            growth_indicators=request.growth_indicators
        )
        
        return dimensions
    
    def _enhance_with_llm(
        self,
        request: CalculateFitmentRequest,
        dimension_scores: Dict[str, DimensionScore]
    ) -> Dict[str, Any]:
        """
        Use LLM to enhance scoring with detailed reasoning and recommendations.
        This adds the qualitative analysis that pure scoring can't provide.
        """
        template_str = self._load_prompt_template()
        template = Template(template_str)
        
        # Build resume text summary
        resume_summary = f"""
        Skills: {', '.join(request.candidate_skills)}
        Experience: {request.candidate_experience_years} years
        Education: {request.candidate_education}
        """
        
        prompt = template.render(
            resume_text=resume_summary,
            job_description=request.job_description
        )
        
        llm_response = self.llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}]
        )
        
        return self._parse_llm_response(llm_response["content"])
    
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
            # Return empty structure if parsing fails
            return {
                "overall_reasoning": "LLM reasoning unavailable",
                "strengths": [],
                "weaknesses": [],
                "recommendations": "Proceed with human review"
            }
    
    def _convert_to_schema(
        self,
        dimension_scores: Dict[str, DimensionScore],
        llm_enhancement: Dict[str, Any],
        score_id: str,
        request: CalculateFitmentRequest,
        scoring_metadata: Dict[str, Any]
    ) -> FitmentScoreResponse:
        """Convert scores to Pydantic schema."""
        # Calculate overall score
        overall_score = self.scoring_engine.calculate_overall_score(
            skills_score=dimension_scores["skills"].score,
            experience_score=dimension_scores["experience"].score,
            education_score=dimension_scores["education"].score,
            culture_fit_score=dimension_scores["culture_fit"].score
        )
        
        return FitmentScoreResponse(
            id=score_id,
            candidate_id=request.candidate_id,
            job_id=request.job_id,
            resume_id=request.resume_id,
            overall_score=overall_score,
            overall_reasoning=llm_enhancement.get("overall_reasoning", f"Weighted score: {overall_score:.2f}"),
            skills_score=dimension_scores["skills"].score,
            skills_reasoning=dimension_scores["skills"].reasoning,
            experience_score=dimension_scores["experience"].score,
            experience_reasoning=dimension_scores["experience"].reasoning,
            education_score=dimension_scores["education"].score,
            education_reasoning=dimension_scores["education"].reasoning,
            culture_fit_score=dimension_scores["culture_fit"].score,
            culture_fit_reasoning=dimension_scores["culture_fit"].reasoning,
            strengths=llm_enhancement.get("strengths", []),
            weaknesses=llm_enhancement.get("weaknesses", []),
            recommendations=llm_enhancement.get("recommendations", "No specific recommendations"),
            scoring_model=scoring_metadata.get("model"),
            scoring_timestamp=scoring_metadata.get("timestamp"),
            scoring_duration_ms=scoring_metadata.get("duration_ms"),
            token_usage=scoring_metadata.get("token_usage")
        )
    
    def _save_to_database(self, db: Session, fitment_response: FitmentScoreResponse) -> FitmentScore:
        """Save fitment score to database."""
        db_score = FitmentScore(
            id=fitment_response.id,
            candidate_id=fitment_response.candidate_id,
            job_id=fitment_response.job_id,
            resume_id=fitment_response.resume_id,
            overall_score=fitment_response.overall_score,
            overall_reasoning=fitment_response.overall_reasoning,
            skills_score=fitment_response.skills_score,
            skills_reasoning=fitment_response.skills_reasoning,
            experience_score=fitment_response.experience_score,
            experience_reasoning=fitment_response.experience_reasoning,
            education_score=fitment_response.education_score,
            education_reasoning=fitment_response.education_reasoning,
            culture_fit_score=fitment_response.culture_fit_score,
            culture_fit_reasoning=fitment_response.culture_fit_reasoning,
            scoring_model=fitment_response.scoring_model,
            scoring_duration_ms=fitment_response.scoring_duration_ms,
            token_usage=fitment_response.token_usage
        )
        
        db.add(db_score)
        db.commit()
        db.refresh(db_score)
        
        return db_score
    
    def _publish_event(self, fitment_response: FitmentScoreResponse):
        """Publish FitmentScoreCalculated event to Kafka."""
        try:
            producer = get_kafka_producer()
            producer.publish_event(
                topic="fitment-score-calculated",
                event_type="FitmentScoreCalculated",
                payload={
                    "score_id": fitment_response.id,
                    "candidate_id": fitment_response.candidate_id,
                    "job_id": fitment_response.job_id,
                    "overall_score": fitment_response.overall_score,
                    "scoring_timestamp": fitment_response.scoring_timestamp.isoformat()
                },
                key=fitment_response.id
            )
        except Exception as e:
            logger.error(f"Failed to publish FitmentScoreCalculated event: {str(e)}")
    
    async def calculate_fitment(
        self,
        request: CalculateFitmentRequest,
        db: Optional[Session] = None
    ) -> FitmentScoreResponse:
        """
        Calculate fitment score for a candidate-job pair.
        
        Args:
            request: Fitment calculation request
            db: Database session
        
        Returns:
            FitmentScoreResponse with detailed scores and reasoning
        """
        start_time = time.time()
        score_id = f"fitment_{request.candidate_id}_{request.job_id}"
        
        try:
            # Calculate dimension scores using scoring engine
            dimension_scores = self._calculate_dimension_scores(request)
            
            # Enhance with LLM reasoning
            llm_enhancement = self._enhance_with_llm(request, dimension_scores)
            
            # Build response
            scoring_metadata = {
                "model": settings.LLM_MODEL,
                "timestamp": time.time(),
                "duration_ms": 0,  # Will be set at end
                "token_usage": 0
            }
            
            fitment_response = self._convert_to_schema(
                dimension_scores, llm_enhancement, score_id, request, scoring_metadata
            )
            
            # Update metadata
            scoring_metadata["duration_ms"] = int((time.time() - start_time) * 1000)
            fitment_response.scoring_duration_ms = scoring_metadata["duration_ms"]
            
            # Save to database
            if db:
                self._save_to_database(db, fitment_response)
            
            # Publish event
            self._publish_event(fitment_response)
            
            logger.info(f"Successfully calculated fitment score {score_id}")
            return fitment_response
            
        except Exception as e:
            logger.error(f"Failed to calculate fitment score: {str(e)}")
            raise LLMProviderError(f"Failed to calculate fitment score: {str(e)}")
    
    def get_fitment_score(self, score_id: str, db: Session) -> Optional[FitmentScoreResponse]:
        """
        Retrieve a fitment score from database.
        
        Args:
            score_id: Score identifier
            db: Database session
        
        Returns:
            FitmentScoreResponse or None if not found
        """
        try:
            db_score = db.query(FitmentScore).filter(
                FitmentScore.id == score_id
            ).first()
            
            if not db_score:
                return None
            
            return FitmentScoreResponse(
                id=db_score.id,
                candidate_id=db_score.candidate_id,
                job_id=db_score.job_id,
                resume_id=db_score.resume_id,
                overall_score=db_score.overall_score,
                overall_reasoning=db_score.overall_reasoning,
                skills_score=db_score.skills_score,
                skills_reasoning=db_score.skills_reasoning,
                experience_score=db_score.experience_score,
                experience_reasoning=db_score.experience_reasoning,
                education_score=db_score.education_score,
                education_reasoning=db_score.education_reasoning,
                culture_fit_score=db_score.culture_fit_score,
                culture_fit_reasoning=db_score.culture_fit_reasoning,
                strengths=[],
                weaknesses=[],
                recommendations="",
                scoring_model=db_score.scoring_model,
                scoring_timestamp=db_score.scoring_timestamp,
                scoring_duration_ms=db_score.scoring_duration_ms or 0,
                token_usage=db_score.token_usage or 0
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve fitment score {score_id}: {str(e)}")
            raise
