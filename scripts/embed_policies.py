"""Script to embed policy documents into ChromaDB."""
import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.rag.chroma_client import ChromaClient


async def embed_policies():
    """Embed all policy documents from data/policies into ChromaDB."""
    print("Starting policy embedding...")
    
    # Initialize ChromaDB client
    client = ChromaClient()
    
    # Get policy directory
    policy_dir = Path(__file__).parent.parent / "data" / "policies"
    
    if not policy_dir.exists():
        print(f"Policy directory not found: {policy_dir}")
        return
    
    # Read all policy files
    policies = []
    for policy_file in policy_dir.glob("*.txt"):
        print(f"Reading {policy_file.name}...")
        with open(policy_file, "r", encoding="utf-8") as f:
            content = f.read()
            
            policies.append({
                "id": f"policy-{policy_file.stem}",
                "text": content,
                "metadata": {
                    "filename": policy_file.name,
                    "source": "order-policies",
                }
            })
    
    if not policies:
        print("No policy files found!")
        return
    
    print(f"Found {len(policies)} policy files")
    
    # Embed and upsert to ChromaDB
    try:
        print("Embedding and uploading to ChromaDB...")
        await client.upsert_policies_batch(policies)
        print(f"Successfully embedded {len(policies)} policies into ChromaDB!")
        print(f"Collection: {client.collection_name}")
        print(f"Storage location: {client.persist_directory}")
    except Exception as e:
        print(f"Error embedding policies: {e}")
        raise


if __name__ == "__main__":
    # Ensure environment variables are loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(embed_policies())

