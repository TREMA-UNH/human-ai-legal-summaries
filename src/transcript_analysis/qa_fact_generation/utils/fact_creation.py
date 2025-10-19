
# fact_creation.py
import logging
from typing import List, Optional, Tuple
from transcript_analysis.models.pymodels import Fact, Conversation
from .llm import generate_sentence

logger = logging.getLogger(__name__)


def create_speaker_annotated_qa(
    question: str, 
    answer: str, 
    conversation: Conversation, 
    prepend_speakers: bool,
    CONFIG,
    annotate_answer_only: bool
) -> Tuple[str, str, Optional[Conversation]]:
    """
    Create speaker-annotated Q&A strings.
    
    Returns:
        Tuple of (question_sa, answer_sa, fact_conversation)
    """
    if prepend_speakers:
        q_speaker = conversation.Q_SPEAKER or "Q"
        a_speaker = conversation.A_SPEAKER or "A"
        question_sa = f"{q_speaker}: {question}" if not CONFIG.only_A_detection else f"Q: {question}"
        answer_sa = f"{a_speaker}: {answer}"
        fact_conversation = Conversation(Q_SPEAKER=q_speaker, A_SPEAKER=a_speaker)
        if annotate_answer_only:
            return question, answer_sa, fact_conversation
    else:
        question_sa = question
        answer_sa = answer
        fact_conversation = None
    
    return question_sa, answer_sa, fact_conversation


def generate_narrative_sentence(
    bedrock_client,
    CONFIG,
    question: str,
    answer: str,
    question_sa: str,
    answer_sa: str,
    context: List[str],
    generate_narrative: bool,
    prepend_speakers: bool,
    print_usage:bool
) -> Optional[str]:
    """
    Generate narrative sentence if required.
    
    Returns:
        Generated sentence or None
    """
    if not generate_narrative:
        return None
    
    sentence = (
        generate_sentence(
            bedrock_client, CONFIG, question_sa, answer_sa, context, print_usage
        ).sentence
        if prepend_speakers
        else generate_sentence(
            bedrock_client, CONFIG, question, answer, context, print_usage
        ).sentence
    )
    
    context.append(sentence)
    if len(context) > CONFIG.context_length:
        context.pop(0)
    
    return sentence


def create_fact_object(
    question: str,
    answer: str,
    question_sa: str,
    answer_sa: str,
    sentence: Optional[str],
    fact_conversation: Optional[Conversation],
    current_page: int,
    question_line_number: int
) -> Fact:
    """Create a Fact object with all required fields."""
    fact = Fact(
        question=question,
        answer=answer,
        question_sa=question_sa,
        answer_sa=answer_sa,
        sentence=sentence,
        conversation=fact_conversation,
        page_number=current_page,
        line_number=question_line_number,
    )
    
    logger.debug(
        f"Created Fact: A='{answer_sa}', Sentence='{sentence}', Page={current_page}, Line={question_line_number}"
    )
    
    return fact
