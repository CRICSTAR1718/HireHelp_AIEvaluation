import time
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..embeddings.embedding_service import EmbeddingService
from ..embeddings.vector_client import VectorClient
from ..database.models import ParsedResume
from ..common.exceptions import EmbeddingError
from .schema import MatchJobRequest, JobMatchResponse, CandidateMatch

logger = logging.getLogger(__name__)


class JobMatchingService:
    """Service for matching job descriptions to candidates using embeddings."""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_client = VectorClient()
    
    def _generate_job_embedding(self, job_description: str) -> List[float]:
        """Generate embedding for job description."""
        try:
            return self.embedding_service.generate_embedding(job_description)
        except Exception as e:
            logger.error(f"Failed to generate job embedding: {str(e)}")
            raise EmbeddingError(f"Failed to generate job embedding: {str(e)}")
    
    def _search_similar_resumes(
        self,
        job_embedding: List[float],
        limit: int,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for resumes similar to job description."""
        try:
            return self.vector_client.search_similar(
                collection_name="resumes",
                query_vector=job_embedding,
                limit=limit,
                score_threshold=score_threshold
            )
        except Exception as e:
            logger.error(f"Failed to search similar resumes: {str(e)}")
            raise EmbeddingError(f"Failed to search similar resumes: {str(e)}")
    
    def _calculate_skills_match(
        self,
        candidate_skills: List[str],
        required_skills: List[str]
    ) -> float:
        """Calculate skills match score."""
        if not required_skills:
            return 1.0
        
        required_set = set(skill.lower() for skill in required_skills)
        candidate_set = set(skill.lower() for skill in candidate_skills)
        
        matched = len(candidate_set & required_set)
        return matched / len(required_skills) if required_skills else 1.0
    
    def _calculate_experience_match(
        self,
        candidate_years: float,
        required_years: float
    ) -> float:
        """Calculate experience match score."""
        if required_years == 0:
            return 1.0
        
        ratio = candidate_years / required_years if required_years > 0 else 0
        return min(1.0, ratio)
    
    def _get_resume_details(self, resume_ids: List[str], db: Session) -> Dict[str, Dict[str, Any]]:
        """Get resume details from database."""
        resumes = db.query(ParsedResume).filter(
            ParsedResume.id.in_(resume_ids)
        ).all()
        
        return {
            resume.id: {
                "candidate_id": resume.candidate_id,
                "skills": [s.get("skill_name", "") for s in (resume.skills or [])],
                "experience_years": resume.total_experience_years or 0
            }
            for resume in resumes
        }
    
    async def match_job(
        self,
        request: MatchJobRequest,
        db: Optional[Session] = None
    ) -> JobMatchResponse:
        """
        Match job description to candidates using semantic search.
        
        Args:
            request: Job matching request
            db: Database session
        
        Returns:
            JobMatchResponse with ranked candidate matches
        """
        start_time = time.time()
        
        try:
            if not db:
                raise ValueError("Database session required")
            
            # Generate job embedding
            job_embedding = self._generate_job_embedding(request.job_description)
            
            # Search for similar resumes
            similar_resumes = self._search_similar_resumes(
                job_embedding=job_embedding,
                limit=request.max_results
            )
            
            if not similar_resumes:
                return JobMatchResponse(
                    job_id=request.job_id,
                    matches=[],
                    total_candidates_evaluated=0,
                    matching_model="semantic",
                    matching_timestamp=time.time()
                )
            
            # Get resume details
            resume_ids = [r["id"] for r in similar_resumes]
            resume_details = self._get_resume_details(resume_ids, db)
            
            # Calculate detailed matches
            matches = []
            for result in similar_resumes:
                resume_id = result["id"]
                similarity_score = result["score"]
                
                if resume_id not in resume_details:
                    continue
                
                details = resume_details[resume_id]
                
                # Calculate skills match
                skills_match = self._calculate_skills_match(
                    details["skills"],
                    request.required_skills
                )
                
                # Calculate experience match
                experience_match = self._calculate_experience_match(
                    details["experience_years"],
                    request.required_experience_years or 0
                )
                
                # Calculate overall match (weighted)
                overall_match = (similarity_score * 0.5 + skills_match * 0.3 + experience_match * 0.2)
                
                # Generate reasoning
                reasoning_parts = []
                reasoning_parts.append(f"Semantic similarity: {similarity_score:.2f}")
                reasoning_parts.append(f"Skills match: {skills_match:.2f}")
                reasoning_parts.append(f"Experience match: {experience_match:.2f}")
                
                match = CandidateMatch(
                    candidate_id=details["candidate_id"],
                    resume_id=resume_id,
                    similarity_score=similarity_score,
                    skills_match_score=skills_match,
                    experience_match_score=experience_match,
                    overall_match_score=overall_match,
                    match_reasoning=". ".join(reasoning_parts)
                )
                
                matches.append(match)
            
            # Sort by overall match score
            matches.sort(key=lambda x: x.overall_match_score, reverse=True)
            
            response = JobMatchResponse(
                job_id=request.job_id,
                matches=matches,
                total_candidates_evaluated=len(similar_resumes),
                matching_model="semantic",
                matching_timestamp=time.time()
            )
            
            logger.info(f"Matched {len(matches)} candidates for job {request.job_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to match job: {str(e)}")
            raise
