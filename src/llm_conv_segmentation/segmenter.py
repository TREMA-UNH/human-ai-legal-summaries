import gzip
import json
import logging
from typing import Optional, List, Dict, Tuple, Set

from transcript_analysis.models.pymodels import Fact, FactAnnotation, FactAnnotationList, AnnotatedFact
from transcript_analysis.qa_fact_generation.utils.file_utils import read_facts
from transcript_analysis.qa_fact_generation_chunk.utils.qa_parser_chunk import chunk_formatted_pairs
from .llm import generate_segments_for_all_pairs

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SegmentIdMapper:
    """Handles mapping of local segment IDs to global segment IDs across chunks."""
    
    def __init__(self):
        self.global_segment_id = 1
        self.segment_id_map = {}
        self.previous_pairs_and_annotations = []
    
    def map_chunk_segment_ids(self, chunk: List[Dict], annotations: List[FactAnnotation], 
                             chunk_index: int, overlap: int) -> List[FactAnnotation]:
        """Map local segment IDs to global IDs for a chunk."""
        local_segment_ids = [ann.segment_id for ann in annotations]
        logger.debug(f"Chunk {chunk_index + 1} local segment_ids: {local_segment_ids}")
        
        local_to_global = {}
        mapped_pairs = set()
        
        # Handle overlap pairs first
        if chunk_index > 0:
            self._handle_overlap_pairs(chunk, annotations, local_segment_ids, 
                                     local_to_global, mapped_pairs, chunk_index, overlap)
        
        # Handle non-overlap pairs
        self._handle_non_overlap_pairs(chunk, annotations, local_segment_ids, 
                                     local_to_global, mapped_pairs, chunk_index)
        
        # Apply global segment IDs
        self._apply_global_segment_ids(annotations, local_segment_ids, local_to_global, chunk_index)
        
        # Update internal state
        self._update_state(chunk, annotations, local_segment_ids)
        
        return annotations
    
    def _handle_overlap_pairs(self, chunk: List[Dict], annotations: List[FactAnnotation],
                            local_segment_ids: List[int], local_to_global: Dict[int, int],
                            mapped_pairs: Set[int], chunk_index: int, overlap: int):
        """Handle segment ID mapping for overlapping pairs."""
        if not self.previous_pairs_and_annotations:
            return
            
        overlap_pairs = chunk[:min(overlap, len(chunk))]
        overlap_annotations = annotations[:min(overlap, len(annotations))]
        
        logger.debug(f"Overlap pairs: {overlap_pairs}")
        
        for j, (pair, ann) in enumerate(zip(overlap_pairs, overlap_annotations)):
            local_id = local_segment_ids[j]
            
            # Try to find matching pair in previous chunk
            for prev_pair, prev_ann in self.previous_pairs_and_annotations[-overlap:]:
                if self._pairs_match(pair, prev_pair):
                    global_id = self.segment_id_map.get(prev_ann.segment_id, self.global_segment_id)
                    local_to_global[local_id] = global_id
                    mapped_pairs.add(j)
                    logger.debug(f"Overlap match in chunk {chunk_index + 1}, pair {j + 1}: "
                              f"local_id {local_id} -> global_id {global_id}")
                    break
            else:
                # No match found
                if j not in mapped_pairs:
                    local_to_global[local_id] = self.global_segment_id
                    self.global_segment_id += 1
                    mapped_pairs.add(j)
                    logger.debug(f"No overlap match for local_id {local_id} in chunk {chunk_index + 1}, "
                              f"pair {j + 1}, assigned global_id {local_to_global[local_id]}")
    
    def _handle_non_overlap_pairs(self, chunk: List[Dict], annotations: List[FactAnnotation],
                                local_segment_ids: List[int], local_to_global: Dict[int, int],
                                mapped_pairs: Set[int], chunk_index: int):
        """Handle segment ID mapping for non-overlapping pairs."""
        for j, (pair, ann) in enumerate(zip(chunk, annotations)):
            if j not in mapped_pairs:
                local_id = local_segment_ids[j]
                if local_id not in local_to_global:
                    local_to_global[local_id] = self.global_segment_id
                    self.global_segment_id += 1
                    logger.debug(f"Non-overlap pair in chunk {chunk_index + 1}, pair {j + 1}: "
                              f"local_id {local_id} -> global_id {local_to_global[local_id]}")
                mapped_pairs.add(j)
    
    def _apply_global_segment_ids(self, annotations: List[FactAnnotation], 
                              local_segment_ids: List[int], 
                              local_to_global: Dict[int, int],
                              chunk_index: int):
        """Apply the mapped global segment IDs to annotations."""
        for j, annotation in enumerate(annotations):
            local_id = local_segment_ids[j]
            try:
                annotation.segment_id = local_to_global[local_id]
            except KeyError:
                logger.error(
                    f"Chunk {chunk_index + 1}, pair {j + 1}: local_id {local_id} not found in local_to_global mapping."
                    f" Assigning fallback global_segment_id = -1."
                )
                annotation.segment_id = -1  # or self.global_segment_id

    
    def _update_state(self, chunk: List[Dict], annotations: List[FactAnnotation], 
                     local_segment_ids: List[int]):
        """Update internal state for next chunk processing."""
        self.previous_pairs_and_annotations = list(zip(chunk, annotations))
        self.segment_id_map = {
            local_segment_ids[j]: annotations[j].segment_id 
            for j in range(len(annotations))
        }
    
    @staticmethod
    def _pairs_match(pair1: Dict, pair2: Dict) -> bool:
        """Check if two Q&A pairs match."""
        return (pair1['question'] == pair2['question'] and 
                pair1['answer'] == pair2['answer'])


