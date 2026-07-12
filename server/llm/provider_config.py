from dataclasses import dataclass
from typing import Optional
from server.config.settings import settings


@dataclass
class ProviderConfig:
    """Configuration for LLM providers."""
    
    provider: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    api_key: Optional[str] = None
    
    @classmethod
    def from_settings(cls) -> "ProviderConfig":
        """Create config from application settings."""
        api_key = None
        
        if settings.LLM_PROVIDER == "openai":
            api_key = settings.OPENAI_API_KEY
        elif settings.LLM_PROVIDER == "gemini":
            api_key = settings.GEMINI_API_KEY
        elif settings.LLM_PROVIDER == "claude":
            api_key = settings.CLAUDE_API_KEY
        
        return cls(
            provider=settings.LLM_PROVIDER,
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            timeout=settings.LLM_TIMEOUT,
            api_key=api_key
        )
