import argparse
import json
from typing import List, Dict

from llm_conv_segmentation.main import initialize_bedrock_model
from .llm import consolidate_nuggets, generate_nuggets_for_a_chunk, generate_nuggets_for_all_chunks
from transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file, create_facts_from_qa_pairs
from transcript_analysis.qa_fact_generation.utils.QA_extractor import QAExtractor
from llm_conv_segmentation.segmenter import create_qa_pairs, chunk_formatted_pairs
from config import CONFIG
from concurrent.futures import ThreadPoolExecutor, as_completed

import logging

logging_config = logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DepositionNuggetGenerator:
    bedrock_client = initialize_bedrock_model(CONFIG)
    CONFIG = CONFIG
    add_witness_name: bool = True

    def __init__(self, input_path: str, output_path: str, chunk_size: int = 5000, overlap: int = 5, print_usage:bool = False, mode:str = "mapping"):
        self.input_path = input_path
        self.output_path = output_path
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.print_usage = print_usage
        self.mode = mode
        self.logger = logging.getLogger(__name__)

    def chunk_the_deposition(self) -> List[List[Dict]]:
        lines = read_transcript_file(self.input_path)
        extractor = QAExtractor(self.bedrock_client)
        extractor.extract_qa_pairs(lines)
        formatted_pairs = extractor.format_the_pairs(add_witness_name=self.add_witness_name)
        logger.info(f"formatted pairs example: {formatted_pairs[:2]}")
        chunks = chunk_formatted_pairs(formatted_pairs, chunk_size=self.chunk_size, overlap=self.overlap)
        return chunks

    def generate_nuggets(self) -> Dict:
        chunks = self.chunk_the_deposition()
        self.all_nuggets = generate_nuggets_for_all_chunks(chunks, self.mode, self.bedrock_client, self.CONFIG, self.print_usage)
        return self.all_nuggets

    def hierarchical_nuggets(self) -> Dict:
        result = consolidate_nuggets(self.bedrock_client, self.CONFIG, self.print_usage, self.all_nuggets)
        return result

    def run(self):
        nuggets = self.generate_nuggets()
        with open(self.output_path, 'w') as f:
            json.dump(nuggets, f, indent=2)
        self.logger.info(f"Nuggets written to {self.output_path}")
        if self.mode == "consolidated":
            hierarchical_nuggets = self.hierarchical_nuggets()
            with open(f"{self.output_path.replace('.json','_hierarchical.json')}", 'w') as f:
                json.dump(hierarchical_nuggets, f, indent=2)
            self.logger.info(f"Nuggets written to hierarchical_{self.output_path}")


