from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import ParseResumeRequest, ParsedResumeResponse, GetParsedResumeRequest
from .service import ResumeParserService

router = APIRouter()
parser_service = ResumeParserService()


@router.post("/parse", response_model=ParsedResumeResponse, status_code=status.HTTP_201_CREATED)
async def parse_resume(
    request: ParseResumeRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Parse a resume using AI.
    
    This endpoint is called internally by candidate-service when a resume is uploaded.
    It extracts structured information from the resume with confidence scores.
    """
    try:
        result = await parser_service.parse_resume(
            resume_id=request.resume_id,
            candidate_id=request.candidate_id,
            file_url=request.file_url,
            file_type=request.file_type,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse resume: {str(e)}"
        )


@router.get("/{resume_id}", response_model=ParsedResumeResponse)
async def get_parsed_resume(
    resume_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Retrieve a previously parsed resume.
    
    Returns the structured data extracted from the resume including confidence scores.
    """
    try:
        result = parser_service.get_parsed_resume(resume_id, db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parsed resume not found: {resume_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve parsed resume: {str(e)}"
        )
