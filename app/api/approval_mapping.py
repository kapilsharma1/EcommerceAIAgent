"""Shared storage for approval_id to conversation_id mapping."""
from typing import Dict

# Store approval_id -> conversation_id mapping for graph resumption
# In production, use Redis or database instead of in-memory dict
approval_to_conversation: Dict[str, str] = {}

