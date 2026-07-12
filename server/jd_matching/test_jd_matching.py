import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from jd_matching.service import JobMatchingService
from jd_matching.schema import MatchJobRequest, JobMatchResponse


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def matching_service():
    """Job matching service fixture."""
    return JobMatchingService()


@pytest.fixture
def sample_request():
    """Sample job matching request."""
    return MatchJobRequest(
        job_id="job_123",
        job_description="Senior Python developer with experience in web development",
        required_skills=["Python", "JavaScript", "React"],
        required_experience_years=5.0,
        max_results=10
    )


@pytest.fixture
def mock_parsed_resumes():
    """Mock parsed resumes."""
    return [
        Mock(
            id="resume_1",
            candidate_id="candidate_1",
            skills=[{"skill_name": "Python"}, {"skill_name": "JavaScript"}],
            total_experience_years=6.0
        ),
        Mock(
            id="resume_2",
            candidate_id="candidate_2",
            skills=[{"skill_name": "Python"}, {"skill_name": "Java"}],
            total_experience_years=4.0
        )
    ]


class TestJobMatchingService:
    """Tests for JobMatchingService."""
    
    @patch('jd_matching.service.EmbeddingService')
    @patch('jd_matching.service.VectorClient')
    def test_match_job_success(self, mock_vector_client, mock_embedding_service, matching_service, sample_request, mock_db, mock_parsed_resumes):
        """Test successful job matching."""
        # Mock embedding service
        mock_es_instance = Mock()
        mock_embedding_service.return_value = mock_es_instance
        mock_es_instance.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Mock vector client
        mock_vc_instance = Mock()
        mock_vector_client.return_value = mock_vc_instance
        mock_vc_instance.search_similar.return_value = [
            {"id": "resume_1", "score": 0.85, "metadata": {}},
            {"id": "resume_2", "score": 0.72, "metadata": {}}
        ]
        
        # Mock database query
        mock_db.query.return_value.filter.return_value.all.return_value = mock_parsed_resumes
        
        result = matching_service.match_job(
            request=sample_request,
            db=mock_db
        )
        
        assert isinstance(result, JobMatchResponse)
        assert result.job_id == "job_123"
        assert len(result.matches) == 2
        assert result.matches[0].overall_match_score >= result.matches[1].overall_match_score
    
    def test_calculate_skills_match(self, matching_service):
        """Test skills match calculation."""
        score = matching_service._calculate_skills_match(
            candidate_skills=["Python", "JavaScript", "React"],
            required_skills=["Python", "JavaScript", "Java"]
        )
        
        assert score == 2/3  # 2 out of 3 required skills
    
    def test_calculate_experience_match(self, matching_service):
        """Test experience match calculation."""
        score = matching_service._calculate_experience_match(
            candidate_years=6.0,
            required_years=5.0
        )
        
        assert score == 1.0  # Exceeds requirement, capped at 1.0
