import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from resume_screening.service import ResumeScreeningService
from resume_screening.schema import ScreenedResumeResponse, CriteriaMatch


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def screening_service():
    """Resume screening service fixture."""
    return ResumeScreeningService()


@pytest.fixture
def mock_parsed_resume():
    """Mock parsed resume."""
    resume = Mock()
    resume.id = "resume_123"
    resume.full_name = "John Doe"
    resume.email = "john@example.com"
    resume.total_experience_years = 5.0
    resume.work_history = [
        {
            "job_title": "Software Engineer",
            "company_name": "Tech Corp",
            "description": "Developed software"
        }
    ]
    resume.skills = [
        {"skill_name": "Python", "category": "technical"},
        {"skill_name": "JavaScript", "category": "technical"}
    ]
    resume.education = [
        {
            "degree": "BS",
            "field_of_study": "Computer Science",
            "institution": "University"
        }
    ]
    return resume


class TestResumeScreeningService:
    """Tests for ResumeScreeningService."""
    
    @patch('resume_screening.service.LLMClient')
    def test_screen_resume_success(self, mock_llm_client, screening_service, mock_db, mock_parsed_resume):
        """Test successful resume screening."""
        # Mock database query
        mock_db.query.return_value.filter.return_value.first.return_value = mock_parsed_resume
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "meets_requirements": true,
                "screening_reasoning": "Candidate meets most requirements",
                "screening_score": 0.85,
                "criteria_match": [
                    {
                        "criterion": "skills",
                        "meets": true,
                        "confidence": 0.90,
                        "reasoning": "Has all required skills"
                    },
                    {
                        "criterion": "experience",
                        "meets": true,
                        "confidence": 0.95,
                        "reasoning": "5 years vs required 3 years"
                    }
                ]
            }
            """,
            "latency_ms": 1200,
            "token_usage": {"total_tokens": 400}
        }
        
        # Mock Kafka producer
        with patch('resume_screening.service.get_kafka_producer') as mock_producer:
            mock_producer_instance = Mock()
            mock_producer.return_value = mock_producer_instance
            mock_producer_instance.publish_event.return_value = True
            
            result = screening_service.screen_resume(
                resume_id="resume_123",
                job_id="job_456",
                job_description="Software Engineer position",
                required_skills=["Python", "JavaScript"],
                required_experience_years=3.0,
                db=mock_db
            )
            
            assert isinstance(result, ScreenedResumeResponse)
            assert result.resume_id == "resume_123"
            assert result.job_id == "job_456"
            assert result.meets_requirements == True
            assert result.screening_score == 0.85
            assert len(result.criteria_match) == 2
    
    def test_get_screening_not_found(self, screening_service, mock_db):
        """Test retrieving non-existent screening."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = screening_service.get_screening("nonexistent_id", mock_db)
        assert result is None
    
    def test_get_resume_text(self, screening_service, mock_db, mock_parsed_resume):
        """Test resume text construction."""
        mock_db.query.return_value.filter.return_value.first.return_value = mock_parsed_resume
        
        text = screening_service._get_resume_text("resume_123", mock_db)
        
        assert "John Doe" in text
        assert "Python" in text
        assert "Software Engineer" in text
