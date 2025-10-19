from typing import List, Tuple, Any
from transcript_analysis.models.pymodels import Conversation
import spacy
import logging

from transcript_analysis.qa_fact_generation.utils.conversation_utils import update_conversation
from transcript_analysis.qa_fact_generation.utils.llm import generate_speakers

logger = logging.getLogger(__name__)
