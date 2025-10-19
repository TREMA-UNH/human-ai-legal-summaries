# from outlines import models, generate
from typing import List
from transcript_analysis.models.pymodels import Conversation, Sentence
from .bedrock_adapter import generate_structured_output
import logging

logger = logging.getLogger(__name__)


def generate_speakers(bedrock_client, CONFIG, context_lines: str, print_usage: bool):
    """Identify speakers (Q and A) from a transcript excerpt using an LLM.

    Args:
        model: The LLM model instance.
        context_lines: List of transcript lines for context.

    Returns:
        Conversation: Structured output with Q and A speaker names.
    """

    prompt = f"""Analyze this transcript excerpt and identify the speakers.

    Transcript:
    {context_lines}

    Instructions: 
    - Identify who is asking the questions (the Q speaker)
    - Identify who is answering the questions (the A speaker)
    - Look for names, titles, or speaker indicators

    Respond in EXACTLY this format:
    Q_SPEAKER: [name or "None"]
    A_SPEAKER: [name or "None"]

    Do not include any other text in your response."""

    logger.debug(prompt)
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    tool_schema = {
        "type": "object",
        "properties": {
            "Q_SPEAKER": {"type": "string"},
            "A_SPEAKER": {"type": "string"},
        },
        "required": ["Q_SPEAKER", "A_SPEAKER"],
    }

    return generate_structured_output(
        bedrock_client=bedrock_client,
        messages=messages,
        tool_schema=tool_schema,
        tool_schema_name="detect_speaker",
        description="Tool for generating structured speaker identification",
        model_id=CONFIG.model_path,
        obj=Conversation,
        max_tokens=CONFIG.max_tokens,
        print_usage = print_usage
    )


def generate_sentence(
    bedrock_client, CONFIG, question: str, answer: str, context: List[str], print_usage: bool
):
    """Generate a concise third-person sentence from a Q-A pair.

    Args:
        model: The LLM model instance.
        question: The question text.
        answer: The answer text.
        context: List of previous sentences for context.

    Returns:
        Sentence: Structured output containing the generated sentence.
    """
    prompt = f"""Generate a JSON object with "sentence": a concise, third-person sentence based ONLY on the (Question) and (Answer), including facts, numbers, dates, money amounts, and exhibit numbers from the (Question) or (Answer). Use (Context) ONLY for pronoun resolution. For documents, use the exhibit number from (Question), (Answer), or the latest exhibit in the (Context).
    Context (for reference ONLY): {''.join(context)}
    (Question): {question}
    (Answer): {answer}
    Generate the sentence.
    """


    logger.debug(prompt)
    messages = [{"role": "user", "content": [{"text": prompt}]}]
    tool_schema = {
        "type": "object",
        "properties": {"sentence": {"type": "string"}},
        "required": ["sentence"],
    }
    return generate_structured_output(
        bedrock_client=bedrock_client,
        messages=messages,
        tool_schema=tool_schema,
        tool_schema_name="generate_sentence",
        description="Tool for generating a 3rd person narrative sentence out of Q&A pairs",
        model_id=CONFIG.model_path,
        obj=Sentence,
        max_tokens=CONFIG.max_tokens,
        print_usage = print_usage
    )
