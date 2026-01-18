"""OpenAI LLM client wrapper with structured output support."""
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from openai import AsyncOpenAI
from langchain_openai import ChatOpenAI
from langsmith import traceable
from app.config import settings
from app.models.domain import LLMResponse, ActionType

logger = logging.getLogger(__name__)


def normalize_llm_response_dict(response_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize LLM response dictionary to ensure proper types for LLMResponse model.
    
    Converts action string to ActionType enum and ensures requires_human_approval
    is set correctly based on action. Also provides defaults for missing fields.
    
    Args:
        response_dict: Raw response dictionary from LLM
        
    Returns:
        Normalized dictionary ready for LLMResponse creation
    """
    # Create a copy to avoid mutating the original
    normalized = response_dict.copy()
    
    # Ensure all required fields have defaults if missing or None
    if not normalized.get("analysis") or normalized.get("analysis") is None:
        normalized["analysis"] = "No analysis provided"
    
    if not normalized.get("final_answer") or normalized.get("final_answer") is None:
        normalized["final_answer"] = "I apologize, but I couldn't generate a response."
    
    if normalized.get("confidence") is None:
        normalized["confidence"] = 0.0
    
    if normalized.get("requires_human_approval") is None:
        normalized["requires_human_approval"] = False
    
    # Convert action string to ActionType enum if needed
    action_value = normalized.get("action", "NONE")
    if isinstance(action_value, str):
        try:
            action = ActionType(action_value)
        except ValueError:
            # Fallback to NONE if invalid action
            action = ActionType.NONE
        normalized["action"] = action
    elif not isinstance(action_value, ActionType):
        # If it's neither string nor ActionType, default to NONE
        action = ActionType.NONE
        normalized["action"] = action
    else:
        action = action_value
    
    # Ensure requires_human_approval is set correctly based on action
    if action != ActionType.NONE:
        # If action is not NONE, requires_human_approval must be True
        normalized["requires_human_approval"] = True
    
    return normalized


class LLMClient:
    """OpenAI client wrapper with LangSmith tracing."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.chat_model = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key=settings.openai_api_key,
        )
    
    @traceable(name="llm_chat_completion")
    async def get_structured_response(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Get structured JSON response from OpenAI.
        
        Args:
            messages: List of message dictionaries
            system_prompt: System prompt for the conversation
            response_format: Optional response format specification
            
        Returns:
            Parsed JSON response as dictionary
        """
        try:
            # Prepare messages with system prompt
            formatted_messages = [
                {"role": "system", "content": system_prompt},
                *messages
            ]
            
            # Build request parameters
            request_params = {
                "model": "gpt-4",
                "messages": formatted_messages,
                "temperature": 0.7,
            }
            
            # Only include response_format if explicitly provided
            # Some models don't support json_object response_format
            if response_format is not None:
                request_params["response_format"] = response_format
            
            response = await self.client.chat.completions.create(**request_params)
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from LLM")
            
            # Parse JSON response
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            raise RuntimeError(f"LLM request failed: {e}")
    
    @traceable(name="llm_structured_decision")
    async def get_agent_decision(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        order_data: Optional[Dict[str, Any]] = None,
        policy_context: Optional[str] = None,
    ) -> Tuple[LLMResponse, str]:
        """
        Get structured agent decision from LLM.
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            order_data: Optional order data
            policy_context: Optional policy context from RAG
            
        Returns:
            Tuple of (LLMResponse with structured decision, next_step value)
        """
        system_prompt = """You are an AI customer support agent.

Rules:
- You must respond ONLY in valid JSON
- You may NEVER execute actions
- You may ONLY propose actions
- If information is missing, ask for tools

Output schema:
{
  "analysis": "string",
  "final_answer": "string",
  "action": "NONE | CANCEL_ORDER | REFUND_ORDER",
  "order_id": "string | null",
  "confidence": number,
  "requires_human_approval": boolean,
  "next_step": "NONE | FETCH_ORDER | FETCH_POLICY"
}

Do NOT add extra fields."""

        # Build context
        context_parts = []
        if order_data:
            context_parts.append(f"Order Data: {json.dumps(order_data, default=str)}")
        if policy_context:
            context_parts.append(f"Policy Context: {policy_context}")
        
        context = "\n\n".join(context_parts) if context_parts else "No additional context available."
        
        # Build messages
        messages = []
        for msg in conversation_history:
            messages.append(msg)
        
        messages.append({
            "role": "user",
            "content": f"Context:\n{context}\n\nUser Message: {user_message}"
        })
        
        # Get structured response
        response_dict = await self.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
        )
        
        # Log raw response for debugging
        logger.debug(f"Raw LLM response: {response_dict}")
        
        # Extract next_step before creating LLMResponse (since it's not in the model anymore)
        next_step = response_dict.pop("next_step", "NONE")
        
        # Normalize response dict (convert action to enum, fix requires_human_approval, add defaults)
        normalized_dict = normalize_llm_response_dict(response_dict)
        
        # Log normalized response for debugging
        logger.debug(f"Normalized response: {normalized_dict}")
        
        # Validate and return both LLMResponse and next_step
        llm_response = LLMResponse(**normalized_dict)
        return llm_response, next_step

