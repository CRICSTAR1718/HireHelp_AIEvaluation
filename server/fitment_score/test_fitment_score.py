import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session
from server.fitment_score.service import FitmentScoreService
from server.fitment_score.schema import CalculateFitmentRequest, FitmentScoreResponse
from server.fitment_score.scoring_engine import ScoringEngine, DimensionScore


@pytest.fixture
def mock_db():
    """Mock database session."""
    return Mock(spec=Session)


@pytest.fixture
def fitment_service():
    """Fitment score service fixture."""
    return FitmentScoreService()


@pytest.fixture
def scoring_engine():
    """Scoring engine fixture."""
    return ScoringEngine()


@pytest.fixture
def sample_request():
    """Sample fitment calculation request."""
    return CalculateFitmentRequest(
        candidate_id="candidate_123",
        job_id="job_456",
        resume_id="resume_789",
        job_description="Senior Software Engineer position",
        candidate_skills=["Python", "JavaScript", "React", "SQL"],
        required_skills=["Python", "JavaScript"],
        bonus_skills=["React", "AWS"],
        candidate_experience_years=5.0,
        required_experience_years=3.0,
        candidate_education=[
            {"degree": "BS", "field_of_study": "Computer Science", "institution": "University"}
        ],
        required_education="Bachelor's"
    )


class TestScoringEngine:
    """Tests for ScoringEngine."""

    def test_calculate_overall_score(self, scoring_engine):
        """Test overall score calculation."""
        score = scoring_engine.calculate_overall_score(
            skills_score=0.8,
            experience_score=0.9,
            education_score=0.7,
            culture_fit_score=0.6
        )

        # Weighted: 0.8*0.4 + 0.9*0.3 + 0.7*0.15 + 0.6*0.15 = 0.32 + 0.27 + 0.105 + 0.09 = 0.785
        assert 0.78 <= score <= 0.79

    def test_calculate_skills_score(self, scoring_engine):
        """Test skills score calculation."""
        result = scoring_engine.calculate_skills_score(
            candidate_skills=["Python", "JavaScript", "React"],
            required_skills=["Python", "JavaScript", "Java"],
            bonus_skills=["React", "AWS"]
        )

        assert isinstance(result, DimensionScore)
        assert 0.0 <= result.score <= 1.0
        assert result.reasoning
        assert result.weight == 0.4

    def test_calculate_experience_score(self, scoring_engine):
        """Test experience score calculation."""
        result = scoring_engine.calculate_experience_score(
            candidate_years=5.0,
            required_years=3.0
        )

        assert isinstance(result, DimensionScore)
        assert result.score >= 0.9  # Should meet requirement
        assert "5 years" in result.reasoning

    def test_calculate_education_score(self, scoring_engine):
        """Test education score calculation."""
        result = scoring_engine.calculate_education_score(
            candidate_education=[{"degree": "BS", "field_of_study": "Computer Science"}],
            required_education="Bachelor's"
        )

        assert isinstance(result, DimensionScore)
        assert result.score > 0.5  # Should match

    def test_calculate_culture_fit_score(self, scoring_engine):
        """Test culture fit score calculation."""
        result = scoring_engine.calculate_culture_fit_score(
            career_trajectory=[
                {"job_title": "Junior Developer"},
                {"job_title": "Senior Developer"}
            ]
        )

        assert isinstance(result, DimensionScore)
        assert 0.0 <= result.score <= 1.0

    def test_update_weights_valid(self, scoring_engine):
        """Test updating weights with valid values."""
        new_weights = {
            "skills": 0.35,
            "experience": 0.35,
            "education": 0.15,
            "culture_fit": 0.15
        }

        scoring_engine.update_weights(new_weights)
        assert scoring_engine.weights == new_weights

    def test_update_weights_invalid(self, scoring_engine):
        """Test updating weights with invalid values."""
        invalid_weights = {
            "skills": 0.5,
            "experience": 0.5,
            "education": 0.0,
            "culture_fit": 0.0
        }

        with pytest.raises(ValueError):
            scoring_engine.update_weights(invalid_weights)


class TestFitmentScoreService:
    """Tests for FitmentScoreService."""

    def test_calculate_dimension_scores(self, fitment_service, sample_request):
        """Test dimension score calculation."""
        dimensions = fitment_service._calculate_dimension_scores(sample_request)

        assert "skills" in dimensions
        assert "experience" in dimensions
        assert "education" in dimensions
        assert "culture_fit" in dimensions

        for dimension in dimensions.values():
            assert isinstance(dimension, DimensionScore)
            assert 0.0 <= dimension.score <= 1.0

    @patch('server.fitment_score.service.LLMClient')
    @pytest.mark.asyncio
    async def test_calculate_fitment_success(self, mock_llm_client, fitment_service, sample_request, mock_db):
        """Test successful fitment calculation."""
        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_client.return_value = mock_llm_instance
        mock_llm_instance.chat_completion.return_value = {
            "content": """
            {
                "overall_reasoning": "Strong candidate with good skills match",
                "strengths": ["Strong technical background", "Relevant experience"],
                "weaknesses": ["Limited leadership experience"],
                "recommendations": "Consider for technical interview"
            }
            """,
            "latency_ms": 2000,
            "token_usage": {"total_tokens": 600}
        }


        fitment_service.llm_client = mock_llm_instance
        result = await fitment_service.calculate_fitment(
            request=sample_request,
            db=mock_db
        )

        assert isinstance(result, FitmentScoreResponse)
        assert result.candidate_id == "candidate_123"
        assert result.job_id == "job_456"
        assert 0.0 <= result.overall_score <= 1.0
        assert result.overall_reasoning  # Must have reasoning per PRD

    def test_get_fitment_score_not_found(self, fitment_service, mock_db):
        """Test retrieving non-existent fitment score."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = fitment_service.get_fitment_score("nonexistent_id", mock_db)
        assert result is None
