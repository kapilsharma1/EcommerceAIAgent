"""OpenAI LLM client wrapper with structured output support."""
import json
import logging
from datetime import date
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
        logger.info("LLM: get_structured_response - START")
        logger.debug(f"LLM: System prompt length: {len(system_prompt)}")
        logger.debug(f"LLM: Number of messages: {len(messages)}")
        
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
            
            logger.info("LLM: Sending request to OpenAI...")
            response = await self.client.chat.completions.create(**request_params)
            logger.info("LLM: Response received from OpenAI")
            
            content = response.choices[0].message.content
            if not content:
                logger.error("LLM: Empty response from LLM")
                raise ValueError("Empty response from LLM")
            
            logger.debug(f"LLM: Response content length: {len(content)}")
            logger.debug(f"LLM: Response content preview: {content[:200]}...")
            
            # Parse JSON response
            try:
                parsed = json.loads(content)
                logger.info("LLM: JSON parsed successfully")
                logger.debug(f"LLM: Parsed response keys: {list(parsed.keys()) if isinstance(parsed, dict) else 'Not a dict'}")
                return parsed
            except json.JSONDecodeError as e:
                logger.error(f"LLM: JSON decode error: {str(e)}")
                logger.error(f"LLM: Raw content: {content}")
                raise ValueError(f"Invalid JSON response from LLM: {e}")
            
        except json.JSONDecodeError as e:
            logger.error(f"LLM: JSON decode error: {str(e)}", exc_info=True)
            raise ValueError(f"Invalid JSON response from LLM: {e}")
        except Exception as e:
            logger.error(f"LLM: Request failed: {str(e)}", exc_info=True)
            raise RuntimeError(f"LLM request failed: {e}")
    
    @traceable(name="llm_structured_decision")
    async def get_agent_decision(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        order_data: Optional[Dict[str, Any]] = None,
        policy_context: Optional[str] = None,
        current_date: Optional[date] = None,
    ) -> Tuple[LLMResponse, str]:
        """
        Get structured agent decision from LLM.
        
        Args:
            user_message: Current user message
            conversation_history: Previous conversation messages
            order_data: Optional order data
            policy_context: Optional policy context from RAG
            current_date: Optional current date for time-based decision making
            
        Returns:
            Tuple of (LLMResponse with structured decision, next_step value)
        """
        logger.info("LLM: get_agent_decision - START")
        logger.info(f"LLM: user_message: {user_message}")
        logger.info(f"LLM: conversation_history length: {len(conversation_history)}")
        logger.info(f"LLM: order_data: {'present' if order_data else 'None'}")
        logger.info(f"LLM: policy_context: {'present' if policy_context else 'None'}")
        logger.info(f"LLM: current_date: {current_date}")
        
        system_prompt = """You are an AI customer support agent.

Rules:
- You must respond ONLY in valid JSON
- You may NEVER execute actions
- You may ONLY propose actions
- If information is missing, ask for tools
- ALWAYS provide a helpful final_answer - NEVER return null or empty string
- If order data is missing, explain that you need to fetch the order information
- If you cannot answer due to missing data, provide a helpful message explaining what information is needed
- Be conversational and helpful in your final_answer
- Use the Current Date provided in context to determine if orders are delayed
- Compare Current Date with expected_delivery_date to calculate delay duration
- Apply time-based cancellation rules (e.g., 7+ days delayed = auto-eligible for cancellation)

Output schema:
{
  "analysis": "string",
  "final_answer": "string",  // REQUIRED: Must always be a non-empty string, never null
  "action": "NONE | CANCEL_ORDER | REFUND_ORDER",
  "order_id": "string | null",
  "confidence": number,
  "requires_human_approval": boolean,
  "next_step": "NONE | FETCH_ORDER | FETCH_POLICY"
}

IMPORTANT: final_answer must ALWAYS be a non-empty string. If you need more information, say something like:
- "I need to fetch your order information to answer your question. Let me retrieve that for you."
- "I don't have the order details yet. I'll fetch that information now."
- Never return null or empty string for final_answer.

Do NOT add extra fields."""

        # Build context
        context_parts = []
        if current_date:
            context_parts.append(f"Current Date: {current_date.isoformat()}")
            logger.debug(f"LLM: Added current_date to context: {current_date}")
        if order_data:
            context_parts.append(f"Order Data: {json.dumps(order_data, default=str)}")
            logger.debug(f"LLM: Added order_data to context (length: {len(context_parts[-1])})")
        if policy_context:
            context_parts.append(f"Policy Context: {policy_context}")
            logger.debug(f"LLM: Added policy_context to context (length: {len(context_parts[-1])})")
        
        context = "\n\n".join(context_parts) if context_parts else "No additional context available."
        logger.debug(f"LLM: Total context length: {len(context)}")
        
        # Build messages
        messages = []
        for msg in conversation_history:
            messages.append(msg)
        
        user_content = f"Context:\n{context}\n\nUser Message: {user_message}"
        messages.append({
            "role": "user",
            "content": user_content
        })
        logger.debug(f"LLM: User message content length: {len(user_content)}")
        
        # Get structured response
        logger.info("LLM: Calling get_structured_response...")
        response_dict = await self.get_structured_response(
            messages=messages,
            system_prompt=system_prompt,
        )
        
        # Log raw response for debugging
        logger.info(f"LLM: Raw response received: {response_dict}")
        
        # Extract next_step before creating LLMResponse (since it's not in the model anymore)
        next_step = response_dict.pop("next_step", "NONE")
        logger.info(f"LLM: Extracted next_step: {next_step}")
        
        # Normalize response dict (convert action to enum, fix requires_human_approval, add defaults)
        logger.info("LLM: Normalizing response dict...")
        normalized_dict = normalize_llm_response_dict(response_dict)
        
        # Log normalized response for debugging
        logger.info(f"LLM: Normalized response: {normalized_dict}")
        
        # Validate and return both LLMResponse and next_step
        try:
            llm_response = LLMResponse(**normalized_dict)
            logger.info(f"LLM: LLMResponse created - action: {llm_response.action}, confidence: {llm_response.confidence}")
            logger.info("LLM: get_agent_decision - END")
            return llm_response, next_step
        except Exception as e:
            logger.error(f"LLM: Error creating LLMResponse: {str(e)}", exc_info=True)
            logger.error(f"LLM: normalized_dict: {normalized_dict}")
            raise