class ChunkProcessor:
    """Handles processing of individual chunks."""
    
    def __init__(self, bedrock_client, config, print_usage: bool):
        self.bedrock_client = bedrock_client
        self.config = config
        self.print_usage = print_usage
        self.segment_mapper = SegmentIdMapper()
    
    def process_chunk(self, chunk: List[Dict], chunk_index: int, overlap: int) -> Optional[List[FactAnnotation]]:
        """Process a single chunk and return annotations."""
        logger.info(f"Processing chunk {chunk_index + 1} with {len(chunk)} Q&A pairs")
        
        result = generate_segments_for_all_pairs(
            self.bedrock_client,
            self.config,
            self.print_usage,
            chunk
        )
        
        if not result or not hasattr(result, "fact_annotations"):
            logger.error(f"Failed to process chunk {chunk_index + 1}. Result: {result}")
            return None
        
        annotations = result.fact_annotations
        logger.info(f"Chunk {chunk_index + 1} produced {len(annotations)} annotations for {len(chunk)} pairs")
        logger.debug(f"Annotations for chunk {chunk_index + 1}: {[ann.model_dump() for ann in annotations]}")
        
        # Map segment IDs
        self.segment_mapper.map_chunk_segment_ids(chunk, annotations, chunk_index, overlap)
        
        return annotations
    
    def filter_overlapping_annotations(self, annotations: List[FactAnnotation], 
                                     chunk_index: int, overlap: int, 
                                     previous_chunk_size: int) -> List[FactAnnotation]:
        """Filter out overlapping annotations from processed chunk."""
        if chunk_index == 0:
            return annotations
        
        overlap_start = min(overlap, previous_chunk_size)
        filtered_annotations = annotations[overlap_start:]
        
        logger.info(f"Chunk {chunk_index + 1}: Kept {len(filtered_annotations)} non-overlapping annotations, "
                   f"discarded {overlap_start} overlap annotations")
        
        return filtered_annotations


