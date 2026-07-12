from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import StartInterviewRequest, SubmitAnswerRequest, InterviewResponse, GetInterviewRequest
from .service import AIInterviewService

router = APIRouter()
interview_service = AIInterviewService()


@router.post("/start", response_model=InterviewResponse, status_code=status.HTTP_201_CREATED)
async def start_interview(
    request: StartInterviewRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Start an AI-powered interview for a candidate.
    
    Generates interview questions based on the candidate's resume and job requirements.
    """
    try:
        result = await interview_service.start_interview(
            request=request,
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
            detail=f"Failed to start interview: {str(e)}"
        )


@router.post("/answer", response_model=InterviewResponse)
async def submit_answer(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Submit an answer for the current interview question.
    
    Returns the next question or completion status if all questions are answered.
    """
    try:
        result = await interview_service.submit_answer(
            request=request,
            db=db
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(e)}"
        )


@router.get("/{interview_id}", response_model=InterviewResponse)
async def get_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Retrieve an interview session.
    
    Returns the interview state including questions and answers.
    """
    try:
        result = interview_service.get_interview(interview_id, db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview not found: {interview_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve interview: {str(e)}"
        )
