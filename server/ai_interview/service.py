import time
import logging
import uuid
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from ..llm.client import LLMClient
from ..config.settings import settings
from ..common.exceptions import LLMProviderError
from ..database.models import AIInterview, ParsedResume
from .schema import StartInterviewRequest, SubmitAnswerRequest, InterviewResponse, Question
from .question_generator import QuestionGenerator
from .conversation_manager import ConversationManager, InterviewStatus

logger = logging.getLogger(__name__)


class AIInterviewService:
    """Service for AI-powered interviews."""
    
    def __init__(self):
        self.llm_client = LLMClient()
        self.question_generator = QuestionGenerator()
        self.conversation_manager = ConversationManager()
    
    def _get_resume_text(self, resume_id: str, db: Session) -> str:
        """Get resume text from database."""
        resume = db.query(ParsedResume).filter(
            ParsedResume.id == resume_id
        ).first()
        
        if not resume:
            raise ValueError(f"Resume not found: {resume_id}")
        
        # Construct text summary
        text_parts = []
        if resume.full_name:
            text_parts.append(f"Name: {resume.full_name}")
        if resume.total_experience_years:
            text_parts.append(f"Experience: {resume.total_experience_years} years")
        if resume.skills:
            text_parts.append(f"Skills: {', '.join([s.get('skill_name', '') for s in resume.skills])}")
        
        return "\n".join(text_parts)
    
    async def start_interview(
        self,
        request: StartInterviewRequest,
        db: Optional[Session] = None
    ) -> InterviewResponse:
        """
        Start an AI interview for a candidate.
        
        Args:
            request: Interview start request
            db: Database session
        
        Returns:
            InterviewResponse with questions
        """
        start_time = time.time()
        interview_id = f"interview_{uuid.uuid4().hex}"
        
        try:
            # Get resume text
            if not db:
                raise ValueError("Database session required")
            resume_text = self._get_resume_text(request.resume_id, db)
            
            # Generate questions
            questions_data = self.question_generator.generate_questions(
                resume_text=resume_text,
                job_description=request.job_description,
                role_title=request.role_title,
                experience_level=request.experience_level,
                focus_areas=request.focus_areas,
                num_questions=request.num_questions
            )
            
            # Convert to schema
            questions = [Question(**q) for q in questions_data]
            
            # Create interview session
            interview = self.conversation_manager.create_interview(
                interview_id=interview_id,
                candidate_id=request.candidate_id,
                job_id=request.job_id,
                questions=[q.dict() for q in questions]
            )
            
            # Start the interview
            self.conversation_manager.start_interview(interview_id)
            
            # Get current question
            current_question_data = self.conversation_manager.get_current_question(interview_id)
            current_question = Question(**current_question_data) if current_question_data else None
            
            # Save to database
            if db:
                self._save_to_database(db, interview, questions)
            
            # Build response
            interview_state = self.conversation_manager.get_interview_state(interview_id)
            
            response = InterviewResponse(
                id=interview_id,
                candidate_id=request.candidate_id,
                job_id=request.job_id,
                status=interview_state["status"],
                current_question_index=interview_state["current_question_index"],
                total_questions=interview_state["total_questions"],
                questions=questions,
                answers=[],
                current_question=current_question,
                started_at=interview_state["started_at"],
                completed_at=interview_state["completed_at"],
                interview_model=settings.LLM_MODEL,
                created_at=interview_state.get("started_at", time.time())
            )
            
            logger.info(f"Started AI interview {interview_id} for candidate {request.candidate_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to start interview: {str(e)}")
            raise LLMProviderError(f"Failed to start interview: {str(e)}")
    
    async def submit_answer(
        self,
        request: SubmitAnswerRequest,
        db: Optional[Session] = None
    ) -> InterviewResponse:
        """
        Submit an answer for the current question.
        
        Args:
            request: Answer submission request
            db: Database session
        
        Returns:
            InterviewResponse with next question or completion status
        """
        try:
            # Submit answer to conversation manager
            interview = self.conversation_manager.submit_answer(
                interview_id=request.interview_id,
                answer=request.answer,
                answer_metadata=request.answer_metadata
            )
            
            # Get next question
            next_question_data = self.conversation_manager.get_current_question(request.interview_id)
            next_question = Question(**next_question_data) if next_question_data else None
            
            # Update database if interview is complete
            if db and interview["status"] == InterviewStatus.COMPLETED:
                self._update_database_completion(db, request.interview_id, interview)
            
            # Get interview state
            interview_state = self.conversation_manager.get_interview_state(request.interview_id)
            questions = [Question(**q) for q in interview_state["questions"]]
            
            response = InterviewResponse(
                id=request.interview_id,
                candidate_id=interview_state["candidate_id"],
                job_id=interview_state["job_id"],
                status=interview_state["status"],
                current_question_index=interview_state["current_question_index"],
                total_questions=interview_state["total_questions"],
                questions=questions,
                answers=interview_state["answers"],
                current_question=next_question,
                started_at=interview_state["started_at"],
                completed_at=interview_state["completed_at"],
                interview_model=settings.LLM_MODEL,
                created_at=interview_state.get("started_at", time.time())
            )
            
            logger.info(f"Submitted answer for interview {request.interview_id}")
            return response
            
        except Exception as e:
            logger.error(f"Failed to submit answer: {str(e)}")
            raise LLMProviderError(f"Failed to submit answer: {str(e)}")
    
    def get_interview(self, interview_id: str, db: Session) -> Optional[InterviewResponse]:
        """
        Retrieve an interview from database.
        
        Args:
            interview_id: Interview identifier
            db: Database session
        
        Returns:
            InterviewResponse or None if not found
        """
        try:
            db_interview = db.query(AIInterview).filter(
                AIInterview.id == interview_id
            ).first()
            
            if not db_interview:
                return None
            
            questions = [Question(**q) for q in (db_interview.questions or [])]
            
            return InterviewResponse(
                id=db_interview.id,
                candidate_id=db_interview.candidate_id,
                job_id=db_interview.job_id,
                status=db_interview.status,
                current_question_index=db_interview.current_question_index,
                total_questions=db_interview.total_questions,
                questions=questions,
                answers=db_interview.answers or [],
                current_question=None,
                started_at=db_interview.started_at,
                completed_at=db_interview.completed_at,
                interview_model=db_interview.interview_model,
                created_at=db_interview.created_at
            )
            
        except Exception as e:
            logger.error(f"Failed to retrieve interview {interview_id}: {str(e)}")
            raise
    
    def _save_to_database(self, db: Session, interview: Dict[str, Any], questions: List[Question]):
        """Save interview to database."""
        db_interview = AIInterview(
            id=interview["id"],
            candidate_id=interview["candidate_id"],
            job_id=interview["job_id"],
            status=interview["status"],
            current_question_index=interview["current_question_index"],
            total_questions=interview["total_questions"],
            questions=[q.dict() for q in questions],
            answers=[],
            interview_model=settings.LLM_MODEL,
            started_at=interview["started_at"]
        )
        
        db.add(db_interview)
        db.commit()
        db.refresh(db_interview)
    
    def _update_database_completion(self, db: Session, interview_id: str, interview: Dict[str, Any]):
        """Update database when interview completes."""
        db_interview = db.query(AIInterview).filter(
            AIInterview.id == interview_id
        ).first()
        
        if db_interview:
            db_interview.status = interview["status"]
            db_interview.answers = interview["answers"]
            db_interview.current_question_index = interview["current_question_index"]
            db_interview.completed_at = interview["completed_at"]
            db_interview.total_duration_ms = int((interview["completed_at"] - interview["started_at"]).total_seconds() * 1000)
            
            db.commit()
    
