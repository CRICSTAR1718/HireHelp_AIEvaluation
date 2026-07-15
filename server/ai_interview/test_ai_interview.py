import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from server.ai_interview.service import AIInterviewService
from server.ai_interview.schema import StartInterviewRequest, SubmitAnswerRequest, InterviewResponse
from server.ai_interview.question_generator import QuestionGenerator
from server.ai_interview.conversation_manager import ConversationManager


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def interview_service():
    """AI interview service fixture."""
    return AIInterviewService()


@pytest.fixture
def question_generator():
    """Question generator fixture."""
    return QuestionGenerator()


@pytest.fixture
def conversation_manager():
    """Conversation manager fixture."""
    return ConversationManager()


@pytest.fixture
def sample_start_request():
    """Sample interview start request."""
    return StartInterviewRequest(
        candidate_id="candidate_123",
        job_id="job_456",
        resume_id="resume_789",
        job_description="Senior Software Engineer",
        role_title="Senior Software Engineer",
        experience_level="senior",
        focus_areas=["technical", "leadership"],
        num_questions=5
    )


@pytest.fixture
def mock_parsed_resume():
    """Mock parsed resume."""
    resume = Mock()
    resume.id = "resume_789"
    resume.full_name = "John Doe"
    resume.total_experience_years = 8.0
    resume.skills = [
        {"skill_name": "Python", "category": "technical"},
        {"skill_name": "Leadership", "category": "soft"}
    ]
    return resume


class TestQuestionGenerator:
    """Tests for QuestionGenerator."""
    
    @patch('server.ai_interview.question_generator.LLMClient')
    def test_generate_questions(self, mock_llm_client, question_generator):
        """Test question generation."""
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "questions": [
                    {
                        "question": "Describe your experience with Python",
                        "category": "technical",
                        "competency_level": "senior",
                        "assesses": "Python knowledge",
                        "evaluation_rubric": {
                            "excellent": "Deep knowledge",
                            "good": "Good knowledge",
                            "fair": "Basic knowledge",
                            "poor": "No knowledge"
                        }
                    }
                ]
            }
            """,
            "latency_ms": 1500,
            "token_usage": {"total_tokens": 500}
        }
        
        question_generator.llm_client = mock_llm_instance
        questions = question_generator.generate_questions(
            resume_text="Python developer with 5 years experience",
            job_description="Senior Python developer",
            role_title="Senior Developer",
            experience_level="senior"
        )
        
        assert len(questions) > 0
        assert "question" in questions[0]
        assert "category" in questions[0]


class TestConversationManager:
    """Tests for ConversationManager."""
    
    def test_create_interview(self, conversation_manager):
        """Test interview creation."""
        questions = [
            {"question": "Q1", "category": "technical"},
            {"question": "Q2", "category": "behavioral"}
        ]
        
        interview = conversation_manager.create_interview(
            interview_id="interview_123",
            candidate_id="candidate_456",
            job_id="job_789",
            questions=questions
        )
        
        assert interview["id"] == "interview_123"
        assert interview["candidate_id"] == "candidate_456"
        assert interview["total_questions"] == 2
        assert interview["status"] == "pending"
    
    def test_start_interview(self, conversation_manager):
        """Test starting an interview."""
        conversation_manager.create_interview(
            interview_id="interview_123",
            candidate_id="candidate_456",
            job_id="job_789",
            questions=[{"question": "Q1"}]
        )
        
        interview = conversation_manager.start_interview("interview_123")
        
        assert interview["status"] == "in_progress"
        assert interview["started_at"] is not None
    
    def test_submit_answer(self, conversation_manager):
        """Test submitting an answer."""
        conversation_manager.create_interview(
            interview_id="interview_123",
            candidate_id="candidate_456",
            job_id="job_789",
            questions=[{"question": "Q1"}, {"question": "Q2"}]
        )
        conversation_manager.start_interview("interview_123")
        
        interview = conversation_manager.submit_answer(
            interview_id="interview_123",
            answer="My answer"
        )
        
        assert len(interview["answers"]) == 1
        assert interview["current_question_index"] == 1
    
    def test_get_current_question(self, conversation_manager):
        """Test getting current question."""
        questions = [
            {"question": "Q1"},
            {"question": "Q2"}
        ]
        conversation_manager.create_interview(
            interview_id="interview_123",
            candidate_id="candidate_456",
            job_id="job_789",
            questions=questions
        )
        conversation_manager.start_interview("interview_123")
        
        current = conversation_manager.get_current_question("interview_123")
        
        assert current == questions[0]


class TestAIInterviewService:
    """Tests for AIInterviewService."""
    
    @patch('server.ai_interview.service.QuestionGenerator')
    @pytest.mark.asyncio
    async def test_start_interview_success(self, mock_question_gen, interview_service, sample_start_request, mock_db, mock_parsed_resume):
        """Test successful interview start."""
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_parsed_resume
        
        # Mock question generator
        mock_qg_instance = Mock()
        mock_question_gen.return_value = mock_qg_instance
        mock_qg_instance.generate_questions.return_value = [
            {
                "question": "Describe your experience",
                "category": "technical",
                "competency_level": "senior",
                "assesses": "Experience",
                "evaluation_rubric": {"excellent": "Great", "good": "Good"}
            }
        ]
        
        interview_service.question_generator = mock_qg_instance
        result = await interview_service.start_interview(
            request=sample_start_request,
            db=mock_db
        )
        
        assert isinstance(result, InterviewResponse)
        assert result.candidate_id == "candidate_123"
        assert result.job_id == "job_456"
        assert result.status == "in_progress"
        assert len(result.questions) > 0
    
    def test_get_interview_not_found(self, interview_service, mock_db):
        """Test retrieving non-existent interview."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = interview_service.get_interview("nonexistent_id", mock_db)
        assert result is None
