"""Guardrails AI output validation."""
import json
from typing import Dict, Any, Optional
from guardrails import Guard
from langsmith import traceable
from app.models.domain import LLMResponse, ActionType, NextStep


class GuardrailsValidator:
    """Guardrails AI validator for LLM outputs."""
    
    def __init__(self):
        """Initialize Guardrails validator."""
        # Define the expected JSON schema
        schema = {
            "type": "object",
            "properties": {
                "analysis": {"type": "string"},
                "final_answer": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["NONE", "CANCEL_ORDER", "REFUND_ORDER"]
                },
                "order_id": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "requires_human_approval": {"type": "boolean"},
            },
            "required": [
                "analysis",
                "final_answer",
                "action",
                "confidence",
                "requires_human_approval"
            ],
            "additionalProperties": False
        }
        
        # Create Guard with validators
        self.guard = Guard.from_pydantic(output_class=LLMResponse)
    
    @traceable(name="guardrails_validate")
    def validate(self, llm_output: Dict[str, Any]) -> LLMResponse:
        """
        Validate LLM output against guardrails.
        
        Args:
            llm_output: Raw LLM output dictionary
            
        Returns:
            Validated LLMResponse
            
        Raises:
            ValueError: If validation fails
        """
        try:
            # Use Guardrails to validate
            validated_output = self.guard.validate(
                llm_output,
                metadata={"strict": True}
            )
            
            # Parse into LLMResponse
            # Guardrails returns validated dict, convert to model
            response = LLMResponse.model_validate(validated_output)
            
            # Additional business logic validations
            self._validate_business_rules(response)
            
            return response
            
        except Exception as e:
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
        return LLMResponse(
            analysis=f"Validation error occurred: {error_message}",
            final_answer=(
                "I apologize, but I encountered an error processing your request. "
                "Please try rephrasing your question or contact support for assistance."
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

