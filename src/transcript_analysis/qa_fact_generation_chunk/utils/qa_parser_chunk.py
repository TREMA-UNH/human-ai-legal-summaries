
import logging
from typing import Dict, List, Tuple
import json

from transcript_analysis.models.pymodels import Conversation, Fact, SentenceList
from transcript_analysis.qa_fact_generation.utils.llm import generate_speakers
from transcript_analysis.qa_fact_generation.utils.QA_extractor import extract_qa_pairs
from transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file
from transcript_analysis.qa_fact_generation.utils.conversation_utils import update_conversation
from transcript_analysis.qa_fact_generation.utils.speaker_detection import NER_for_speaker_detection
from transcript_analysis.qa_fact_generation.utils.fact_creation import (
    create_speaker_annotated_qa,
    generate_narrative_sentence,
    create_fact_object
)
from .llm_chunk import generate_sentence_for_all_pairs



logger = logging.getLogger(__name__)





def estimate_tokens(text):
    """Rough estimate: 1 token ≈ 4 characters."""
    return len(text) // 4


def chunk_pairs(pairs, chunk_size=6000):
    """Split formatted_pairs into smaller chunks based on serialized JSON length."""
    chunks = []
    current_chunk = []
    current_size = 0

    for pair in pairs:
        pair_str = json.dumps(pair)
        pair_size = len(pair_str) + 2  # Approximate buffer for comma/spacing
        if current_size + pair_size <= chunk_size:
            current_chunk.append(pair)
            current_size += pair_size
        else:
            chunks.append(current_chunk)
            current_chunk = [pair]
            current_size = pair_size

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def chunk_formatted_pairs(pairs: List[dict], chunk_size: int = 6000, overlap: int = 3) -> List[List[dict]]:
    """Split pairs into chunks based on serialized JSON length with overlap."""
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive")
    if len(pairs) <=0:
        raise ValueError("QA pairs dict is empty")
    chunks = []
    current_chunk = []
    current_size = 0
    pair_index = 0
    
    while pair_index < len(pairs):

        pair = pairs[pair_index]
        pair_str = json.dumps(pair)
        pair_size = len(pair_str) + 2  # Buffer for comma/spacing

        if pair_size > chunk_size:
            if current_chunk:
                chunks.append(current_chunk)
            chunks.append([pair])
            current_chunk = []
            current_size = 0
            pair_index += 1
            continue

        if current_size + pair_size > chunk_size and current_chunk:
            chunks.append(current_chunk)
            overlap_start = max(0, len(current_chunk) - overlap)
            current_chunk = current_chunk[overlap_start:] if overlap_start < len(current_chunk) else []
            current_size = sum(len(json.dumps(p)) + 2 for p in current_chunk)
        
        current_chunk.append(pair)
        current_size += pair_size
        pair_index += 1

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def chunk_summary_facts(facts: List[Dict[str, str]], chunk_size: int = 4000, overlap: int = 2) -> List[List[Dict[str, str]]]:
    """Chunk summary facts with overlap for accuracy evaluation."""
    
    # Convert your facts format if needed
    formatted_facts = [{"fact_id": k, "content": v} for item in facts for k, v in item.items()]
    
    return chunk_formatted_pairs(formatted_facts, chunk_size, overlap)

def process_transcript_all_pairs(
    bedrock_client,
    nlp,
    filepath: str,
    CONFIG,
    extract_qa: bool = True,
    detect_speakers: bool = True,
    prepend_speakers: bool = True,
    generate_narrative: bool = True,
    number_of_first_qa_pairs: int = 2,
    print_usage:bool = False
) -> List[Fact]:
    """
    Process transcript file to extract facts with speaker detection and narrative generation.
    
    Args:
        bedrock_client: AWS Bedrock client
        nlp: NLP model - for NER
        filepath: Path to transcript file
        CONFIG: Configuration object
        extract_qa: Whether to extract Q&A pairs
        detect_speakers: Whether to detect speakers
        prepend_speakers: Whether to prepend speakers to Q&A
        generate_narrative: Whether to generate narrative sentences
        number_of_first_qa_pairs: Number of first Q&A pairs to consider for intro context
        
    Returns:
        List of Fact objects
    """



    if not extract_qa:
        return []

    # Step 0: Read the file
    lines = read_transcript_file(filepath)

    # Step 1: Extract Q&A pairs and introductory lines
    qa_pairs, introductory_lines = extract_qa_pairs(lines)
    if not qa_pairs:
        logger.info("No Q&A pairs extracted from transcript")
        return []

    # Step 2: Process Q&A pairs for speaker detection and fact creation
    facts = []
    conversation = Conversation()
    limit_pairs = CONFIG.limit_pairs or float("inf")
    intro_context = "".join(introductory_lines).strip()

    only_once = False # only once detect the speakers

    for idx, (question, answer, current_page, question_line_number) in enumerate(qa_pairs):
        if len(facts) >= limit_pairs:
            logger.info(f"Reached limit of {limit_pairs} Fact objects, stopping")
            break

        # Initialize default values
        question_sa = question
        answer_sa = answer
        fact_conversation = None

        # Perform NER and speaker detection
        if detect_speakers and not only_once:
            only_once = CONFIG.only_A_detection
            names, full_context = NER_for_speaker_detection(
                bedrock_client, nlp, CONFIG, qa_pairs, idx, 
                question, answer, intro_context, number_of_first_qa_pairs
            )
            
            if names and full_context:
                new_conversation = generate_speakers(bedrock_client, CONFIG, full_context, print_usage)
                conversation = update_conversation(conversation, new_conversation, nlp, CONFIG)

        # Create speaker-annotated Q&A
        if detect_speakers and prepend_speakers:
            question_sa, answer_sa, fact_conversation = create_speaker_annotated_qa(
                question, answer, conversation, prepend_speakers, CONFIG
            )

        logger.info(f"Q_SA:{question_sa}\nA_SA:{answer_sa}")

        # Create fact object
        fact = create_fact_object(
            question, answer, question_sa, answer_sa, "",
            fact_conversation, current_page, question_line_number
        )
        facts.append(fact)


    if generate_narrative:
        # Format Q&A pairs
        formatted_pairs = [{f"q{i+1}": fact.question_sa, f"a_{i+1}": fact.answer_sa} for i, fact in enumerate(facts)]

        # Always chunk to stay safely under token limits
        chunks = chunk_pairs(formatted_pairs, chunk_size=5000)
        logger.info(f"{len(chunks)} chunk(s).")
        output = []

        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1} with {len(chunk)} Q&A pairs")
            # logger.info(f"chunk: {chunk}")
            result = generate_sentence_for_all_pairs(bedrock_client, CONFIG, print_usage, chunk)

            if result:
                # Extract only the 'results' from the response and extend output
                for key, sentence_list in result:
                    if key == 'results':
                        output.extend(sentence_list)
            else:
                logger.error(f"Failed to process chunk {i+1}")
                return

        logger.info(f"output: {output}")
        for i, sentenceObject in enumerate(output):
            facts[i].sentence = sentenceObject.sentence
            
        
    return facts