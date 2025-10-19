from typing import List
import spacy
import logging

logger = logging.getLogger(__name__)


def extract_names(nlp, text: str) -> List[str]:
    """Extract person names from a sentence using spaCy's NER.

    Args:
        nlp: The spaCy NLP model.
        text: The input text to process.

    Returns:
        List[str]: List of extracted person names.
    """

    doc = nlp(text)
    names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    logger.debug(f"\n\nExtracting names from '{text}'\n")
    return names
