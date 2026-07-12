import httpx
import logging
from typing import Dict, Any, Optional
from ..config.settings import settings

logger = logging.getLogger(__name__)


class CandidateServiceClient:
    """HTTP client for internal communication with candidate-service."""
    
    def __init__(self):
        self.base_url = settings.CANDIDATE_SERVICE_URL
        self.timeout = 30.0
    
    async def get_candidate_profile(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get candidate profile from candidate-service.
        
        Args:
            candidate_id: Candidate identifier
        
        Returns:
            Candidate profile dict or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/candidates/{candidate_id}",
                    headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to get candidate profile: {str(e)}")
            return None
    
    async def get_resume_url(self, resume_id: str) -> Optional[str]:
        """
        Get resume file URL from candidate-service.
        
        Args:
            resume_id: Resume identifier
        
        Returns:
            Resume URL or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/resumes/{resume_id}/url",
                    headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                data = response.json()
                return data.get("url")
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to get resume URL: {str(e)}")
            return None
    
    async def update_candidate_status(self, candidate_id: str, status: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Update candidate status in candidate-service.
        
        Args:
            candidate_id: Candidate identifier
            status: New status
            metadata: Optional metadata about status change
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(
                    f"{self.base_url}/api/v1/candidates/{candidate_id}/status",
                    json={"status": status, "metadata": metadata or {}},
                    headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                )
                
                response.raise_for_status()
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to update candidate status: {str(e)}")
            return False


# Singleton instance
_candidate_client = None


def get_candidate_client() -> CandidateServiceClient:
    """Get or create candidate service client singleton."""
    global _candidate_client
    if _candidate_client is None:
        _candidate_client = CandidateServiceClient()
    return _candidate_client
