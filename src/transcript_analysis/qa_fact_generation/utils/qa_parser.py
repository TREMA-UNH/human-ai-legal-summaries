
import logging
from typing import List, Tuple
from transcript_analysis.models.pymodels import Conversation, Fact
from utils.llm import generate_speakers
from utils.QA_extractor import extract_qa_pairs
from .file_utils import read_transcript_file
from .conversation_utils import update_conversation
from .speaker_detection import NER_for_speaker_detection
from .fact_creation import (
    create_speaker_annotated_qa,
    generate_narrative_sentence,
    create_fact_object
)

logger = logging.getLogger(__name__)


def process_transcript(
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
    context = []
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
        # Generate narrative sentence
        if generate_narrative:
            try:
                sentence = generate_narrative_sentence(
                    bedrock_client, CONFIG, question, answer, question_sa, answer_sa,
                    context, generate_narrative, prepend_speakers, print_usage
                )
            except:
                logger.info("*************************** generate sentence failed ***************************")
                sentence = f"{question_sa}\n{answer_sa}"

        logger.info(f"SENTENCE:{sentence}")
        
        if generate_narrative and detect_speakers:
            # Create fact object
            fact = create_fact_object(
                question, answer, question_sa, answer_sa, sentence,
                fact_conversation, current_page, question_line_number
            )
            facts.append(fact)

            logger.info(f"Processed Fact {len(facts)}")

        else:
            # Create fact object
            fact = create_fact_object(
                question, answer, "", "", "",
                Conversation(), current_page, question_line_number
            )
            facts.append(fact)

            logger.info(f"Processed Fact {len(facts)}")
    return facts