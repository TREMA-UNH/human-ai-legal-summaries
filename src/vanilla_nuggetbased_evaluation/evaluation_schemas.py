"""Schema definitions for structured output evaluation."""

from typing import Dict, Any


class EvaluationSchemas:
    """Container for all evaluation schemas."""
    
    @staticmethod
    def get_nugget_coverage_schema():
        return {
            "type": "object",  # Since each nugget is a single object
            "properties": {
                "text": {"type": "string"},  # Nugget text
                "present": {"type": "integer", "enum": [0, 1]},  # Score options: 0 or 1
                "explanation": {"type": "string"}  # Explanation of the score
            },
            "required": ["text", "score", "explanation"]  
        }

   
    
    @staticmethod
    def get_detail_coverage_schema():
        return {
            "type": "object",
            "properties": {
                "nuggets": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                            "score": {"type": "integer", "enum": [0, 1, 2]},
                            "explanation": {"type": "string"},
                        },
                        "required": [ "text", "score", "explanation"]
                    }
                }
            },
            "required": ["nuggets"]
        }

    
    