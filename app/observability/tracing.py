"""LangSmith observability and tracing."""
import os
from typing import Optional, Dict, Any
from langsmith import Client, traceable
from app.config import settings


class Observability:
    """LangSmith observability manager."""
    
    def __init__(self):
        """Initialize LangSmith client."""
        if settings.langchain_tracing_v2 and settings.langchain_api_key:
            self.client = Client(api_key=settings.langchain_api_key)
            self.enabled = True
        else:
            self.client = None
            self.enabled = False
    
    def setup_langsmith(self):
        """Setup LangSmith environment variables."""
        if settings.langchain_tracing_v2:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            if settings.langchain_api_key:
                os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
    
    def tag_trace(self, trace_id: str, tags: Dict[str, str]):
        """
        Tag a trace with metadata.
        
        Args:
            trace_id: Trace ID
            tags: Tags to add
        """
        if not self.enabled or not self.client:
            return
        
        try:
            # LangSmith automatically tags traces via decorators
            # This is for manual tagging if needed
            pass
        except Exception:
            # Silently fail if tagging fails
            pass


# Global observability instance
observability = Observability()


def setup_observability():
    """Setup observability for the application."""
    observability.setup_langsmith()

