"""Main entry point for nugget evaluation."""

import logging
import json
from typing import Dict, List

from src.vanilla_nuggetbased_evaluation.predefined_nuggetbased_evaluation import EnhancedSummaryEvaluator, evaluate_summary_with_criteria
from .nugget_evaluator import NuggetEvaluator
import argparse

logger = logging.getLogger(__name__)




def main():
    
    parser = argparse.ArgumentParser(description="evalute summary with nuggets")
    parser.add_argument("--nuggets", type=str, required = True, help="file for hierarchical nuggtes (.json)")
    parser.add_argument("--summary", type=str, required = True , help = "path to the summary file (.txt)")
    parser.add_argument("--deposition", type=str, required = True, help="deposiiton file path")
    parser.add_argument("--print-usage", action="store_true", help = " flag to print each single api call usage/cost")
    parser.add_argument("-o", "--output", type=str, required=True, help="path to store evaluation results (.json)")
    parser.add_argument("--mode", type = str, default = "consolidated", help = "mode for completeness checking can be consolidated or mapping")
    

    args = parser.parse_args()

    deposition_file_path, nuggets_file, summary_path, print_usage, output_path, mode =args.deposition, args.nuggets, args.summary, args.print_usage,  args.output, args.mode

    evaluator = EnhancedSummaryEvaluator()
    
    # Run evaluation -- output a dictionary (json format)
    results = evaluator.evaluate_summary(
        deposition_file_path=deposition_file_path,
        nuggets_file=nuggets_file,
        summary_path=summary_path,
        output_path=output_path,
        print_usage=print_usage,
        mode=mode
    )
    
    print(results)
    
    
    


if __name__ == "__main__":
    main()



