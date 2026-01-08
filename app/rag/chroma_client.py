"""ChromaDB RAG client for policy retrieval."""
from typing import List, Dict, Any, Optional
import chromadb
from langsmith import traceable
from app.config import settings
from app.rag.embedder import Embedder


class ChromaClient:
    """ChromaDB client for vector storage and retrieval."""
    
    def __init__(self):
        """Initialize ChromaDB client."""
        # Use persistent storage in a local directory
        self.persist_directory = "./chroma_db"
        self.collection_name = "order-policies"
        self.embedder = Embedder()
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        # Get or create collection
        # Note: ChromaDB will handle embeddings, but we're using our own embedder
        # So we'll store pre-computed embeddings
        try:
            self.collection = self.client.get_collection(
                name=self.collection_name,
                embedding_function=None  # We provide our own embeddings
            )
            print(f"Loaded existing ChromaDB collection: {self.collection_name}")
        except Exception:
            # Collection doesn't exist, create it
            self.collection = self.client.create_collection(
                name=self.collection_name,
                embedding_function=None  # We provide our own embeddings
            )
            print(f"Created new ChromaDB collection: {self.collection_name}")
    
    @traceable(name="chroma_upsert")
    async def upsert_policy(
        self,
        policy_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Upsert a policy document into ChromaDB.
        
        Args:
            policy_id: Unique identifier for the policy
            text: Policy text content
            metadata: Optional metadata dictionary
        """
        try:
            # Generate embedding
            embedding = await self.embedder.embed_text(text)
            
            # Prepare metadata
            metadata = metadata or {}
            metadata["text"] = text
            
            # Upsert to ChromaDB
            self.collection.upsert(
                ids=[policy_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to upsert policy: {e}")
    
    @traceable(name="chroma_query")
    async def query_policies(
        self,
        query_text: str,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Query policies using semantic similarity.
        
        Args:
            query_text: Query text
            top_k: Number of results to return
            
        Returns:
            List of policy chunks with metadata
        """
        try:
            # Generate query embedding
            query_embedding = await self.embedder.embed_text(query_text)
            
            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            policy_chunks = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    policy_chunks.append({
                        "id": results["ids"][0][i],
                        "score": 1 - results["distances"][0][i],  # Convert distance to similarity
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                    })
            
            return policy_chunks
            
        except Exception as e:
            raise RuntimeError(f"Failed to query policies: {e}")
    
    @traceable(name="chroma_batch_upsert")
    async def upsert_policies_batch(
        self,
        policies: List[Dict[str, str]],
    ) -> None:
        """
        Upsert multiple policy documents.
        
        Args:
            policies: List of dictionaries with 'id', 'text', and optional 'metadata'
        """
        try:
            # Generate embeddings for all policies
            texts = [policy["text"] for policy in policies]
            embeddings = await self.embedder.embed_batch(texts)
            
            # Prepare data for batch upsert
            ids = [policy["id"] for policy in policies]
            documents = texts
            metadatas = []
            
            for policy in policies:
                metadata = policy.get("metadata", {})
                metadata["text"] = policy["text"]
                metadatas.append(metadata)
            
            # Batch upsert
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
        except Exception as e:
            raise RuntimeError(f"Failed to batch upsert policies: {e}")

