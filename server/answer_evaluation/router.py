from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import EvaluateAnswerRequest, AnswerEvaluationResponse, GetAnswerEvaluationRequest
from .service import AnswerEvaluationService

router = APIRouter()
evaluation_service = AnswerEvaluationService()


@router.post("/evaluate", response_model=AnswerEvaluationResponse, status_code=status.HTTP_201_CREATED)
async def evaluate_answer(
    request: EvaluateAnswerRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Evaluate an interview answer using AI.
    
    Provides score, reasoning, strengths, weaknesses, and follow-up suggestions.
    """
    try:
        result = await evaluation_service.evaluate_answer(
            request=request,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate answer: {str(e)}"
        )


@router.get("/{evaluation_id}", response_model=AnswerEvaluationResponse)
async def get_answer_evaluation(
    evaluation_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Retrieve an answer evaluation.
    
    Returns the evaluation with score, reasoning, and feedback.
    """
    try:
        result = evaluation_service.get_answer_evaluation(evaluation_id, db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Answer evaluation not found: {evaluation_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve answer evaluation: {str(e)}"
        )
