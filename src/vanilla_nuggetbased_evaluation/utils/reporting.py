import json
from pathlib import Path
from typing import Dict
import logging
# from .html import save_html

def save_evaluation_results(result: Dict, output_path: str, ui_output_path: str, logger: logging.Logger) -> None:
    """Save evaluation results to JSON and HTML."""
    try:
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        logger.info(f"Saved evaluation results to {output_path}")
        # return result
        
        # html_path = output_path.replace(".json", ".html")
        # save_html(result, html_path)
        # logger.info(f"Saved HTML report to {html_path}")
        
        # if ui_output_path:
        #     save_html(result, ui_output_path)
        #     logger.info(f"Saved HTML report to UI path {ui_output_path}")
    except Exception as e:
        logger.error(f"Failed to save evaluation results: {str(e)}")
        raise