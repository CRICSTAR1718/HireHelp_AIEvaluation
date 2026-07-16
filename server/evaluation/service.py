import logging
from sqlalchemy.orm import Session
from ..resume_parser.service import ResumeParserService
from ..fitment_score.service import FitmentScoreService
from ..resume_parser.schema import ParsedResumeResponse
from .schema import EvaluationRequest, EvaluationResponse

logger = logging.getLogger(__name__)


class EvaluationService:
    """Orchestrates the complete resume evaluation pipeline."""

    def __init__(self):
        # Instantiate services only once
        self.resume_parser_service = ResumeParserService()
        self.fitment_score_service = FitmentScoreService()

    async def evaluate(self, request: EvaluationRequest, db: Session) -> EvaluationResponse:
        """
        Complete evaluation pipeline.

        1. Parse Resume
        2. Calculate Fitment Score
        3. Return Evaluation Response
        """
        # Step 1: Parse Resume
        resume_id = f"resume_{request.candidate_id}_{request.application_id}"
        parsed_resume: ParsedResumeResponse = await self.resume_parser_service.parse_resume(
            resume_id=resume_id,
            candidate_id=request.candidate_id,
            file_url=request.resume_url,
            file_type="pdf",
            db=db,
        )

        # Step 2: Calculate Fitment Score
        fitment_result = await self.fitment_score_service.calculate_fitment_from_parsed_resume(
            parsed_resume=parsed_resume,
            job_description=request.job_description,
            job_id=request.job_id,
            candidate_id=request.candidate_id,
            resume_id=resume_id,
            required_skills=request.required_skills or [],
            required_experience_years=request.required_experience_years or 0,
            db=db,
        )

        # Step 3: Build Evaluation Response
        return EvaluationResponse(
            application_id=request.application_id,
            fitment_score=fitment_result.overall_score * 100,  # Convert to percentage
            recommendation=fitment_result.recommendations,
            matched_skills=self._extract_matched_skills(fitment_result),
            missing_skills=self._extract_missing_skills(fitment_result),
            strengths=fitment_result.strengths,
            weaknesses=fitment_result.weaknesses,
        )

    def _extract_matched_skills(self, fitment_result) -> list[str]:
        """Extract matched skills from fitment result."""
        # Extract from skills reasoning - parse the LLM response for mentioned skills
        # This is a simplified extraction - in production, use more sophisticated parsing
        reasoning = fitment_result.skills_reasoning.lower()
        # This is a placeholder - actual implementation would parse the reasoning text
        # For now, return empty list as the fitment service doesn't explicitly return this
        return []

    def _extract_missing_skills(self, fitment_result) -> list[str]:
        """Extract missing skills from fitment result."""
        # Extract from skills reasoning - parse the LLM response for missing skills
        # This is a simplified extraction - in production, use more sophisticated parsing
        reasoning = fitment_result.skills_reasoning.lower()
        # This is a placeholder - actual implementation would parse the reasoning text
        # For now, return empty list as the fitment service doesn't explicitly return this
        return []