# Standard Library Imports
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Local Application Imports
from config import CONFIG
from llm_conv_segmentation.main import initialize_bedrock_model

# Project-Specific Imports
from transcript_analysis.qa_fact_generation.utils.file_utils import read_transcript_file
from transcript_analysis.qa_fact_generation.utils.token_manager import TokenManager
from vanilla_nuggetbased_evaluation.evaluation_pymodels import ConsolidatedNuggetItem
from vanilla_nuggetbased_evaluation.evaluation_criteria.accuracy_evaluator import evaluate_accuracy
from vanilla_nuggetbased_evaluation.evaluation_criteria.clarity_evaluator import evaluate_clarity
from vanilla_nuggetbased_evaluation.evaluation_criteria.completeness_evaluator import evaluate_completeness
from vanilla_nuggetbased_evaluation.evaluation_criteria.structure_evaluator import evaluate_structure
from vanilla_nuggetbased_evaluation.utils.reporting import save_evaluation_results
from vanilla_nuggetbased_evaluation.data_loader import NuggetLoader
from vanilla_nuggetbased_evaluation.evaluation_schemas import EvaluationSchemas
from transcript_analysis.models.pymodels import Conversation
from transcript_analysis.qa_fact_generation.utils.QA_extractor import QAExtractor
from vanilla_nuggetbased_evaluation.evaluation_criteria.citation_evaluator import calculate_citation_score, evaluate_citations


def collect_evaluation_results(
    futures: Dict[str, Any],
    logger: logging.Logger,
) -> Dict[str, Dict[str, Any]]:
    """
    Collect evaluation results from futures, handling errors.
    """
    results = {}
    for criterion, future in futures.items():
        try:
            result = future.result()
            
            # Special handling for citation_analysis
            if criterion == "citation_analysis":
                if isinstance(result, list):
                    # Convert list to expected format
                    citation_score = calculate_citation_score(result) if result else 0.0
                    results[criterion] = {
                        "score": citation_score,
                        "explanation": f"Analyzed {len(result)} citations",
                        "details": result
                    }
                    continue  # Add this continue to skip the standard handling below
            
            # Standard handling for other criteria
            if not isinstance(result, dict) or "score" not in result:
                error_message = f"Invalid result format for {criterion}"
                logger.error(error_message)
                results[criterion] = {"score": 0.0, "explanation": error_message}
                continue
                
            results[criterion] = result
        
        except Exception as e:
            error_message = f"Error processing {criterion}: {str(e)}"
            logger.error(error_message)
            results[criterion] = {"score": 0.0, "explanation": error_message}
    
    return results

