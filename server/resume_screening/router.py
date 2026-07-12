from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import ScreenResumeRequest, ScreenedResumeResponse, GetScreeningRequest
from .service import ResumeScreeningService

router = APIRouter()
screening_service = ResumeScreeningService()


@router.post("/screen", response_model=ScreenedResumeResponse, status_code=status.HTTP_201_CREATED)
async def screen_resume(
    request: ScreenResumeRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Screen a resume against job requirements.
    
    Evaluates a parsed resume against job requirements including skills,
    experience, and education.
    """
    try:
        result = await screening_service.screen_resume(
            resume_id=request.resume_id,
            job_id=request.job_id,
            job_description=request.job_description,
            required_skills=request.required_skills,
            required_experience_years=request.required_experience_years,
            required_education=request.required_education,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to screen resume: {str(e)}"
        )


@router.get("/{screening_id}", response_model=ScreenedResumeResponse)
async def get_screening(
    screening_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Retrieve a screening result.
    
    Returns the screening evaluation for a resume-job pair.
    """
    try:
        result = screening_service.get_screening(screening_id, db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Screening not found: {screening_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve screening: {str(e)}"
        )
