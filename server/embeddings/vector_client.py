from typing import List, Dict, Any, Optional
import logging
from ..common.exceptions import EmbeddingError
from ..config.settings import settings

logger = logging.getLogger(__name__)


class VectorClient:
    """
    Unified interface for vector database operations.
    Supports Qdrant and pgvector for similarity search and storage.
    """
    
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.dimension = settings.EMBEDDING_DIMENSION
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the appropriate vector database client."""
        if self.provider == "qdrant":
            self._init_qdrant()
        elif self.provider == "pgvector":
            self._init_pgvector()
        else:
            # For OpenAI-only embedding generation, we might not have a vector DB
            logger.warning(f"No vector database configured for provider: {self.provider}")
            self.client = None
    
    def _init_qdrant(self):
        """Initialize Qdrant client."""
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
            logger.info("Initialized Qdrant vector client")
        except ImportError:
            raise EmbeddingError("Qdrant client package not installed")
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize Qdrant client: {str(e)}")
    
    def _init_pgvector(self):
        """Initialize pgvector client."""
        try:
            import psycopg2
            self.connection = psycopg2.connect(settings.PGVECTOR_CONNECTION_STRING)
            logger.info("Initialized pgvector vector client")
        except ImportError:
            raise EmbeddingError("psycopg2 package not installed")
        except Exception as e:
            raise EmbeddingError(f"Failed to initialize pgvector client: {str(e)}")
    
    def create_collection(self, collection_name: str, dimension: Optional[int] = None):
        """
        Create a vector collection.
        
        Args:
            collection_name: Name of the collection
            dimension: Embedding dimension (uses default if not provided)
        """
        if not self.client:
            logger.warning("No vector client configured, skipping collection creation")
            return
        
        try:
            if self.provider == "qdrant":
                self._create_qdrant_collection(collection_name, dimension or self.dimension)
            elif self.provider == "pgvector":
                self._create_pgvector_table(collection_name)
        except Exception as e:
            logger.error(f"Failed to create collection: {str(e)}")
            raise EmbeddingError(f"Failed to create collection: {str(e)}")
    
    def _create_qdrant_collection(self, collection_name: str, dimension: int):
        """Create Qdrant collection."""
        from qdrant_client.models import Distance, VectorParams, PointStruct
        
        # Check if collection exists
        collections = self.client.get_collections().collections
        existing_names = [c.name for c in collections]
        
        if collection_name not in existing_names:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
            )
            logger.info(f"Created Qdrant collection: {collection_name}")
    
    def _create_pgvector_table(self, table_name: str):
        """Create pgvector table."""
        cursor = self.connection.cursor()
        
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                vector_id VARCHAR(255) UNIQUE NOT NULL,
                embedding vector({self.dimension}),
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create index for similarity search
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS {table_name}_embedding_idx 
            ON {table_name} 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
        """)
        
        self.connection.commit()
        logger.info(f"Created pgvector table: {table_name}")
    
    def insert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Insert vectors into the collection.
        
        Args:
            collection_name: Name of the collection
            vectors: List of embedding vectors
            ids: List of unique IDs for each vector
            metadata: Optional list of metadata dicts for each vector
        """
        if not self.client:
            logger.warning("No vector client configured, skipping vector insertion")
            return
        
        try:
            if self.provider == "qdrant":
                self._insert_qdrant_vectors(collection_name, vectors, ids, metadata)
            elif self.provider == "pgvector":
                self._insert_pgvector_vectors(collection_name, vectors, ids, metadata)
        except Exception as e:
            logger.error(f"Failed to insert vectors: {str(e)}")
            raise EmbeddingError(f"Failed to insert vectors: {str(e)}")
    
    def _insert_qdrant_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]]
    ):
        """Insert vectors into Qdrant."""
        from qdrant_client.models import PointStruct
        
        points = []
        for i, (vector, id_) in enumerate(zip(vectors, ids)):
            point = PointStruct(
                id=id_,
                vector=vector,
                payload=metadata[i] if metadata else {}
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Inserted {len(vectors)} vectors into Qdrant collection: {collection_name}")
    
    def _insert_pgvector_vectors(
        self,
        table_name: str,
        vectors: List[List[float]],
        ids: List[str],
        metadata: Optional[List[Dict[str, Any]]]
    ):
        """Insert vectors into pgvector."""
        cursor = self.connection.cursor()
        
        for i, (vector, id_) in enumerate(zip(vectors, ids)):
            meta = metadata[i] if metadata else {}
            cursor.execute(
                f"""
                INSERT INTO {table_name} (vector_id, embedding, metadata)
                VALUES (%s, %s::vector, %s::jsonb)
                ON CONFLICT (vector_id) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    metadata = EXCLUDED.metadata
                """,
                (id_, str(vector), meta)
            )
        
        self.connection.commit()
        logger.info(f"Inserted {len(vectors)} vectors into pgvector table: {table_name}")
    
    def search_similar(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors.
        
        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Optional minimum similarity score
        
        Returns:
            List of results with IDs, scores, and metadata
        """
        if not self.client:
            logger.warning("No vector client configured, returning empty results")
            return []
        
        try:
            if self.provider == "qdrant":
                return self._search_qdrant(collection_name, query_vector, limit, score_threshold)
            elif self.provider == "pgvector":
                return self._search_pgvector(collection_name, query_vector, limit, score_threshold)
        except Exception as e:
            logger.error(f"Failed to search vectors: {str(e)}")
            raise EmbeddingError(f"Failed to search vectors: {str(e)}")
    
    def _search_qdrant(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int,
        score_threshold: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Search Qdrant for similar vectors."""
        from qdrant_client.models import Filter
        
        search_params = {
            "collection_name": collection_name,
            "query_vector": query_vector,
            "limit": limit
        }
        
        if score_threshold:
            search_params["score_threshold"] = score_threshold
        
        results = self.client.search(**search_params)
        
        return [
            {
                "id": result.id,
                "score": result.score,
                "metadata": result.payload
            }
            for result in results
        ]
    
    def _search_pgvector(
        self,
        table_name: str,
        query_vector: List[float],
        limit: int,
        score_threshold: Optional[float]
    ) -> List[Dict[str, Any]]:
        """Search pgvector for similar vectors."""
        cursor = self.connection.cursor()
        
        query = f"""
            SELECT vector_id, 1 - (embedding <=> %s::vector) as similarity, metadata
            FROM {table_name}
        """
        
        if score_threshold:
            query += " WHERE 1 - (embedding <=> %s::vector) >= %s"
            cursor.execute(query, (str(query_vector), score_threshold))
        else:
            query += " ORDER BY embedding <=> %s::vector LIMIT %s"
            cursor.execute(query, (str(query_vector), limit))
        
        results = cursor.fetchall()
        
        return [
            {
                "id": row[0],
                "score": row[1],
                "metadata": row[2]
            }
            for row in results
        ]
    
    def delete_vector(self, collection_name: str, vector_id: str):
        """
        Delete a vector from the collection.
        
        Args:
            collection_name: Name of the collection
            vector_id: ID of the vector to delete
        """
        if not self.client:
            logger.warning("No vector client configured, skipping vector deletion")
            return
        
        try:
            if self.provider == "qdrant":
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=[vector_id]
                )
            elif self.provider == "pgvector":
                cursor = self.connection.cursor()
                cursor.execute(
                    f"DELETE FROM {collection_name} WHERE vector_id = %s",
                    (vector_id,)
                )
                self.connection.commit()
            
            logger.info(f"Deleted vector {vector_id} from {collection_name}")
        except Exception as e:
            logger.error(f"Failed to delete vector: {str(e)}")
            raise EmbeddingError(f"Failed to delete vector: {str(e)}")
