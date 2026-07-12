import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class InterviewStatus(str, Enum):
    """Interview status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationManager:
    """Manages multi-turn interview conversation state."""
    
    def __init__(self):
        self.interviews: Dict[str, Dict[str, Any]] = {}
    
    def create_interview(
        self,
        interview_id: str,
        candidate_id: str,
        job_id: str,
        questions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Create a new interview session.
        
        Args:
            interview_id: Unique interview identifier
            candidate_id: Candidate identifier
            job_id: Job identifier
            questions: List of question objects
        
        Returns:
            Interview session object
        """
        interview = {
            "id": interview_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "status": InterviewStatus.PENDING,
            "current_question_index": 0,
            "total_questions": len(questions),
            "questions": questions,
            "answers": [],
            "started_at": None,
            "completed_at": None,
            "metadata": {}
        }
        
        self.interviews[interview_id] = interview
        logger.info(f"Created interview {interview_id} with {len(questions)} questions")
        
        return interview
    
    def start_interview(self, interview_id: str) -> Dict[str, Any]:
        """
        Start an interview session.
        
        Args:
            interview_id: Interview identifier
        
        Returns:
            Updated interview session
        """
        if interview_id not in self.interviews:
            raise ValueError(f"Interview not found: {interview_id}")
        
        interview = self.interviews[interview_id]
        interview["status"] = InterviewStatus.IN_PROGRESS
        interview["started_at"] = datetime.utcnow()
        
        logger.info(f"Started interview {interview_id}")
        return interview
    
    def get_current_question(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current question for an interview.
        
        Args:
            interview_id: Interview identifier
        
        Returns:
            Current question object or None if interview is complete
        """
        if interview_id not in self.interviews:
            raise ValueError(f"Interview not found: {interview_id}")
        
        interview = self.interviews[interview_id]
        
        if interview["current_question_index"] >= interview["total_questions"]:
            return None
        
        return interview["questions"][interview["current_question_index"]]
    
    def submit_answer(
        self,
        interview_id: str,
        answer: str,
        answer_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Submit an answer for the current question.
        
        Args:
            interview_id: Interview identifier
            answer: Candidate's answer
            answer_metadata: Optional metadata about the answer
        
        Returns:
            Updated interview session
        """
        if interview_id not in self.interviews:
            raise ValueError(f"Interview not found: {interview_id}")
        
        interview = self.interviews[interview_id]
        
        if interview["status"] != InterviewStatus.IN_PROGRESS:
            raise ValueError(f"Interview is not in progress: {interview_id}")
        
        # Record answer
        answer_record = {
            "question_index": interview["current_question_index"],
            "question": interview["questions"][interview["current_question_index"]],
            "answer": answer,
            "timestamp": datetime.utcnow(),
            "metadata": answer_metadata or {}
        }
        
        interview["answers"].append(answer_record)
        
        # Move to next question
        interview["current_question_index"] += 1
        
        # Check if interview is complete
        if interview["current_question_index"] >= interview["total_questions"]:
            interview["status"] = InterviewStatus.COMPLETED
            interview["completed_at"] = datetime.utcnow()
            logger.info(f"Completed interview {interview_id}")
        
        return interview
    
    def get_interview_state(self, interview_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current state of an interview.
        
        Args:
            interview_id: Interview identifier
        
        Returns:
            Interview session object or None if not found
        """
        return self.interviews.get(interview_id)
    
    def update_interview_status(
        self,
        interview_id: str,
        status: InterviewStatus
    ) -> Dict[str, Any]:
        """
        Update interview status.
        
        Args:
            interview_id: Interview identifier
            status: New status
        
        Returns:
            Updated interview session
        """
        if interview_id not in self.interviews:
            raise ValueError(f"Interview not found: {interview_id}")
        
        interview = self.interviews[interview_id]
        interview["status"] = status
        
        if status == InterviewStatus.COMPLETED:
            interview["completed_at"] = datetime.utcnow()
        
        logger.info(f"Updated interview {interview_id} status to {status}")
        return interview
    
    def delete_interview(self, interview_id: str):
        """
        Delete an interview session.
        
        Args:
            interview_id: Interview identifier
        """
        if interview_id in self.interviews:
            del self.interviews[interview_id]
            logger.info(f"Deleted interview {interview_id}")
    
    def get_progress(self, interview_id: str) -> Dict[str, Any]:
        """
        Get interview progress information.
        
        Args:
            interview_id: Interview identifier
        
        Returns:
            Progress information
        """
        if interview_id not in self.interviews:
            raise ValueError(f"Interview not found: {interview_id}")
        
        interview = self.interviews[interview_id]
        
        return {
            "interview_id": interview_id,
            "status": interview["status"],
            "current_question": interview["current_question_index"] + 1,
            "total_questions": interview["total_questions"],
            "progress_percent": (interview["current_question_index"] / interview["total_questions"]) * 100,
            "answers_count": len(interview["answers"]),
            "started_at": interview["started_at"],
            "completed_at": interview["completed_at"]
        }
