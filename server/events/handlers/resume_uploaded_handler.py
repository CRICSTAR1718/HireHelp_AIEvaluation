from typing import Dict, Any
import logging
from ...common.exceptions import AIServiceException

logger = logging.getLogger(__name__)


async def handle_resume_uploaded(payload: Dict[str, Any]):
    """
    Handle ResumeUploaded event from candidate-service.
    Triggers the resume parsing pipeline.
    
    Expected payload:
    {
        "resume_id": "string",
        "candidate_id": "string",
        "file_url": "string",
        "file_type": "string",
        "uploaded_at": "string"
    }
    """
    try:
        resume_id = payload.get('resume_id')
        candidate_id = payload.get('candidate_id')
        file_url = payload.get('file_url')
        
        if not all([resume_id, candidate_id, file_url]):
            logger.error(f"Invalid ResumeUploaded payload: {payload}")
            return
        
        logger.info(f"Processing ResumeUploaded event for resume {resume_id}")
        
        # Import here to avoid circular dependencies
        from ...resume_parser.service import ResumeParserService
        
        parser_service = ResumeParserService()
        
        # Trigger resume parsing
        await parser_service.parse_resume(
            resume_id=resume_id,
            candidate_id=candidate_id,
            file_url=file_url
        )
        
        logger.info(f"Successfully triggered parsing for resume {resume_id}")
        
    except Exception as e:
        logger.error(f"Error handling ResumeUploaded event: {str(e)}", exc_info=True)
        raise AIServiceException(f"Failed to handle ResumeUploaded event: {str(e)}")
