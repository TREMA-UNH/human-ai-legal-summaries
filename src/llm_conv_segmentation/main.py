import argparse
import json
import gzip
import logging

from .segmenter import annotate_facts
from config import CONFIG

import boto3
from botocore.exceptions import ClientError
import sys
from tenacity import RetryError
import torch

import logging

logger = logging.Logger(__name__)
logging.basicConfig(level = logging.INFO)

def handle_aws_error(error):
    """Handle AWS errors with clean user messages and exit."""
    
    # Handle RetryError wrapping ClientError
    if isinstance(error, RetryError):
        if hasattr(error, 'last_attempt') and error.last_attempt.exception():
            original_error = error.last_attempt.exception()
            if isinstance(original_error, ClientError):
                error_code = original_error.response['Error']['Code']
                if error_code == 'ExpiredTokenException':
                    print("Error: Your AWS credentials have expired.")
                    print("Please refresh your AWS credentials and try again.")
                    sys.exit(1)
        print("Error: Failed to process transcript. Please try again.")
        sys.exit(1)
    
    # Handle direct ClientError
    elif isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        if error_code == 'ExpiredTokenException':
            print("Error: Your AWS credentials have expired.")
            print("Please refresh your AWS credentials and try again.")
        else:
            print(f"AWS Error: {error.response['Error']['Message']}")
        sys.exit(1)

def initialize_bedrock_model(CONFIG):
    try:
        from src.utils.aws_session import create_bedrock_client
        
        print(f"CONFIG REGION NAME:{CONFIG}")
        # Use the new utility that handles both SSO and regular credentials
        bedrock = create_bedrock_client(
            profile_name=CONFIG.sso_profile if CONFIG.sso_profile != "default" else None,
            region_name=CONFIG.aws_region
        )
        
        print("✓ AWS Bedrock client initialized successfully")
        return bedrock
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        raise



def main():
    parser = argparse.ArgumentParser(description="prompting llm to segment the conversation with segment id and confidence level")
    parser.add_argument("--input",type=str, required=True, help="input .jsonl.gz file to read the Q&A pairs from")
    parser.add_argument("-o","--output", type=str, required=True, help="jsonl.gz file to store new facts with segment id and cofidence level")
    parser.add_argument("--model-id", type=str, required=False)
    parser.add_argument("--chunk-size", type=int, required=False, default=6000)
    parser.add_argument(
        "--logger-level",
        default="info",
        type=str,
        help="just choose between [info, debug]",
    )
    parser.add_argument(
        "--print-usage",
        action="store_true",
        help="print llm usage",
    )
    parser.add_argument("--sso-profile", type=str, required=True, help="aws sso profile set in ~/.aws/config.")

    args = parser.parse_args()


    # Configure logging
    logging.basicConfig(
        level=logging.INFO if args.logger_level == "info" else logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger = logging.getLogger(__name__)

    # Update configuration with command-line arguments
    CONFIG.update_from_args(args)
    # print(CONFIG)
    # Set random seed
    torch.random.manual_seed(CONFIG.seed)

    # Initialize models
    try:
        # model = models.transformers(args.model or CONFIG.model_path, device="cuda")
        bedrock_client = initialize_bedrock_model(CONFIG)
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        raise

    annotate_facts(args.input, args.output, bedrock_client, CONFIG, args.print_usage, args.chunk_size)
    
if __name__=="__main__":
    main()