import re
from typing import List, Tuple, Optional
import logging

from config import CONFIG
from transcript_analysis.qa_fact_generation.utils.conversation_utils import update_conversation
from transcript_analysis.qa_fact_generation.utils.fact_creation import create_speaker_annotated_qa
from transcript_analysis.qa_fact_generation.utils.llm import generate_speakers
from transcript_analysis.qa_fact_generation.utils.speaker_detection import NER_for_speaker_detection
from transcript_analysis.models.pymodels import Conversation
import spacy

logger = logging.getLogger(__name__)


class QAExtractor:
    """Extracts Q&A pairs from transcript lines with page and line tracking."""
    
    def __init__(self, bedrock_client = None):
        self.qa_pairs = [] #qa pairs with context - List of Q&A pairs as (question, answer, qpage, qline_number, apage, aline_number)
        self.introductory_lines = []
        self.in_intro = True
        self.current_question = []
        self.current_answer = []
        self.mode = None  # Can be 'Q' or 'A'
        self.current_page = 0
        self.question_line_number = 0
        self.question_page_number = 0  # Page where the question started
        self.bedrock_client = bedrock_client



    
    def detect_speaker_names(self, config, number_of_first_qa_pairs: int = 2, nlp="en_core_web_trf", print_usage: bool = False) -> Conversation:
        """
        Detect speaker names for a deposition using LLM-based speaker detection.
        
        Args:
            bedrock_client: The Bedrock client for LLM calls.
            config: AppConfig object with configuration settings.
            introductory_lines: List of introductory lines for context.
            qa_pairs: List of Q&A pairs for context (each tuple: question, answer, _, _).
            number_of_first_qa_pairs: Number of Q&A pairs to use for context.
            nlp: The spaCy model to use for processing.
            print_usage: Whether to print usage information.
        
        Returns:
            Conversation object containing detected speaker information (e.g., A_SPEAKER).
        """
        bedrock_client = self.bedrock_client
        introductory_lines = self.introductory_lines
        qa_pairs = self.qa_pairs

        nlp = spacy.load(nlp)
        conversation = Conversation()
        
        if config.only_A_detection:
            # Build context from intro and up to number_of_first_qa_pairs
            context_pairs = qa_pairs[:min(number_of_first_qa_pairs, len(qa_pairs))]
            intro_context = "".join(introductory_lines).strip()
            full_context = f"{intro_context}\n" + "\n".join([f"Q: {q}\nA: {a}" for q, a, _, _,_,_ in context_pairs])
            
            # Call LLM to detect speakers
            new_conversation = generate_speakers(bedrock_client, config, full_context, print_usage)
            if new_conversation:
                conversation = update_conversation(conversation, new_conversation, nlp, config)
        
        logger.debug(f"Detected conversation: {conversation}")
        logger.debug(f"A_SPEAKER: {conversation.A_SPEAKER}")
        config.conversation = conversation
        return conversation
 
    def extract_qa_pairs(self, lines: List[str]) -> Tuple[List[Tuple[str, str, int, int, int, int]], List[str]]:
        """Extract all Q&A pairs from the transcript with page and line numbers."""
        self._reset_state()
        
        for i, line in enumerate(lines, 1):
            logger.debug(line)
            
            if self._handle_page_number(line, i):
                continue
                
            self._process_line(line, i)
        
        self._flush_current_pair()
        logger.info(f"Extracted {len(self.qa_pairs)} Q/A pairs")
        logger.debug("INTRODUCTORY LINES:\n")
        logger.debug(self.introductory_lines)
        return self.qa_pairs, self.introductory_lines

    def _reset_state(self):
        """Reset the extractor state for a new extraction."""
        self.qa_pairs = []
        self.introductory_lines = []
        self.in_intro = True
        self.current_question = []
        self.current_answer = []
        self.mode = None
        self.current_page = 0
        self.question_line_number = 0
        self.question_page_number = 0
        self.answer_line_number = 0
        self.answer_page_number = 0
        
    def _handle_page_number(self, line: str, line_index: int) -> bool:
        """
        Handle page number detection and update current page.
        Returns True if line was a page number and should be skipped, False otherwise.
        """
        if not hasattr(self, 'waiting_for_page_number'):
            self.waiting_for_page_number = False
        
        page_related = False
        
        if '\f' in line:
            self.waiting_for_page_number = True
            page_related = True
            
            after_f = line.split('\f', 1)[-1]
            number_match = re.search(r'(\d+)', after_f)
            if number_match:
                try:
                    self.current_page = int(number_match.group(1))
                    self.waiting_for_page_number = False
                    logger.debug(f"Updated page number to {self.current_page} (same line as \\f)")
                except ValueError:
                    pass
        
        elif self.waiting_for_page_number:
            if re.match(r"^\s*\d+\s+(Q|A|\w)", line.strip()):
                self.waiting_for_page_number = False
                return False
            
            page_related = True
            
            number_match = re.search(r'(\d+)', line)
            if number_match:
                try:
                    self.current_page = int(number_match.group(1))
                    self.waiting_for_page_number = False
                    logger.debug(f"Updated page number to {self.current_page} (line after \\f)")
                except ValueError:
                    pass
        
        if not page_related:
            return False
        
        if self.in_intro:
            logger.debug(f"line:{line} added to INTRO")
            self.introductory_lines.append(line.strip())
        
        return True

    def _process_line(self, line: str, line_index: int):
        """Process each line for Q&A content or introductory material."""
        if self.in_intro:
            if self._is_question_line(line):
                self.in_intro = False
                self._handle_question_line(line, line_index)
            else:
                self.introductory_lines.append(line)
        elif self._is_question_line(line):
            # Only start a new question if we saw an answer or this is the first question
            if self.mode == "A" or not self.current_question:
                self._handle_question_line(line, line_index)
            else:
                # Treat this Q line as a continuation of the current question
                content = re.sub(r"^\s*\d+\s+Q\b\s*", "", line.strip())
                self.current_question.append(content)
                logger.debug(f"Appended to question at line {line_index}: {content}")
        elif self._is_answer_line(line):
            self._handle_answer_line(line, line_index)
        elif self._is_continuation_line(line):
            self._handle_continuation_line(line, line_index)

    def _is_question_line(self, line: str) -> bool:
        """Check if line starts a new question."""
        regex = r"^\s*\d+[:.\s]+\s*Q\b"
        return bool(re.match(regex, line.strip()))

    def _is_answer_line(self, line: str) -> bool:
        """Check if line starts a new answer."""
        regex = r"^\s*\d+[:.\s]+\s*A\b"
        return bool(re.match(regex, line.strip()))

    def _is_continuation_line(self, line: str) -> bool:
        """Check if line is a continuation of current Q or A."""
        return bool(re.match(r"^\s*\d+\s+", line.strip())) and not self._is_question_line(line) and not self._is_answer_line(line)

    def _handle_question_line(self, line: str, line_index: int):
        """Handle the start of a new question."""
        self.in_intro = False
        self._flush_current_pair()
        
        line_number_match = re.match(r"^\s*(\d+)", line.strip())
        if line_number_match:
            self.question_line_number = int(line_number_match.group(1))
        
        self.question_page_number = self.current_page
        
        question_content = re.sub(r"^\s*\d+\s+Q\b\s*", "", line.strip())
        self.current_question = [question_content]
        self.current_answer = []
        self.mode = "Q"
        logger.debug(f"New question at line {line_index}: {line}")
        logger.debug(f"Question starts on page {self.question_page_number}")

    def _handle_answer_line(self, line: str, line_index: int):
        """Handle the start of a new answer."""
        line_number_match = re.match(r"^\s*(\d+)", line.strip())
        if line_number_match:
            self.answer_line_number = int(line_number_match.group(1))
        
        self.answer_page_number = self.current_page

        answer_content = re.sub(r"^\s*\d+\s+A\b\s*", "", line.strip())
        self.current_answer = [answer_content]
        self.mode = "A"
        logger.debug(f"New answer at line {line_index}: {line}")

    def _handle_continuation_line(self, line: str, line_index: int):
        """Handle continuation of current question or answer."""
        content = re.sub(r"^\s*\d+\s+", "", line.strip())
        
        if self.mode == "Q":
            if content:
                self.current_question.append(content)
                logger.debug(f"Appended to question at line {line_index}: {content}")
        elif self.mode == "A":
            if content:
                self.current_answer.append(content)
                logger.debug(f"Appended to answer at line {line_index}: {content}")

    def _flush_current_pair(self):
        """Flush current Q&A pair to the results list."""
        if not self.current_question:
            return
            
        question = " ".join(self.current_question).strip()
        question = re.sub(r'\s+', ' ', question)  # Replace multiple spaces with single space
        
        answer = " ".join(self.current_answer).strip() if self.current_answer else ""
        answer = re.sub(r'\s+', ' ', answer)  # Replace multiple spaces with single space
    
        # Ensure answer page/line are set, default to question page/line if no answer found
        a_page = self.answer_page_number if hasattr(self, 'answer_page_number') and self.answer_page_number > 0 else self.question_page_number
        a_line = self.answer_line_number if hasattr(self, 'answer_line_number') and self.answer_line_number > 0 else self.question_line_number
        
        # CHANGE THIS LINE - Create 6-tuple instead of 4-tuple
        qa_pair = (question, answer, self.question_page_number, self.question_line_number, a_page, a_line)
        self.qa_pairs.append(qa_pair)
        
        
        logger.debug(f"Flushed pair: Q='{question}' (page {self.question_page_number}, line {self.question_line_number}), "
                f"A='{answer}' (page {a_page}, line {a_line})")




    def retrieve_page_line_range(self, start_page, end_page, start_line, end_line) -> str:
        """Retrieve lines from the transcript for a given page:line range."""
        try:
            # Filter lines for the specified page and line range
            matching_lines = [
                line for pg, ln, line in self.all_lines
                if start_page<= pg <=end_page and start_line <= ln <= end_line
            ]
            
            if not matching_lines:
                return f"No lines found for page range: {start_page}-{end_page}, lines: {start_line}-{end_line}."
            
            # Join the lines, preserving original formatting
            return "\n".join(matching_lines)
        
        except ValueError as e:
            return f"Error: {str(e)}"

    # def format_the_pairs(self, add_witness_name: bool = False, nlp="en_core_web_trf", number_of_first_qa_pairs: int = 2, print_usage: bool = False, annotate_answer_only: bool = True) -> List[dict]:
    #     """
    #     Format the extracted Q&A pairs into a list of dictionaries with 'q' and 'a' keys.
        
    #     Returns:
    #         List of dictionaries like: {'q': question, 'a': answer}
    #     """
    #     if add_witness_name:
    #         nlp = spacy.load(nlp)
    #         formatted_qa_pairs = []
    #         conversation = Conversation()
    #         intro_context = "".join(self.introductory_lines).strip()
    #         speakers_detected = False  # Track single detection

    #         for idx, (question, answer, _, _) in enumerate(self.qa_pairs):
    #             question_sa = question
    #             answer_sa = answer

    #             # Perform LLM-based speaker detection once if only_A_detection is True
    #             if not speakers_detected and CONFIG.only_A_detection:
    #                 # Build context from intro and up to number_of_first_qa_pairs
    #                 context_pairs = self.qa_pairs[:min(idx + number_of_first_qa_pairs, len(self.qa_pairs))]
    #                 full_context = f"{intro_context}\n" + "\n".join([f"Q: {q}\nA: {a}" for q, a, _, _ in context_pairs])
                    
    #                 # Call LLM to detect speakers
    #                 new_conversation = generate_speakers(self.bedrock_client, CONFIG, full_context, print_usage)
    #                 if new_conversation:
    #                     speakers_detected = True
    #                     conversation = update_conversation(conversation, new_conversation, nlp, CONFIG)

    #             # Annotate only the answer with speaker
    #             question_sa, answer_sa, _ = create_speaker_annotated_qa(
    #                 question, answer, conversation, prepend_speakers=True, CONFIG=CONFIG, annotate_answer_only=annotate_answer_only
    #             )

    #             logger.debug(f"Q_SA:{question_sa}\nA_SA:{answer_sa}")
    #             formatted_qa_pairs.append({"q": question_sa, "a": answer_sa})
    #         CONFIG.conversation = conversation
    #         return formatted_qa_pairs

    #     return [{"q": q, "a": a} for q, a, _, _ in self.qa_pairs]
    def format_the_pairs(self, add_witness_name: bool = False, nlp="en_core_web_trf", number_of_first_qa_pairs: int = 2, print_usage: bool = False, annotate_answer_only: bool = True) -> List[dict]:
        """
        Format the extracted Q&A pairs into a list of dictionaries with separate location info for questions and answers.
        
        Returns:
            List of dictionaries like: {
                'q': question, 'q_page': page, 'q_line': line,
                'a': answer, 'a_page': page, 'a_line': line
            }
        """
        if add_witness_name:
            nlp = spacy.load(nlp)
            formatted_qa_pairs = []
            conversation = Conversation()
            intro_context = "".join(self.introductory_lines).strip()
            speakers_detected = False  # Track single detection

            for idx, (question, answer, q_page, q_line, a_page, a_line) in enumerate(self.qa_pairs):
                question_sa = question
                answer_sa = answer

                # Perform LLM-based speaker detection once if only_A_detection is True
                if not speakers_detected and CONFIG.only_A_detection:
                    # Build context from intro and up to number_of_first_qa_pairs
                    context_pairs = self.qa_pairs[:min(idx + number_of_first_qa_pairs, len(self.qa_pairs))]
                    full_context = f"{intro_context}\n" + "\n".join([f"Q: {q}\nA: {a}" for q, a, _, _, _, _ in context_pairs])
                    
                    # Call LLM to detect speakers
                    new_conversation = generate_speakers(self.bedrock_client, CONFIG, full_context, print_usage)
                    if new_conversation:
                        speakers_detected = True
                        conversation = update_conversation(conversation, new_conversation, nlp, CONFIG)

                # Annotate only the answer with speaker
                question_sa, answer_sa, _ = create_speaker_annotated_qa(
                    question, answer, conversation, prepend_speakers=True, CONFIG=CONFIG, annotate_answer_only=annotate_answer_only
                )

                logger.debug(f"Q_SA:{question_sa}\nA_SA:{answer_sa}")
                # Include separate page and line information for questions and answers
                formatted_qa_pairs.append({
                    "q": question_sa, 
                    "q_page": q_page, 
                    "q_line": q_line,
                    "a": answer_sa, 
                    "a_page": a_page, 
                    "a_line": a_line
                })
            CONFIG.conversation = conversation
            return formatted_qa_pairs

        # For the non-speaker-annotated case, also include separate page and line info
        return [{
            "q": q, 
            "q_page": q_page, 
            "q_line": q_line,
            "a": a, 
            "a_page": a_page, 
            "a_line": a_line
        } for q, a, q_page, q_line, a_page, a_line in self.qa_pairs]


def extract_qa_pairs(lines: List[str]) -> Tuple[List[Tuple[str, str, int, int, int, int]], List[str]]:
    """
    Extract all Q&A pairs from the transcript with page and line numbers.
    
    Args:
        lines: List of transcript lines to process
        
    Returns:
        Tuple containing:
        - List of Q&A pairs as (question, answer, page, line_number)
        - List of introductory lines before first Q&A pair
    """
    extractor = QAExtractor()
    qa_pairs_with_context, intro_lines =  extractor.extract_qa_pairs(lines)
    return qa_pairs_with_context, intro_lines