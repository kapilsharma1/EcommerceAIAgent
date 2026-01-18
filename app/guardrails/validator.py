"""Output validation using Pydantic."""
import json
import logging
from typing import Dict, Any, Optional
from langsmith import traceable
from app.models.domain import LLMResponse, ActionType, NextStep
from app.llm.client import normalize_llm_response_dict

logger = logging.getLogger(__name__)


class GuardrailsValidator:
    """Output validator for LLM responses using Pydantic."""
    
    def __init__(self):
        """Initialize validator."""
        # Using Pydantic for validation (simpler and more reliable than Guardrails)
        pass
    
    @traceable(name="guardrails_validate")
    def validate(self, llm_output: Dict[str, Any]) -> LLMResponse:
        """
        Validate LLM output using Pydantic validation.
        
        Args:
            llm_output: Raw LLM output dictionary
            
        Returns:
            Validated LLMResponse
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Normalize the dict to ensure proper enum types and defaults
            normalized_output = normalize_llm_response_dict(llm_output)
            
            # Parse into LLMResponse using Pydantic (strict validation)
            response = LLMResponse(**normalized_output)
            
            # Additional business logic validations
            self._validate_business_rules(response)
            
            return response
            
        except Exception as e:
            # Log the error for debugging
            logger.error(f"Validation failed: {str(e)}", exc_info=True)
            logger.error(f"Input was: {llm_output}")
            # Return safe fallback
            return self._get_fallback_response(str(e))
    
    def _validate_business_rules(self, response: LLMResponse) -> None:
        """
        Validate business rules beyond schema.
        
        Args:
            response: LLMResponse to validate
            
        Raises:
            ValueError: If business rules are violated
        """
        # Rule: requires_human_approval must be true if action != NONE
        if response.action != ActionType.NONE and not response.requires_human_approval:
            raise ValueError(
                "requires_human_approval must be true when action is not NONE"
            )
        
        # Rule: order_id must be present if action != NONE
        if response.action != ActionType.NONE and not response.order_id:
            raise ValueError(
                "order_id must be provided when action is not NONE"
            )
        
        # Rule: confidence must be between 0 and 1
        if not (0.0 <= response.confidence <= 1.0):
            raise ValueError(
                "confidence must be between 0 and 1"
            )
    
    def _get_fallback_response(self, error_message: str) -> LLMResponse:
        """
        Get safe fallback response on validation failure.
        
        Args:
            error_message: Error message from validation
            
        Returns:
            Safe fallback LLMResponse
        """
        # Include error message in response for debugging (remove in production)
        # Temporarily include error in final_answer to help debug
        return LLMResponse(
            analysis=f"Validation error occurred: {error_message}",
            final_answer=(
                f"I apologize, but I encountered an error processing your request. "
                f"Error details: {error_message} "
                "Please check the server logs for more information."
            ),
            action=ActionType.NONE,
            order_id=None,
            confidence=0.0,
            requires_human_approval=False,
        )
    
    def validate_json_string(self, json_string: str) -> LLMResponse:
        """
        Validate JSON string output from LLM.
        
        Args:
            json_string: JSON string from LLM
            
        Returns:
            Validated LLMResponse
        """
        try:
            # Parse JSON
            parsed = json.loads(json_string)
            return self.validate(parsed)
        except json.JSONDecodeError as e:
            return self._get_fallback_response(f"Invalid JSON: {e}")

