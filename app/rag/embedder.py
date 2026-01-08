"""OpenAI embedding API wrapper for RAG.

This uses OpenAI's embedding API to generate embeddings for RAG.
The embeddings are stored in ChromaDB vector database.
"""
from typing import List
from openai import AsyncOpenAI
from langsmith import traceable
from app.config import settings


class Embedder:
    """OpenAI embedding API client for generating embeddings.
    
    Uses OpenAI's text-embedding-3-small model for generating embeddings.
    The embeddings are stored in ChromaDB vector database.
    """
    
    def __init__(self):
        """Initialize OpenAI embeddings client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = "text-embedding-3-small"  # 1536 dimensions
        self.dimension = 1536
    
    @traceable(name="generate_embeddings")
    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text using OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions)
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            
            # OpenAI returns embeddings in the 'data' field
            if response.data and len(response.data) > 0:
                return response.data[0].embedding
            else:
                raise RuntimeError(f"Unexpected response format: {response}")
                    
        except Exception as e:
            raise RuntimeError(f"Embedding generation failed: {e}")
    
    @traceable(name="generate_batch_embeddings")
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts using OpenAI.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors (each 1536 dimensions)
        """
        try:
            # OpenAI's API supports batch requests natively
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            
            # Extract embeddings from response
            embeddings = [item.embedding for item in response.data]
            
            # Ensure we have the same number of embeddings as inputs
            if len(embeddings) != len(texts):
                raise RuntimeError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )
            
            return embeddings
                    
        except Exception as e:
            raise RuntimeError(f"Batch embedding generation failed: {e}")
