import httpx
import logging
from typing import Dict, Any, Optional
from ..config.settings import settings

logger = logging.getLogger(__name__)


class RecruitmentServiceClient:
    """HTTP client for internal communication with recruitment-service."""
    
    def __init__(self):
        self.base_url = settings.RECRUITMENT_SERVICE_URL
        self.timeout = 30.0
    
    async def get_job_details(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job details from recruitment-service.
        
        Args:
            job_id: Job identifier
        
        Returns:
            Job details dict or None if not found
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jobs/{job_id}",
                    headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                )
                
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to get job details: {str(e)}")
            return None
    
    async def update_fitment_score(self, job_id: str, candidate_id: str, fitment_data: Dict[str, Any]) -> bool:
        """
        Update fitment score in recruitment-service.
        
        Args:
            job_id: Job identifier
            candidate_id: Candidate identifier
            fitment_data: Fitment score data
        
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/jobs/{job_id}/candidates/{candidate_id}/fitment",
                    json=fitment_data,
                    headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                )
                
                response.raise_for_status()
                return True
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to update fitment score: {str(e)}")
            return False
    
    async def get_candidate_applications(self, job_id: str) -> Optional[list[Dict[str, Any]]]:
        """
        Get all candidate applications for a job.
        
        Args:
            job_id: Job identifier
        
        Returns:
            List of applications or None if error
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/jobs/{job_id}/applications",
                    headers={"Authorization": f"Bearer {settings.SERVICE_TOKEN}"}
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPError as e:
            logger.error(f"Failed to get candidate applications: {str(e)}")
            return None


# Singleton instance
_recruitment_client = None


def get_recruitment_client() -> RecruitmentServiceClient:
    """Get or create recruitment service client singleton."""
    global _recruitment_client
    if _recruitment_client is None:
        _recruitment_client = RecruitmentServiceClient()
    return _recruitment_client
