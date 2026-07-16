import logging
from sqlalchemy.orm import Session
from ..common.exceptions import LLMProviderError
from .schema import EvaluationRequest, EvaluationResponse
from .workflow import EvaluationWorkflow

logger = logging.getLogger(__name__)


class EvaluationService:
    """Orchestrates the complete resume evaluation pipeline using LangGraph."""

    def __init__(self):
        # Initialize LangGraph workflow
        self.workflow = EvaluationWorkflow()

    async def evaluate(self, request: EvaluationRequest, db: Session) -> EvaluationResponse:
        """
        Complete evaluation pipeline using LangGraph workflow.

        The workflow orchestrates:
        1. Parse Resume
        2. Calculate Fitment Score
        3. Return Evaluation Response
        """
        # Prepare initial state for the workflow
        initial_state = {
            "application_id": request.application_id,
            "candidate_id": request.candidate_id,
            "job_id": request.job_id,
            "resume_url": request.resume_url,
            "job_description": request.job_description,
            "required_skills": request.required_skills,
            "required_experience_years": request.required_experience_years,
            "db": db,
            "resume_id": None,
            "parsed_resume": None,
            "fitment_result": None,
            "error": None
        }

        # Run the LangGraph workflow
        final_state = await self.workflow.run(initial_state)

        # Check for errors
        if final_state.get("error"):
            logger.error(f"Evaluation workflow failed: {final_state['error']}")
            raise LLMProviderError(f"Evaluation failed: {final_state['error']}")

        # Extract fitment result
        fitment_result = final_state.get("fitment_result")
        if not fitment_result:
            raise LLMProviderError("Fitment result not produced by workflow")

        # Build Evaluation Response
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