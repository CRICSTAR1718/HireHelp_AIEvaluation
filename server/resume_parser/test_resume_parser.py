import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from sqlalchemy.orm import Session
from fastapi import HTTPException
from server.resume_parser.service import ResumeParserService
from server.resume_parser.schema import ParsedResumeResponse, ParseResumeRequest
from server.resume_parser.router import router
from fastapi.testclient import TestClient


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def parser_service():
    """Resume parser service fixture."""
    return ResumeParserService()


@pytest.fixture
def client():
    """Test client for router."""
    from server.main import app
    return TestClient(app)


class TestResumeParserService:
    """Tests for ResumeParserService."""

    @patch('server.resume_parser.service.pdfplumber')
    @patch('server.resume_parser.service.httpx')
    @patch('server.resume_parser.service.LLMClient')
    @pytest.mark.asyncio
    async def test_parse_resume_success(self, mock_llm_client, mock_httpx, mock_pdfplumber, parser_service, mock_db):
        """Test successful resume parsing."""
        # Mock HTTP download response
        mock_response = Mock()
        mock_response.content = b"fake pdf content"
        mock_response.raise_for_status = Mock()
        mock_httpx.get.return_value = mock_response
        
        # Mock pdfplumber.open
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample resume text for John Doe with Python experience"
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "personal_info": {
                    "full_name": {"value": "John Doe", "confidence": 0.95},
                    "email": {"value": "john@example.com", "confidence": 0.98},
                    "phone": {"value": "+1234567890", "confidence": 0.90},
                    "location": {"value": "San Francisco, CA", "confidence": 0.85}
                },
                "experience": {
                    "total_years": {"value": 5.5, "confidence": 0.90},
                    "work_history": []
                },
                "education": [],
                "skills": {
                    "skills": [],
                    "overall_confidence": 0.88
                },
                "needs_human_review": false,
                "parsing_notes": "Successfully parsed"
            }
            """,
            "latency_ms": 1500,
            "token_usage": {"total_tokens": 500}
        }


        parser_service.llm_client = mock_llm_instance
        result = await parser_service.parse_resume(
            resume_id="resume_123",
            candidate_id="candidate_456",
            file_url="http://example.com/resume.pdf",
            db=mock_db
        )

        assert isinstance(result, ParsedResumeResponse)
        assert result.id == "resume_123"
        assert result.candidate_id == "candidate_456"
        assert result.personal_info.full_name.value == "John Doe"
        assert result.personal_info.full_name.confidence == 0.95

    @patch('server.resume_parser.service.pdfplumber')
    @patch('server.resume_parser.service.httpx')
    @patch('server.resume_parser.service.LLMClient')
    @pytest.mark.asyncio
    async def test_parse_resume_low_confidence(self, mock_llm_client, mock_httpx, mock_pdfplumber, parser_service, mock_db):
        """Test resume parsing with low confidence fields."""
        # Mock HTTP download response
        mock_response = Mock()
        mock_response.content = b"fake pdf content"
        mock_response.raise_for_status = Mock()
        mock_httpx.get.return_value = mock_response
        
        # Mock pdfplumber.open
        mock_pdf = Mock()
        mock_page = Mock()
        mock_page.extract_text.return_value = "Sample resume text for John Doe with Python experience"
        mock_pdf.pages = [mock_page]
        mock_pdfplumber.open.return_value.__enter__.return_value = mock_pdf
        
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "personal_info": {
                    "full_name": {"value": "John Doe", "confidence": 0.95},
                    "email": {"value": "john@example.com", "confidence": 0.65},
                    "phone": {"value": null, "confidence": 0.0},
                    "location": {"value": "Unknown", "confidence": 0.50}
                },
                "experience": {
                    "total_years": {"value": 5.5, "confidence": 0.90},
                    "work_history": []
                },
                "education": [],
                "skills": {
                    "skills": [],
                    "overall_confidence": 0.88
                },
                "needs_human_review": false,
                "parsing_notes": "Low confidence on some fields"
            }
            """,
            "latency_ms": 1500,
            "token_usage": {"total_tokens": 500}
        }


        parser_service.llm_client = mock_llm_instance
        result = await parser_service.parse_resume(
            resume_id="resume_123",
            candidate_id="candidate_456",
            file_url="http://example.com/resume.pdf",
            db=mock_db
        )

        # Should flag for human review due to low confidence
        assert result.needs_human_review == True

    def test_get_parsed_resume_not_found(self, parser_service, mock_db):
        """Test retrieving non-existent parsed resume."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = parser_service.get_parsed_resume("nonexistent_id", mock_db)
        assert result is None


class TestResumeParserRouter:
    """Tests for resume parser router."""

    @patch('server.resume_parser.router.parser_service')
    @patch('server.resume_parser.router.verify_service_token')
    def test_parse_resume_endpoint(self, mock_auth, mock_service, client):
        """Test POST /parse endpoint."""
        mock_auth.return_value = {"service": "recruitment-service"}
        mock_service.parse_resume = AsyncMock(
            return_value=ParsedResumeResponse.model_construct(
                id="resume_123", candidate_id="candidate_456"
            )
        )

        response = client.post(
            "/api/v1/resume-parser/parse",
            json={
                "resume_id": "resume_123",
                "candidate_id": "candidate_456",
                "file_url": "http://example.com/resume.pdf"
            },
            headers={"x-internal-service": "recruitment-service"}
        )

        assert response.status_code == 201

    @patch('server.resume_parser.router.parser_service')
    @patch('server.resume_parser.router.verify_service_token')
    def test_get_parsed_resume_endpoint(self, mock_auth, mock_service, client):
        """Test GET /{resume_id} endpoint."""
        mock_auth.return_value = {"service": "recruitment-service"}
        mock_service.get_parsed_resume.return_value = None


        response = client.get(
            "/api/v1/resume-parser/resume_123",
            headers={"x-internal-service": "recruitment-service"}
        )

        assert response.status_code == 404
