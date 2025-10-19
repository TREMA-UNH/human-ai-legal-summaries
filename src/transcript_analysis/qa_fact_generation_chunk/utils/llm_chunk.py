# from outlines import models, generate
from typing import List
from transcript_analysis.models.pymodels import Conversation, Sentence, SentenceList
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
import logging
import json

logger = logging.getLogger(__name__)

def generate_sentence_for_all_pairs(bedrock_client, CONFIG, print_usage: bool, pairs):
    """Process question-answer pairs using the Converse API."""
    # Create the prompt
    prompt = (
        "Given the following list of question-answer pairs, generate a JSON array where each object contains:\n"
        "- \"sentence\": a concise, third-person sentence generated ONLY from the corresponding question and answer.\n\n"
        "Instructions:\n"
        "- Use only the content of each Q&A pair to generate the sentence.\n"
        "- Include factual details like dates, numbers, money amounts, and exhibit numbers.\n"
        "- Use earlier Q&A pairs only to resolve pronouns or ambiguous references.\n"
        "- When referring to documents, use the exhibit number from the question, answer, or the latest mentioned in prior pairs.\n\n"
        f"Input:\n{json.dumps(pairs, indent=2)}\n\n"
        "Output: a JSON array of objects (same order and count as the input), each with a single field \"sentence\"."
        )
    # Define the JSON schema for the tool
    tool_schema = {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "sentence": {
                            "type": "string",
                            "description": "Concise third-person sentence based on the corresponding Q&A pair"
                        }
                    },
                    "required": ["sentence"]
                }
            }
        },
        "required": ["results"]
    }
    logger.debug(prompt)
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    results = generate_structured_output(
        bedrock_client=bedrock_client,
        messages=messages,
        tool_schema=tool_schema,
        tool_schema_name="generate_sentence_for_all",
        description="Tool for generating 3rd person narrative sentences out of Q&A pairs",
        model_id=CONFIG.model_path,
        obj=SentenceList,
        max_tokens=CONFIG.max_tokens,
        print_usage=print_usage
    )
    logger.debug(results)
    return results