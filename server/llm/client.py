from typing import Optional, Dict, Any, List
import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from .provider_config import ProviderConfig
from ..common.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified interface for LLM providers.
    All LLM calls in the service must go through this client.
    """
    
    def __init__(self, config: Optional[ProviderConfig] = None):
        self.config = config or ProviderConfig.from_settings()
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the appropriate LLM provider client."""
        if self.config.provider == "openai":
            self._init_openai()
        elif self.config.provider == "gemini":
            self._init_gemini()
        elif self.config.provider == "claude":
            self._init_claude()
        else:
            raise LLMProviderError(f"Unsupported provider: {self.config.provider}")
    
    def _init_openai(self):
        """Initialize OpenAI client."""
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.config.api_key)
            self.provider_type = "openai"
            logger.info(f"Initialized OpenAI client with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("OpenAI package not installed")
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize OpenAI client: {str(e)}")
    
    def _init_gemini(self):
        """Initialize Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.config.api_key)
            self.client = genai.GenerativeModel(self.config.model)
            self.provider_type = "gemini"
            logger.info(f"Initialized Gemini client with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("Google Generative AI package not installed")
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize Gemini client: {str(e)}")
    
    def _init_claude(self):
        """Initialize Claude client."""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.config.api_key)
            self.provider_type = "claude"
            logger.info(f"Initialized Claude client with model: {self.config.model}")
        except ImportError:
            raise LLMProviderError("Anthropic package not installed")
        except Exception as e:
            raise LLMProviderError(f"Failed to initialize Claude client: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True
    )
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate chat completion with token usage tracking and retry logic.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Dict containing 'content', 'token_usage', 'latency_ms'
        """
        start_time = time.time()
        
        try:
            if self.provider_type == "openai":
                response = self._openai_completion(
                    messages, temperature, max_tokens, **kwargs
                )
            elif self.provider_type == "gemini":
                response = self._gemini_completion(
                    messages, temperature, max_tokens, **kwargs
                )
            elif self.provider_type == "claude":
                response = self._claude_completion(
                    messages, temperature, max_tokens, **kwargs
                )
            else:
                raise LLMProviderError(f"Unknown provider: {self.provider_type}")
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"LLM call completed: provider={self.provider_type}, "
                f"model={self.config.model}, tokens={response.get('token_usage', {}).get('total_tokens', 'unknown')}, "
                f"latency={latency_ms}ms"
            )
            
            response["latency_ms"] = latency_ms
            return response
            
        except Exception as e:
            logger.error(f"LLM call failed: {str(e)}")
            raise LLMProviderError(f"LLM call failed: {str(e)}")
    
    def _openai_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """OpenAI chat completion."""
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            **kwargs
        )
        
        return {
            "content": response.choices[0].message.content,
            "token_usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        }
    
    def _gemini_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Gemini chat completion."""
        # Convert OpenAI-style messages to Gemini format
        gemini_messages = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_messages.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        response = self.client.generate_content(
            gemini_messages,
            generation_config={
                "temperature": temperature or self.config.temperature,
                "max_output_tokens": max_tokens or self.config.max_tokens,
                **kwargs
            }
        )
        
        # Gemini doesn't provide token usage in the same way
        # Gemini exposes token counts via response.usage_metadata
        usage = getattr(response, "usage_metadata", None)
        prompt_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        completion_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        total_tokens = getattr(usage, "total_token_count", None) if usage else None
        if total_tokens is None:
            total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)

        finish_reason = None
        if getattr(response, "candidates", None):
            finish_reason = str(response.candidates[0].finish_reason)

        return {
            "content": response.text,
            "token_usage": {
                "prompt_tokens": prompt_tokens or 0,
                "completion_tokens": completion_tokens or 0,
                "total_tokens": total_tokens or 0
            },
            "finish_reason": finish_reason,
        }
    
    def _claude_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ) -> Dict[str, Any]:
        """Claude chat completion."""
        response = self.client.messages.create(
            model=self.config.model,
            messages=messages,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            **kwargs
        )
        
        return {
            "content": response.content[0].text,
            "token_usage": {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens
            }
        }
    
    def stream_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Generate streaming chat completion.
        
        Yields chunks of content as they are generated.
        """
        start_time = time.time()
        
        try:
            if self.provider_type == "openai":
                yield from self._openai_stream(
                    messages, temperature, max_tokens, **kwargs
                )
            elif self.provider_type == "claude":
                yield from self._claude_stream(
                    messages, temperature, max_tokens, **kwargs
                )
            else:
                raise LLMProviderError(f"Streaming not supported for {self.provider_type}")
            
            latency_ms = int((time.time() - start_time) * 1000)
            logger.info(f"Streaming completed in {latency_ms}ms")
            
        except Exception as e:
            logger.error(f"Streaming failed: {str(e)}")
            raise LLMProviderError(f"Streaming failed: {str(e)}")
    
    def _openai_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ):
        """OpenAI streaming completion."""
        stream = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=temperature or self.config.temperature,
            max_tokens=max_tokens or self.config.max_tokens,
            stream=True,
            **kwargs
        )
        
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    
    def _claude_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        **kwargs
    ):
        """Claude streaming completion."""
        with self.client.messages.stream(
            model=self.config.model,
            messages=messages,
            max_tokens=max_tokens or self.config.max_tokens,
            temperature=temperature or self.config.temperature,
            **kwargs
        ) as stream:
            for text in stream.text_stream:
                yield text
