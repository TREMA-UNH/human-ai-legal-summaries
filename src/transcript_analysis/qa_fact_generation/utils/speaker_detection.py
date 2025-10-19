
# speaker_detection.py
import logging
from typing import List, Tuple
from .ner import extract_names
from .llm import generate_speakers
from .conversation_utils import clean_context

logger = logging.getLogger(__name__)


def build_surrounding_context(
    qa_pairs: List[Tuple], 
    idx: int, 
    CONFIG, 
    intro_context: str, 
    nlp, 
    number_of_first_qa_pairs: int
) -> str:
    """
    Build surrounding context for speaker detection.
    
    Args:
        qa_pairs: List of Q&A pairs
        idx: Current index
        CONFIG: General Configuration
        intro_context: Introductory context of the deposition
        nlp: NLP model for NER task
        number_of_first_qa_pairs: Number of first Q&A pairs to limit considered pairs for speaker detection
        
    Returns:
        Full context string for speaker detection
    """
    # Use surrounding Q&A pairs as context
    start = max(0, idx - CONFIG.window_length_for_ner)
    end = min(len(qa_pairs), idx + CONFIG.window_length_for_ner + 1)

    # Determine number of intro sentences to include based on window length
    num_intro_sentences = (
        CONFIG.window_length_for_ner
        if idx < CONFIG.window_length_for_ner
        else None
    )
    
    if idx <= number_of_first_qa_pairs:
        # Split intro_context into sentences using nlp
        doc = nlp(intro_context)
        sentences = [
            sent.text.strip() for sent in doc.sents if sent.text.strip()
        ]
        if sentences:
            # Select last N sentences where N = window_length_for_ner for early pairs
            if num_intro_sentences is not None:
                selected_sentences = sentences[-num_intro_sentences:]
            else:
                selected_sentences = sentences
            # Create pseudo-Q&A pairs for each sentence
            intro_pairs = [(sent, "") for sent in selected_sentences]
            surrounding_pairs = intro_pairs + [
                (f"\nQ: {q}", f"A: {a}") for q, a, _, _ in qa_pairs[start:end]
            ]
            logger.debug(
                f"Included {len(intro_pairs)} intro sentences in surrounding_pairs for pair {idx+1}: {selected_sentences}"
            )
        else:
            surrounding_pairs = [(intro_context, "")]  + [
                (f"\nQ: {q}", f"A: {a}") for q, a, _, _ in qa_pairs[start:end]
            ]
            logger.debug(
                f"No sentences detected in intro_context, using full intro for pair {idx+1}: {intro_context}"
            )
    else:
        surrounding_pairs = [(f"\nQ: {q}", f"A: {a}") for q, a, _, _ in qa_pairs[start:end]]
    
    logger.debug(f"surrounding pairs: {surrounding_pairs}")
    full_context = clean_context(surrounding_pairs)
    return full_context


def NER_for_speaker_detection(
    bedrock_client,
    nlp,
    CONFIG,
    qa_pairs: List[Tuple],
    idx: int,
    question: str,
    answer: str,
    intro_context: str,
    number_of_first_qa_pairs: int
) -> Tuple[List[str], str]:
    """
    Detect speakers for a Q&A pair using NER and context.
    
    Returns:
        Tuple of (names_found, full_context_used)
    """
    ner_context = f"{question} {answer}"
    names = extract_names(nlp, ner_context)
    logger.debug(f"NER on Q&A pair {idx+1}: names={names}")
    
    full_context = ""
    if names:
        logger.debug(
            f"Names detected in Q&A pair {idx+1} (within first {number_of_first_qa_pairs}), enabling intro context"
        )
        
        full_context = build_surrounding_context(
            qa_pairs, idx, CONFIG, intro_context, nlp, number_of_first_qa_pairs
        )
        logger.debug(
            f"Detecting speakers for pair {idx+1} with context: \n{full_context}\n"
        )
    
    return names, full_context

