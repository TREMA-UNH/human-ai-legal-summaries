import logging
from typing import List, Tuple
from transcript_analysis.models.pymodels import Conversation
from transcript_analysis.qa_fact_generation.utils.ner import extract_names

logger = logging.getLogger(__name__)

def update_conversation(previous_conversation: Conversation, new_conversation: Conversation, nlp, config) -> Conversation:
    """
    Update conversation speakers if new valid speakers are detected.
    
    Args:
        previous_conversation: Current conversation object
        new_conversation: New conversation object with potential speaker updates
        nlp: NLP model for name extraction
        config: Configuration object with speaker update settings
        
    Returns:
        Updated conversation object
    """
    
    # Check if new conversation has valid speakers and differs from previous
    if not _has_valid_speakers(new_conversation, previous_conversation):
        return previous_conversation
    
    print(new_conversation)
    
    # Extract names from both speakers
    q_names = extract_names(nlp, new_conversation.Q_SPEAKER)
    a_names = extract_names(nlp, new_conversation.A_SPEAKER)
    
    logger.info(f"Q speaker names: {q_names}\nA speaker names: {a_names}")
    
    if not (q_names and a_names):
        return previous_conversation
    
    # Handle speaker updates based on configuration
    if not config.fix_a:
        # Both speakers can be updated
        logger.info(f"Updated conversation: Q={new_conversation.Q_SPEAKER}, A={new_conversation.A_SPEAKER}")
        return new_conversation
    
    # A_SPEAKER is fixed - only update if previous A_SPEAKER is empty
    if not previous_conversation.A_SPEAKER:
        logger.info(f"Updated conversation: Q={new_conversation.Q_SPEAKER}, A={new_conversation.A_SPEAKER}")
        return new_conversation
    
    # Keep previous A_SPEAKER, update only Q_SPEAKER
    updated_conversation = Conversation(
        Q_SPEAKER=new_conversation.Q_SPEAKER, 
        A_SPEAKER=previous_conversation.A_SPEAKER
    )
    logger.info(f"Updated conversation (Q only): Q={updated_conversation.Q_SPEAKER}, A={updated_conversation.A_SPEAKER}")
    return updated_conversation


def _has_valid_speakers(new_conversation: Conversation, previous_conversation: Conversation) -> bool:
    """Check if new conversation has valid speakers that differ from previous."""
    q_speaker = new_conversation.Q_SPEAKER
    a_speaker = new_conversation.A_SPEAKER
    
    # Check if speakers exist and are not empty/None
    if not q_speaker or not a_speaker or q_speaker == "None" or a_speaker == "None":
        return False
    
    # Check if speakers differ from previous conversation
    return (previous_conversation.Q_SPEAKER != q_speaker or 
            previous_conversation.A_SPEAKER != a_speaker)


def clean_context(qa_pairs: List[Tuple[str, str]]) -> str:
    """Clean and join Q&A pairs into a single string."""
    cleaned = []
    for question, answer in qa_pairs:
        if question:
            cleaned.append(question)
        if answer:
            cleaned.append(answer)
    return " ".join(cleaned).replace("  ", " ")

