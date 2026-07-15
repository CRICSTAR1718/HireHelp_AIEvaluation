from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import EvaluationRequest, EvaluationResponse
from .service import EvaluationService

router = APIRouter()
evaluation_service = EvaluationService()


@router.post("", response_model=EvaluationResponse, status_code=status.HTTP_200_OK)
async def evaluate_application(
    request: EvaluationRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Evaluate a candidate's application for a job.
    
    This endpoint orchestrates the complete evaluation pipeline:
    1. Parse the resume
    2. Calculate fitment score
    3. Return evaluation results
    
    Called by recruitment-service when an application is submitted.
    """
    try:
        result = await evaluation_service.evaluate(
            request=request,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate application: {str(e)}"
        )
