import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for all tests."""
    with patch('llm.client.LLMClient') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.chat_completion.return_value = {
            "content": '{"result": "mocked"}',
            "latency_ms": 100,
            "token_usage": {"total_tokens": 50}
        }
        yield mock_instance


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer for all tests."""
    with patch('events.kafka_producer.get_kafka_producer') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        mock_instance.publish_event.return_value = True
        yield mock_instance


@pytest.fixture
def sample_parsed_resume():
    """Sample parsed resume data."""
    return {
        "id": "resume_123",
        "candidate_id": "candidate_456",
        "full_name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "location": "San Francisco, CA",
        "total_experience_years": 5.0,
        "work_history": [
            {
                "job_title": "Software Engineer",
                "company_name": "Tech Corp",
                "description": "Developed software"
            }
        ],
        "skills": [
            {"skill_name": "Python", "category": "technical"},
            {"skill_name": "JavaScript", "category": "technical"}
        ],
        "education": [
            {
                "degree": "BS",
                "field_of_study": "Computer Science",
                "institution": "University"
            }
        ]
    }
