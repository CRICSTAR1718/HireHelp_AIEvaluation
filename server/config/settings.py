from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ai-evaluation-service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database
    DATABASE_URL: str  # Transaction pooler connection (PgBouncer port 6543) for running app
    DATABASE_URL_MIGRATIONS: Optional[str] = None  # Direct connection (port 5432) for Alembic DDL
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # LLM Provider
    LLM_PROVIDER: str = "openai"  # openai, gemini, claude
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-4"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    LLM_TIMEOUT: int = 60
    
    # Embeddings
    EMBEDDING_PROVIDER: str = "openai"  # openai, qdrant, pgvector
    VECTOR_BACKEND: str = "pgvector"  # pgvector or qdrant
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    QDRANT_URL: Optional[str] = None
    QDRANT_API_KEY: Optional[str] = None
    PGVECTOR_CONNECTION_STRING: Optional[str] = None
    
# JWT/Auth
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    SERVICE_TOKEN: Optional[str] = None
    
    # Internal Service URLs
    RECRUITMENT_SERVICE_URL: str = "http://localhost:8001"
    CANDIDATE_SERVICE_URL: str = "http://localhost:8002"
    
    # Feature Flags
    ENABLE_AI_INTERVIEW: bool = True
    ENABLE_FITMENT_SCORING: bool = True
    ENABLE_RESUME_SCREENING: bool = True
    
    # Thresholds
    CONFIDENCE_THRESHOLD: float = 0.7
    FITMENT_SCORE_THRESHOLD: float = 0.6
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