class EnhancedSummaryEvaluator:
    """
    Evaluates summaries based on nuggets and predefined criteria.

    Evaluation Criteria:
    - Completeness: Are top 3-5 most important nuggets present?
    - Accuracy: Are nuggets correctly represented without distortion?
    - Structure: Is the summary well-organized with logical flow?
    - Clarity: Are terms and acronyms clearly defined?
    """

    def __init__(self, max_prompt_tokens: int = 4000):
        self.bedrock_client = initialize_bedrock_model(CONFIG)
        self.config = CONFIG
        self.logger = logging.getLogger(__name__)
        self.nugget_loader = NuggetLoader()
        self.schemas = EvaluationSchemas()
        self.max_prompt_tokens = max_prompt_tokens
        self.token_manager = TokenManager()

    def evaluate_summary(
        self,
        deposition_file_path: str,
        nuggets_file: str,
        summary_path: str,
        print_usage: bool = False,
        output_path: Optional[str] = None,
        max_workers: int = 1,
        top_n_nuggets: Optional[int] = None,
        mode: str = "consolidated",
    ) -> Dict:
        """
        Evaluates a summary based on nuggets and predefined criteria.

        Args:
            deposition_file_path: Path to the deposition file.
            nuggets_file: Path to the nuggets file.
            summary_path: Path to the summary file.
            print_usage: Whether to print token usage statistics.
            output_path: Optional path to save evaluation results.
            max_workers: Number of concurrent workers for parallel evaluation.
            top_n_nuggets: Number of top nuggets to check for completeness.
            mode: Evaluation mode ("consolidated" or "mapping").
            debug: If True, print score details for debugging.

        Returns:
            Dictionary with evaluation results and statistics.

        Raises:
            FileNotFoundError: If input files are not found.
            ValueError: If mode is invalid.
        """


        lines = read_transcript_file(deposition_file_path)
        extractor = QAExtractor(self.bedrock_client)
        extractor.extract_qa_pairs(lines)
        conversation = extractor.detect_speaker_names(self.config)
        self.logger.info("Starting comprehensive summary evaluation")

        # Validate inputs
        for path in [deposition_file_path, nuggets_file, summary_path]:
            if not Path(path).is_file():
                self.logger.error(f"File not found: {path}")
                raise FileNotFoundError(f"File not found: {path}")
        if mode not in ["consolidated", "mapping"]:
            self.logger.error(f"Invalid mode: {mode}")
            raise ValueError(f"Mode must be 'consolidated' or 'mapping', got {mode}")

        # Load data
        summary = "\n".join(read_transcript_file(summary_path))
        if mode=="consolidated":
            nugget_data = self.nugget_loader.load_nuggets_consolidated(nuggets_file)
        elif mode=="mapping":
            nugget_data = self.nugget_loader.load_nuggets(nuggets_file)


        # Parallel evaluation of criteria
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                "coverage": executor.submit(
                    self._evaluate_completeness,
                    nugget_data,
                    summary,
                    print_usage,
                    top_n_nuggets,
                    mode
                ),
                # "accuracy": executor.submit(
                #     self._evaluate_accuracy,
                #     nugget_data,
                #     summary,
                #     print_usage,
                #     max_workers  
                # ),
                "structure": executor.submit(
                    self._evaluate_structure,
                    summary,
                    print_usage
                ),
                # "clarity": executor.submit(
                #     self._evaluate_clarity,
                #     summary,
                #     print_usage
                # ),
                "citation_analysis": executor.submit(
                    self._evaluate_citation,
                    summary_path,
                    conversation,
                    deposition_file_path,
                    print_usage

                )
            }

            # Collect results
            results = collect_evaluation_results(futures, self.logger)

        # Compile final result
        final_result = {
            "summary_path": summary_path,
            "summary": summary,
            "criteria_scores": results,
            "stats": {
                # "total_consolidated_nuggets": len(nugget_data.consolidated_nuggets),
                "total_original_nuggets": sum(len(nuggets) for nuggets in nugget_data),
                "summary_length": len(summary.split())
            }
        }

        # Save results if output path provided
        if output_path:
            save_evaluation_results(final_result, output_path, self.config.ui_output_path, self.logger)

        return final_result

    def _evaluate_completeness(
        self,
        nugget_data: Any,
        summary: str,
        print_usage: bool,
        top_n_nuggets: Optional[int] = None,
        mode: str = "mapping"
    ) -> Dict:
        """Evaluates if top N nuggets are present in the summary."""
        self.logger.info(f"Evaluating completeness for top {top_n_nuggets} nuggets in {mode} mode")
        return evaluate_completeness(
            self.logger,
            self.token_manager.truncate_nuggets_for_prompt,
            self.bedrock_client,
            self.config,
            nugget_data,
            summary,
            print_usage,
            top_n_nuggets,
            mode
        )

    def _evaluate_accuracy(
        self,
        mapping: Dict[str, List[Dict[str, str]]],
        summary: str,
        print_usage: bool,
        max_workers: int = 4
    ) -> Dict:
        """Evaluates if inaccuracies exist in the summary against nuggets."""
        self.logger.info("Evaluating accuracy for summary against nuggets")
        return evaluate_accuracy(
            self.logger,
            self.token_manager.truncate_nuggets_for_prompt,
            self.bedrock_client,
            self.config,
            mapping,
            summary,
            print_usage
        )

    def _evaluate_structure(self, summary: str, print_usage: bool) -> Dict:
        """Evaluates the summary's structure and logical flow."""
        self.logger.info("Evaluating structure")
        return evaluate_structure(self.logger, self.bedrock_client, self.config, summary, print_usage)

    def _evaluate_clarity(self, summary: str, print_usage: bool) -> Dict:
        """Evaluates clarity of terminology, especially acronyms."""
        self.logger.info("Evaluating clarity of terminology")
        return evaluate_clarity(self.logger, self.bedrock_client, self.config, summary, print_usage)

    def _evaluate_citation(self, summary_path: str, conversation: Conversation, deposiiton_file_path: str, print_usage: bool):
        self.logger.info("Evaluating Citations")
        return evaluate_citations(self.logger, self.bedrock_client, self.config, summary_path, conversation,  deposiiton_file_path, print_usage)
def evaluate_summary_with_criteria(
    deposition_file_path: str,
    nuggets_file: str,
    summary_path: str,
    output_path: Optional[str] = None,
    mode: Optional[str] = None,
    generate_report: bool = True
) -> Dict:
    """
    Convenience function to evaluate a summary with all criteria.

    Args:
        deposition_file_path: Path to the deposition file.
        nuggets_file: Path to the nuggets file.
        summary_path: Path to the summary file.
        output_path: Optional path to save results.
        mode: Evaluation mode ("consolidated" or "mapping").
        generate_report: Whether to generate a human-readable report.

    Returns:
        Dictionary containing evaluation results.
    """
    evaluator = EnhancedSummaryEvaluator()
    results = evaluator.evaluate_summary(
        deposition_file_path=deposition_file_path,
        nuggets_file=nuggets_file,
        summary_path=summary_path,
        output_path=output_path,
        print_usage=True,
        mode=mode or "consolidated",
        # debug=generate_report
    )
    if generate_report:
        print(results)
    return results