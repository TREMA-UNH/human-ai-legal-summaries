import os
from pydantic import BaseModel
from typing import Optional, Any

from transcript_analysis.models.pymodels import Conversation


class AppConfig(BaseModel):
    # AWS settings
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    # model_path: str = os.getenv("MODEL_PATH", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    model_path: str = os.getenv("MODEL_PATH", "anthropic.claude-3-haiku-20240307-v1:0")

    # model_path: str = os.getenv("MODEL_PATH", "amazon.nova-sonic-v1:0") # doesnt support converse api
    # model_path: str = os.getenv("MODEL_PATH", "amazon.nova-pro-v1:0")

    

    sso_profile: str = os.getenv("SSO_PROFILE", "nfarzi-dev")
    
    # Conversation settings
    fix_a: bool = True
    only_A_detection: bool = True
    conversation: Conversation  = Conversation()


    # General settings
    context_length: int = 2
    window_length_for_ner: int = 8
    max_tokens: int = 4000  # Reduced for Claude 3 Haiku (4096 limit)
    seed: int = 0
    limit_pairs: Optional[int] = None
    max_intro_chars: int = 500
    ui_output_path: str = os.getenv(
        "UI_OUTPUT_PATH",
        "/Users/nfarzi/Documents/nextpoint/deposition-pipeline-ui_/public/results/evaluation/evaluation_report.html"
    )

    def get(self, key: str, default: Any = None) -> Any:
        if key in self.model_fields:
            return getattr(self, key)
        if default is not None:
            return default
        raise AttributeError(f"'{key}' is not a valid configuration field")
    
    def __str__(self):
        return f"{self.model_path} {self.aws_region}"
    
    def update_from_args(self, args):
        """Update configuration attributes from parsed command-line arguments."""
        args_dict = vars(args)
        for field_name in self.model_fields:
            if field_name in args_dict and args_dict[field_name] is not None:
                setattr(self, field_name, args_dict[field_name])
                



class ConfigSingleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = AppConfig()
        return cls._instance

CONFIG = ConfigSingleton()                

