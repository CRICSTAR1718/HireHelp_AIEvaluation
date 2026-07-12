import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from answer_evaluation.service import AnswerEvaluationService
from answer_evaluation.schema import EvaluateAnswerRequest, AnswerEvaluationResponse


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def evaluation_service():
    """Answer evaluation service fixture."""
    return AnswerEvaluationService()


@pytest.fixture
def sample_request():
    """Sample answer evaluation request."""
    return EvaluateAnswerRequest(
        interview_id="interview_123",
        question_index=0,
        question="Describe your experience with REST APIs",
        answer="I have built several REST APIs using Python and Flask. I implemented CRUD operations, authentication, and rate limiting.",
        question_category="technical",
        evaluation_rubric={
            "excellent": "Deep knowledge with examples",
            "good": "Good understanding",
            "fair": "Basic knowledge",
            "poor": "No knowledge"
        }
    )


class TestAnswerEvaluationService:
    """Tests for AnswerEvaluationService."""
    
    @patch('answer_evaluation.service.LLMClient')
    def test_evaluate_answer_success(self, mock_llm_client, evaluation_service, sample_request, mock_db):
        """Test successful answer evaluation."""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "score": 0.75,
                "reasoning": "Candidate shows good understanding of REST APIs with practical experience",
                "strengths": ["Practical experience", "Mentions key features"],
                "weaknesses": ["Could elaborate on design patterns"],
                "follow_up_suggestions": ["How do you handle authentication?", "What about error handling?"]
            }
            """,
            "latency_ms": 1200,
            "token_usage": {"total_tokens": 400}
        }
        
        result = evaluation_service.evaluate_answer(
            request=sample_request,
            db=mock_db
        )
        
        assert isinstance(result, AnswerEvaluationResponse)
        assert result.interview_id == "interview_123"
        assert result.question_index == 0
        assert result.score == 0.75
        assert len(result.strengths) == 2
        assert len(result.weaknesses) == 1
    
    def test_get_answer_evaluation_not_found(self, evaluation_service, mock_db):
        """Test retrieving non-existent answer evaluation."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = evaluation_service.get_answer_evaluation("nonexistent_id", mock_db)
        assert result is None
