import pytest
from unittest.mock import Mock, patch, AsyncMock
from events.handlers.resume_uploaded_handler import handle_resume_uploaded
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def sample_resume_uploaded_event():
    """Sample ResumeUploaded Kafka event."""
    return {
        "event_type": "ResumeUploaded",
        "payload": {
            "resume_id": "resume_123",
            "candidate_id": "candidate_456",
            "file_url": "http://example.com/resume.pdf",
            "file_type": "pdf"
        },
        "timestamp": "2024-01-01T00:00:00Z"
    }


class TestResumeUploadedHandler:
    """Tests for resume uploaded Kafka handler."""
    
    @patch('events.handlers.resume_uploaded_handler.ResumeParserService')
    @patch('events.handlers.resume_uploaded_handler.get_db')
    async def test_handle_resume_uploaded_success(
        self,
        mock_get_db,
        mock_parser_service,
        sample_resume_uploaded_event,
        mock_db
    ):
        """Test successful handling of ResumeUploaded event."""
        # Mock database
        mock_get_db.return_value = mock_db
        
        # Mock parser service
        mock_parser_instance = Mock()
        mock_parser_service.return_value = mock_parser_instance
        mock_parser_instance.parse_resume = AsyncMock(return_value=Mock(id="parsed_123"))
        
        # Handle event
        await handle_resume_uploaded(sample_resume_uploaded_event)
        
        # Verify parser was called
        mock_parser_instance.parse_resume.assert_called_once()
        call_args = mock_parser_instance.parse_resume.call_args
        assert call_args[1]["resume_id"] == "resume_123"
        assert call_args[1]["candidate_id"] == "candidate_456"
        assert call_args[1]["file_url"] == "http://example.com/resume.pdf"
    
    @patch('events.handlers.resume_uploaded_handler.ResumeParserService')
    @patch('events.handlers.resume_uploaded_handler.get_db')
    async def test_handle_resume_uploaded_missing_fields(
        self,
        mock_get_db,
        mock_parser_service,
        mock_db
    ):
        """Test handling event with missing required fields."""
        mock_get_db.return_value = mock_db
        mock_parser_instance = Mock()
        mock_parser_service.return_value = mock_parser_instance
        
        # Event with missing fields
        incomplete_event = {
            "event_type": "ResumeUploaded",
            "payload": {
                "resume_id": "resume_123"
                # Missing candidate_id and file_url
            }
        }
        
        # Should raise error or handle gracefully
        with pytest.raises((KeyError, ValueError)):
            await handle_resume_uploaded(incomplete_event)
