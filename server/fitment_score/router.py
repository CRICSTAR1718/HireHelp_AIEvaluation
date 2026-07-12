from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import CalculateFitmentRequest, FitmentScoreResponse, GetFitmentScoreRequest
from .service import FitmentScoreService

router = APIRouter()
fitment_service = FitmentScoreService()


@router.post("/calculate", response_model=FitmentScoreResponse, status_code=status.HTTP_201_CREATED)
async def calculate_fitment(
    request: CalculateFitmentRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Calculate fitment score for a candidate-job pair.
    
    Evaluates candidate fitment across skills, experience, education, and culture fit.
    Every score includes detailed reasoning as per PRD requirements.
    """
    try:
        result = await fitment_service.calculate_fitment(
            request=request,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate fitment score: {str(e)}"
        )


@router.get("/{score_id}", response_model=FitmentScoreResponse)
async def get_fitment_score(
    score_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Retrieve a fitment score.
    
    Returns the detailed fitment analysis including dimension scores and reasoning.
    """
    try:
        result = fitment_service.get_fitment_score(score_id, db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fitment score not found: {score_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve fitment score: {str(e)}"
        )
