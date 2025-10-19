# from outlines import models, generate
from typing import List
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
import logging
import json
from transcript_analysis.models.pymodels import Fact, FactAnnotation, FactAnnotationList, AnnotatedFact

logger = logging.getLogger(__name__)


def generate_segments_for_all_pairs(
    bedrock_client,
    CONFIG,
    print_usage: bool,
    pairs: List[dict],
) -> FactAnnotationList:
    """Process question-answer pairs using the Converse API with context from previous annotations."""

    prompt = (
        "You are analyzing question-answer pairs from a deposition transcript to identify coherent thematic segments. "
        "Your goal is to group related questions based on the attorney's investigative strategy and line of inquiry.\n\n"
        
        "SEGMENTATION CRITERIA:\n"
        "- Create a new segment only when the attorney shifts to a fundamentally different investigative theme\n"
        "- Focus on the attorney's intent and questioning strategy, not superficial topic changes\n"
        "- Maintain segments even when specific entities, dates, or details change within the same investigative area\n\n"
        
        "OUTPUT REQUIREMENTS:\n"
        "For each question-answer pair, provide:\n"
        "- 'segment_id': Integer starting from 1, incrementing only when a new thematic segment begins.\n"
        "- 'segment_topic': Concise one-line summary describing the most important parts of the segment"
        "- 'reasoning': Brief justification for segmentation decision. Use 'None' for same-segment pairs, or explain the shift for new segments.\n\n"
        
        "CONSISTENCY RULES:\n"
        "- All pairs within the same segment must have identical 'segment_topic' text\n"
        "- Review the full context before assigning topics to ensure logical grouping\n"
        "- Prioritize investigative coherence over surface-level topic similarity\n\n"
        
        f"DEPOSITION DATA:\n{json.dumps(pairs, indent=2)}\n\n"
        
        f"Return a JSON array containing exactly {len(pairs)} objects in the original order, "
        f"each with 'segment_id', 'segment_topic', and 'reasoning' fields."
    )



    tool_schema = {
        "type": "object",
        "properties": {
            "fact_annotations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "segment_id": {
                            "type": "integer",
                            "description": "Topic segment number starting from 1 for new topics in this chunk."
                        },
                        "segment_topic": {
                            "type": "string",
                            "description": "Segment topic showing the mutual theme of pairs belonging to that segment."
                        },"reasoning": {
                            "type": "string",
                            "description": "Rational behind choosing this topic."
                        }
                        

                    },
                    "required": ["segment_id",
                                 "segment_topic", "reasoning"
                                 ]
                }
            }
        },
        "required": ["fact_annotations"]
    }

    logger.debug(f"Prompt: {prompt}")
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    results = generate_structured_output(
        bedrock_client=bedrock_client,
        messages=messages,
        tool_schema=tool_schema,
        tool_schema_name="assign_segment_for_pairs",
        description="Tool for assigning segment_id, segment topic and reasoning for each Q&A pair",
        model_id=CONFIG.model_path,
        obj=FactAnnotationList,
        max_tokens=CONFIG.max_tokens,
        print_usage=print_usage
    )
    logger.debug(f"Raw result: {results}")
    return results