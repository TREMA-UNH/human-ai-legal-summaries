import json
import logging
from dataclasses import dataclass
from typing import List, Dict, Any

from src.vanilla_nuggetbased_evaluation.evaluation_pymodels import ConsolidatedNuggetItem, NuggetData

logger = logging.getLogger(__name__)



class NuggetLoader:
    """Handles loading and parsing of nuggets JSON files."""

    def __init__(self):
        self.logger = logger

    def load_nuggets_consolidated(self, file_path: str) -> NuggetData:
        """Load and parse the nuggets JSON file."""
        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)

            self.logger.info(f"Successfully loaded nuggets from {file_path}")

            nuggets_list = [
                ConsolidatedNuggetItem(**item)
                for item in raw_data.get("consolidated_nuggets", [])
            ]

            return NuggetData(
                consolidated_nuggets=nuggets_list,
                mapping=raw_data.get("mapping", {}),
                raw_data=raw_data
            )
        except Exception as e:
            self.logger.error(f"Failed to load nuggets: {e}")
            raise
    

    def load_nuggets(self, file_path: str) -> NuggetData:
        """Load and parse the nuggets JSON file."""
        try:
            with open(file_path, 'r') as f:
                raw_data = json.load(f)

            self.logger.info(f"Successfully loaded nuggets from {file_path}")

            # raw_text_list = [
            #     item["nugget_text"]
            #     for item in raw_data.values()
            # ]

            return raw_data
        except Exception as e:
            self.logger.error(f"Failed to load nuggets: {e}")
            raise