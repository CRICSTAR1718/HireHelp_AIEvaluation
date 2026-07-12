from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import ExtractSkillsRequest, SkillExtractionResponse, GetSkillExtractionRequest
from .service import SkillExtractionService

router = APIRouter()
extraction_service = SkillExtractionService()


@router.post("/extract", response_model=SkillExtractionResponse, status_code=status.HTTP_201_CREATED)
async def extract_skills(
    request: ExtractSkillsRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Extract skills from text (resume or job description).
    
    Identifies and categorizes skills with confidence scores.
    """
    try:
        result = await extraction_service.extract_skills(
            request=request,
            db=db
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract skills: {str(e)}"
        )


@router.get("/{extraction_id}", response_model=SkillExtractionResponse)
async def get_skill_extraction(
    extraction_id: str,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Retrieve a skill extraction result.
    
    Returns the extracted skills with categories and confidence scores.
    """
    try:
        result = extraction_service.get_skill_extraction(extraction_id, db)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Skill extraction not found: {extraction_id}"
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve skill extraction: {str(e)}"
        )
