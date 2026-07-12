from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..config.db import get_db
from ..common.middleware.auth import verify_service_token
from .schema import MatchJobRequest, JobMatchResponse
from .service import JobMatchingService

router = APIRouter()
matching_service = JobMatchingService()


@router.post("/match", response_model=JobMatchResponse)
async def match_job(
    request: MatchJobRequest,
    db: Session = Depends(get_db),
    claims: dict = Depends(verify_service_token)
):
    """
    Match job description to candidates using semantic search.
    
    Uses embeddings to find candidates whose resumes are semantically similar
    to the job description.
    """
    try:
        result = await matching_service.match_job(
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
            detail=f"Failed to match job: {str(e)}"
        )
