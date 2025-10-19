import logging
from typing import Dict, List
import json 
import gzip
from transcript_analysis.qa_fact_generation.utils.fact_creation import create_fact_object
from transcript_analysis.models.pymodels import Conversation, Fact


logger = logging.getLogger(__name__)


def inspect_replacements(file_path: str) -> str:
    """
    Inspect and handle Unicode replacement characters in a file.
    
    Args:
        file_path: Path to the file to inspect
        
    Returns:
        Decoded text with replacements handled
    """
    # Read file in binary mode to get raw bytes
    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    # Read file with errors="replace" to get decoded text
    with open(file_path, encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Find positions where replacement characters (U+FFFD) appear
    replacement_char = "\uFFFD"
    replacements = []

    for i, char in enumerate(text):
        if char == replacement_char:
            # Map the text position to the byte position
            # This assumes one byte per character before the replacement, which may need adjustment
            byte_pos = i  # Approximate, refine based on actual byte-to-char mapping
            if byte_pos < len(raw_bytes):
                bad_byte = raw_bytes[byte_pos:byte_pos+1]
                replacements.append((byte_pos, bad_byte))

    # Log the replacements
    if replacements:
        logger.info("Found %d replacements in file: %s", len(replacements), file_path)
        for pos, bad_byte in replacements:
            logger.info("Replaced byte 0x%s at position %d with U+FFFD", bad_byte.hex(), pos)
    else:
        logger.info("No replacements found in file: %s", file_path)

    return text  # Return the decoded text for further processing


def read_transcript_file(filepath: str) -> List[str]:
    """
    Read transcript file with Unicode error handling.
    
    Args:
        filepath: Path to the transcript file
        
    Returns:
        List of lines from the file
    """
    # try:
    logger.info("reading lines")
    with open(filepath, 'r', encoding='utf-8', newline='', errors="ignore") as f:
        lines = f.readlines()
    return lines
    # except UnicodeDecodeError:
    #     logger.info("UnicodeDecodeError-reading the lines with replacement")
        # return None
        # decoded_text = inspect_replacements(filepath)
        # return decoded_text.splitlines()






def read_facts(input_file_path):
    facts = []
    with gzip.open(input_file_path, "rt", encoding="utf-8") as f:
        for line in f:
            facts.append(Fact(**json.loads(line)))
    return facts



def create_facts_from_qa_pairs(qa_pairs: List[Dict], introductory_lines: list[str], CONFIG  ):
    # Step 2: Process Q&A pairs for speaker detection and fact creation
    facts = []
    limit_pairs = CONFIG.limit_pairs or float("inf")

    only_once = False # only once detect the speakers

    for idx, (question, answer, current_page, question_line_number) in enumerate(qa_pairs):
        if len(facts) >= limit_pairs:
            logger.info(f"Reached limit of {limit_pairs} Fact objects, stopping")
            break

        # Initialize default values
        question_sa = None
        answer_sa = None
        fact_conversation = None

        # Create fact object
        fact = create_fact_object(
            question, answer, question_sa, answer_sa, "",
            fact_conversation, current_page, question_line_number
        )
        facts.append(fact)