class AnnotationValidator:
    """Handles validation and logging of annotation results."""
    
    @staticmethod
    def validate_annotations(facts: List[Fact], annotations: List[FactAnnotation]) -> bool:
        """Validate that annotations match facts and log results."""
        logger.debug(f"Total annotations: {len(annotations)}, Total facts: {len(facts)}")
        
        # In the processing logic, add validation:
        if len(annotations) != len(facts):
            logger.warning(f"LLM returned {len(annotations)} annotations for {len(facts)} pairs. "
                        f"This will be handled by truncating/padding.")
            
            if len(annotations) > len(facts):
                # Truncate excess annotations
                annotations = annotations[:len(facts)]
                logger.info(f"Truncated to {len(annotations)} annotations")
            else:
                # Pad with default annotations
                for i in range(len(annotations), len(facts)):
                    default_ann = FactAnnotation(segment_id=-1, confidence=0.5)
                    annotations.append(default_ann)
                logger.info(f"Padded to {len(annotations)} annotations")
        
        logger.debug(f"Global segment_ids in output: {[ann.segment_id for ann in annotations]}")
        return True
    
    @staticmethod
    def _log_annotation_details(annotations: List[FactAnnotation]):
        """Log detailed annotation information for debugging."""
        logger.debug(f"Global segment_ids in output: {[ann.segment_id for ann in annotations]}")
        logger.debug(f"Output annotations: {[ann.model_dump() for ann in annotations]}")


def create_qa_pairs(facts: List[Fact]) -> List[Dict]:
    """Convert facts to Q&A pairs format."""
    return [{"question": fact.question_sa, "answer": fact.answer_sa} for fact in facts]


def create_annotated_facts(facts: List[Fact], annotations: List[FactAnnotation]) -> List[AnnotatedFact]:
    """Create annotated facts, handling mismatches gracefully."""
    annotated_facts = []
    
    for i, fact in enumerate(facts):
        if i < len(annotations):
            annotated_facts.append(AnnotatedFact(fact=fact, annotation=annotations[i]))
        else:
            logger.warning(f"No annotation for fact {i + 1}, using default annotation")
            default_annotation = FactAnnotation(segment_id=0, confidence=0.0)
            annotated_facts.append(AnnotatedFact(fact=fact, annotation=default_annotation))
    
    return annotated_facts


def save_annotated_facts(annotated_facts: List[AnnotatedFact], output_path: str):
    """Save annotated facts to compressed JSON file."""
    with gzip.open(output_path, "wt", encoding="utf-8") as f:
        for annotated_fact in annotated_facts:
            json.dump(annotated_fact.model_dump(), f)
            f.write("\n")
    
    logger.info(f"Saved {len(annotated_facts)} annotated facts to {output_path}")


def annotate_facts(input_path: str, output_path: str, bedrock_client, CONFIG, 
                  print_usage: bool, chunk_size: int = 6000, overlap: int = 5):
    """
    Main function to annotate facts with segment information.
    
    Args:
        input_path: Path to input facts file
        output_path: Path to output annotated facts file
        bedrock_client: Bedrock client for LLM calls
        CONFIG: Configuration object
        print_usage: Whether to print usage statistics
        chunk_size: Size of chunks for processing
        overlap: Number of overlapping pairs between chunks
    """
    # Load and prepare data
    facts = read_facts(input_path)
    logger.info(f"Loaded {len(facts)} facts.")
    
    pairs = create_qa_pairs(facts)
    chunks = chunk_formatted_pairs(pairs, chunk_size=chunk_size, overlap=overlap)
    logger.debug(f"Created {len(chunks)} chunk(s) with {overlap} overlap.")
    logger.debug(f"Examples: {chunks[:3]}")
    
    # Process chunks
    processor = ChunkProcessor(bedrock_client, CONFIG, print_usage)
    all_annotations = []
    previous_chunk_size = 0
    
    for i, chunk in enumerate(chunks):
        annotations = processor.process_chunk(chunk, i, overlap)
        if annotations is None:
            return  # Error occurred during processing
        
        # Filter overlapping annotations
        filtered_annotations = processor.filter_overlapping_annotations(
            annotations, i, overlap, previous_chunk_size
        )
        all_annotations.extend(filtered_annotations)
        previous_chunk_size = len(chunk)
    
    # Validate and create final output
    AnnotationValidator.validate_annotations(facts, all_annotations)
    annotated_facts = create_annotated_facts(facts, all_annotations)
    save_annotated_facts(annotated_facts, output_path)