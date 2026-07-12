import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from skill_extraction.service import SkillExtractionService
from skill_extraction.schema import ExtractSkillsRequest, SkillExtractionResponse


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def extraction_service():
    """Skill extraction service fixture."""
    return SkillExtractionService()


@pytest.fixture
def sample_request():
    """Sample skill extraction request."""
    return ExtractSkillsRequest(
        source_type="resume",
        source_id="resume_123",
        text="Python developer with 5 years experience in JavaScript and React. Strong communication skills and team leadership.",
        focus_categories=["technical", "soft"]
    )


class TestSkillExtractionService:
    """Tests for SkillExtractionService."""
    
    @patch('skill_extraction.service.LLMClient')
    def test_extract_skills_success(self, mock_llm_client, extraction_service, sample_request, mock_db):
        """Test successful skill extraction."""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "skills": [
                    {
                        "skill_name": "Python",
                        "category": "technical",
                        "confidence": 0.95,
                        "context": "mentioned in summary"
                    },
                    {
                        "skill_name": "JavaScript",
                        "category": "technical",
                        "confidence": 0.90,
                        "context": "mentioned in summary"
                    },
                    {
                        "skill_name": "Communication",
                        "category": "soft",
                        "confidence": 0.85,
                        "context": "mentioned in summary"
                    }
                ]
            }
            """,
            "latency_ms": 1000,
            "token_usage": {"total_tokens": 300}
        }
        
        result = extraction_service.extract_skills(
            request=sample_request,
            db=mock_db
        )
        
        assert isinstance(result, SkillExtractionResponse)
        assert result.source_type == "resume"
        assert result.source_id == "resume_123"
        assert len(result.skills) == 3
        assert result.skills[0].category == "technical"
    
    def test_get_skill_extraction_not_found(self, extraction_service, mock_db):
        """Test retrieving non-existent skill extraction."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = extraction_service.get_skill_extraction("nonexistent_id", mock_db)
        assert result is None
