from typing import List, Optional
import logging
from ..common.exceptions import EmbeddingError
from ..config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating embeddings from text.
    Supports multiple embedding providers (OpenAI, Gemini, Qdrant, pgvector).
    """
    
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.model = settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        self._initialize_provider()
    
    def _initialize_provider(self):
        """Initialize the appropriate embedding provider."""
        if self.provider == "openai":
            self._init_openai()
        elif self.provider == "gemini":
            self._init_gemini()
        elif self.provider == "qdrant":
            self._init_qdrant()
        elif self.provider == "pgvector":
            self._init_pgvector()
        else:
            raise EmbeddingError(f"Unsupported embedding provider: {self.provider}")
    
    def _init_openai(self):
        """Initialize OpenAI embedding client."""
        try:
            import openai
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info(f"Initialized OpenAI embedding service with model: {self.model}")
        except ImportError:
            raise EmbeddingError("OpenAI package not installed")
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize OpenAI embedding service: {str(e)}")
    
    def _init_gemini(self):
        """Initialize Gemini embedding client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._genai = genai
            logger.info(f"Initialized Gemini embedding service with model: {self.model}")
        except ImportError:
            raise EmbeddingError("google-generativeai package not installed")
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize Gemini embedding service: {str(e)}")

    def _init_qdrant(self):
        """Initialize Qdrant client for embeddings."""
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            logger.info("Initialized Qdrant embedding service")
        except ImportError:
            raise EmbeddingError("Qdrant client package not installed")
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize Qdrant embedding service: {str(e)}")
    
    def _init_pgvector(self):
        """
        pgvector is a storage backend (see VectorClient), not an embedding
        generator. EMBEDDING_PROVIDER should be 'openai' or 'gemini'; VECTOR_BACKEND
        should be 'pgvector'. These are independent settings.
        """
        raise EmbeddingError(
            "EMBEDDING_PROVIDER=pgvector is invalid — pgvector only stores vectors. "
            "Set EMBEDDING_PROVIDER=openai or gemini, and VECTOR_BACKEND=pgvector instead."
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Input text to embed
        
        Returns:
            List of float values representing the embedding
        """
        try:
            if self.provider == "openai":
                return self._openai_embedding(text)
            elif self.provider == "gemini":
                return self._gemini_embedding(text)
            elif self.provider == "qdrant":
                return self._qdrant_embedding(text)
            elif self.provider == "pgvector":
                return self._pgvector_embedding(text)
            else:
                raise EmbeddingError(f"Unknown provider: {self.provider}")
        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise EmbeddingError(f"Failed to generate embedding: {str(e)}")
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of input texts to embed
        
        Returns:
            List of embedding vectors
        """
        try:
            if self.provider == "openai":
                return self._openai_embeddings_batch(texts)
            elif self.provider == "gemini":
                return [self._gemini_embedding(t) for t in texts]
            else:
                # Fallback to individual calls for other providers
                return [self.generate_embedding(text) for text in texts]
        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {str(e)}")
            raise EmbeddingError(f"Failed to generate batch embeddings: {str(e)}")
    
    def _openai_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def _openai_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings using OpenAI."""
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def _gemini_embedding(self, text: str) -> List[float]:
        """Generate embedding using Gemini's embedding API."""
        model_name = self.model if self.model.startswith("models/") else f"models/{self.model}"
        try:
            result = self._genai.embed_content(
                model=model_name,
                content=text,
                output_dimensionality=self.dimension,
            )
        except TypeError:
            # Installed google-generativeai version doesn't support
            # output_dimensionality — fall back to the model's default size.
            logger.warning(
                "Installed google-generativeai version doesn't support "
                "output_dimensionality; using model's default embedding size instead."
            )
            result = self._genai.embed_content(
                model=model_name,
                content=text,
            )
        return result["embedding"]

    def _qdrant_embedding(self, text: str) -> List[float]:
        """Generate embedding using Qdrant's built-in encoder."""
        # Qdrant doesn't have built-in embedding generation
        # This would typically use an external model
        raise EmbeddingError("Qdrant requires external embedding model - use OpenAI or configure pgvector")
    
    def _pgvector_embedding(self, text: str) -> List[float]:
        """Generate embedding using pgvector."""
        # pgvector stores embeddings but doesn't generate them
        # This would typically use an external model
        raise EmbeddingError("pgvector requires external embedding model - use OpenAI or configure Qdrant")