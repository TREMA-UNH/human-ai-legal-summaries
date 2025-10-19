import json
import logging
from typing import Dict, List

import botocore
import botocore.exceptions

from src.transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file
from src.vanilla_nuggetbased_evaluation.evaluation_pymodels import (
    DetailCoverage,
    ConsolidatedNuggetItem,
    DetailCoverageItem,
    NuggetCoverage,
    NuggetCoverageItem,

)
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import generate_structured_output
from .data_loader import NuggetLoader
from .evaluation_schemas import EvaluationSchemas
from llm_conv_segmentation.main import initialize_bedrock_model
from config import CONFIG
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class NuggetEvaluator:
    def __init__(self):
        self.bedrock_client = initialize_bedrock_model(CONFIG)
        self.config = CONFIG
        self.logger = logging.getLogger(__name__)
        self.nugget_loader = NuggetLoader()
        self.schemas = EvaluationSchemas()

    def evaluate_nuggets(
        self,
        nuggets_file: str,
        summary_path: str,
        print_usage: bool,
        output_path: str,
        max_workers: int = 4 
    ) -> Dict:
        self.logger.info("Starting nugget evaluation")

        summary = "\n".join(read_transcript_file(summary_path))
        nugget_data = self.nugget_loader.load_nuggets(nuggets_file)

        self.logger.info(nugget_data.consolidated_nuggets)
        ctc = self.evaluate_consolidated_nugget_coverage(
            nugget_data.consolidated_nuggets, summary, print_usage, max_workers
        )
        fdc = self.evaluate_detail_coverage(
            nugget_data.mapping, summary, print_usage, max_workers
        )

        result = {
            "CTC": {
                **ctc.model_dump(),
                "CTC_score": ctc.CTC_score
            },
            "FDC": fdc.model_dump(),
        }

        try:
            with open(output_path, "w") as f:
                json.dump(result, f, indent=2)
            self.logger.info(f"Saved evaluation results to {output_path}")
        except Exception as e:
            self.logger.error(f"Failed to save evaluation results: {str(e)}")
            raise

        return result

    def evaluate_consolidated_nugget_coverage(
        self,
        consolidated_nuggets: List[ConsolidatedNuggetItem],
        summary: str,
        print_usage: bool,
        max_workers: int
    ) -> NuggetCoverage:
        self.logger.info("Evaluating Consolidated Nugget Coverage (CTC)")
        
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type((botocore.exceptions.ReadTimeoutError,)),
            reraise=True
        )
        def evaluate_single_nugget(index: int, consolidated_nugget: str, consolidated_id: str) -> NuggetCoverageItem:
            prompt = (
                "Evaluate whether the consolidated nugget is covered in the summary. "
                "Return a JSON object with:\n"
                "  - \"text\": the nugget text,\n"
                "  - \"present\": 1 if the summary covers it, otherwise 0,\n"
                "  - \"explanation\": a short explanation of the score.\n"
                "Return only a JSON array of such objects. Do not include any extra text.\n\n"
                f"***NUGGETS***:\n{json.dumps(consolidated_nugget, indent=2)}\n\n***SUMMARY***:\n{summary}"
            )

            messages = [{"role": "user", "content": [{"text": prompt}]}]

            self.logger.info(f"Evaluating CTC nugget {index+1}/{len(consolidated_nuggets)}, size: {len(json.dumps(prompt))} characters")
            nci = generate_structured_output(
                bedrock_client=self.bedrock_client,
                messages=messages,
                tool_schema=self.schemas.get_nugget_coverage_schema(),
                tool_schema_name="nugget_coverage",
                description="Binary check of consolidated nugget coverage.",
                model_id=self.config.model_path,
                max_tokens=self.config.max_tokens,
                print_usage=print_usage,
                obj=NuggetCoverageItem
            )
            nci.consolidated_id = consolidated_id
            self.logger.info(f"CTC nugget {index+1} result: {nci}")
            return nci

        formatted_consolidated_nuggets = [(i, c_nugget.text, c_nugget.consolidated_id) for i, c_nugget in enumerate(consolidated_nuggets)]
        c_nuggets = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_nugget = {
                executor.submit(evaluate_single_nugget, i, nugget_text, consolidated_id): (i, nugget_text)
                for i, nugget_text, consolidated_id in formatted_consolidated_nuggets
            }
            for future in as_completed(future_to_nugget):
                i, nugget_text = future_to_nugget[future]
                try:
                    result = future.result()
                    c_nuggets.append(result)
                except Exception as e:
                    self.logger.error(f"CTC nugget {i+1} failed: {e}")
                    raise

        return NuggetCoverage(c_nuggets=c_nuggets)

    def evaluate_detail_coverage(
        self,
        mapping: Dict[str, List[Dict[str, str]]],
        summary: str,
        print_usage: bool,
        max_workers: int
    ) -> DetailCoverage:
        self.logger.info("Evaluating Fine-Grained Detail Coverage (FDC)")
        
        @retry(
            stop=stop_after_attempt(5),
            wait=wait_exponential(multiplier=1, min=4, max=60),
            retry=retry_if_exception_type((botocore.exceptions.ReadTimeoutError,)),
            reraise=True
        )
        def evaluate_mapping_chunk(consolidated_id: str, original_nuggets: List[Dict[str, str]]) -> DetailCoverage:
            print(type(original_nuggets))
            nugget_texts = [n.text for n in original_nuggets]
            prompt = (
                f"For each original nugget, assess whether it is covered in the provided summary. "
                f"Score: 2 = fully covered, 1 = partially mentioned, 0 = absent. "
                f"Return a JSON object matching this schema:\n"
                "{\n"
                "  'text': the nugget text str,\n"
                "  'score': the coverage score (integer; 0, 1, or 2)\n"
                "  'explanation': a short explanation of the score\n"
                "}\n"
                f"\n\nORIGINAL NUGGETS:\n{json.dumps(nugget_texts, indent=2)}\n\nSUMMARY:\n{summary}"
            )


            self.logger.info(f"Evaluating FDC for consolidated ID {consolidated_id}, size: {len(json.dumps(prompt))} characters")
            result = generate_structured_output(
                bedrock_client=self.bedrock_client,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                tool_schema=self.schemas.get_detail_coverage_schema(),
                tool_schema_name="detail_coverage",
                description=f"Evaluate fine-grained nugget presence for consolidated ID {consolidated_id}.",
                model_id=self.config.model_path,
                max_tokens=self.config.max_tokens,
                print_usage=print_usage,
                obj=DetailCoverage
            )

            if isinstance(result.nuggets, str):
                try:
                    result.nuggets = json.loads(result.nuggets)
                    result.nuggets = [DetailCoverageItem(**nugget) for nugget in result.nuggets]
                except json.JSONDecodeError as e:
                    self.logger.error(f"Failed to parse nuggets JSON for consolidated ID {consolidated_id}: {result.nuggets}")
                    raise ValueError(f"Invalid JSON in nuggets: {str(e)}")

            for i, nugget in enumerate(result.nuggets):
                nugget.nugget_id = original_nuggets[i].nugget_id
                nugget.consolidated_id = consolidated_id

            self.logger.info(f"FDC result for consolidated ID {consolidated_id}: {result}")
            return result

        all_nuggets = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_mapping = {
                executor.submit(evaluate_mapping_chunk, consolidated_id, original_nuggets): consolidated_id
                for consolidated_id, original_nuggets in mapping.items()
            }
            for future in as_completed(future_to_mapping):
                consolidated_id = future_to_mapping[future]
                try:
                    result = future.result()
                    all_nuggets.extend(result.nuggets)
                except Exception as e:
                    self.logger.error(f"FDC for consolidated ID {consolidated_id} failed: {e}")
                    raise

        return DetailCoverage(nuggets=all_nuggets)