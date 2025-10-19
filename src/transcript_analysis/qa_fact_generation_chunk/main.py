import argparse
import json
import logging

# import logging.config
import spacy
import torch
import gzip

# from outlines import models
from transcript_analysis.models.pymodels import Fact, Sentence
from .utils.qa_parser_chunk import process_transcript_all_pairs
from config import CONFIG
import boto3
from botocore.exceptions import ClientError
import sys
from tenacity import RetryError
from transcript_analysis.qa_fact_generation.utils.bedrock_adapter import print_token_summary


"""
process_transcript extracts QA pairs and it assigns the speakers to the actual Q and A and generates narrative sentences 
"""

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
        print(f"CONFIG REGION NAME:{CONFIG}")
        # Initialize session with a specific profile
        # session = boto3.Session(profile_name="default")
        # bedrock = session.client("bedrock-runtime", region_name="us-east-1")
        session = boto3.Session(profile_name=CONFIG.sso_profile)
        bedrock = session.client("bedrock-runtime", region_name=CONFIG.aws_region)


        return bedrock
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        raise


def main():
    """Main function to process transcripts and generate facts."""
    parser = argparse.ArgumentParser(
        description="Extract facts from Q-A pairs in transcripts."
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        required=True,
        help="Path to output .jsonl.gz file (a list of facts).",
    )
    parser.add_argument(
        "--input", type=str, required=True, help="Path to input transcript file."
    )
    parser.add_argument(
        "--context-length",
        type=int,
        required=False,
        default=2,
        help="Number of previous sentences to use as context in the prompt when making statements from Q&As .",
    )
    parser.add_argument(
        "--window-length-for-ner",
        type=int,
        required=False,
        default=4,
        help="Context window size (before and after if current line) for NER.",
    )
    parser.add_argument(
        "--max-tokens",
        required=False,
        type=int,
        help="Maximum tokens for LLM generation.",
    )
    parser.add_argument(
        "--seed",
        required=False,
        default=0,
        type=int,
        help="Random seed for reproducibility.",
    )
    parser.add_argument(
        "--limit-pairs",
        required=False,
        type=int,
        help="Maximum number of Q-A pairs to process.",
    )
    parser.add_argument(
        "--ner-model",
        type=str,
        required=False,
        # default="en_core_web_sm",
        default="en_core_web_trf",
        help="Model name for NER recognition.",
    )
    parser.add_argument(
        "--model-path",
        required=False,
        help="llm model id aws llms on bedrock (to do detect speakers and generate statements)",
    )
    parser.add_argument(
        "--aws_region",
        required=False,
        help="aws region to connect to the bedrock-runtime",
    )
    parser.add_argument(
        "--no-speakers",
        action="store_true",
        help="Disable speaker detection and prepending.",
    )
    parser.add_argument(
        "--no-narrative",
        action="store_true",
        help="Disable narrative sentence generation.",
    )
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

    # parser.add_argument("--profile", type=str, help="profile name to connect to aws.")
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
        nlp = spacy.load(args.ner_model) if not args.no_speakers else None
        # model = models.transformers(args.model or CONFIG.model_path, device="cuda")
        bedrock_client = initialize_bedrock_model(CONFIG)
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        raise

    # Process transcript
    print("Phase: Process transcript")
    try:
        facts = process_transcript_all_pairs(
            bedrock_client,
            nlp,
            args.input,
            CONFIG,
            extract_qa=True,
            detect_speakers=not args.no_speakers,
            prepend_speakers=not args.no_speakers,
            generate_narrative=not args.no_narrative,
            print_usage = args.print_usage
        )
    except FileNotFoundError:
        logger.error(f"Input file not found: {args.input}")
        raise
    except (RetryError, ClientError) as e:
        handle_aws_error(e)
    except Exception as e:
        logger.error(f"Error processing input file: {e}")
        raise
    

    # Write to output
    print("Phase: Write to output")
    if facts:
        try:
            with gzip.open(args.output, "wt", encoding="utf-8") as f:
                for i, fact in enumerate(facts):
                    json.dump(fact.model_dump(), f)
                    f.write("\n")
                    # logger.info(f"Processed Q{i+1}: {fact.question_sa}")
                    # logger.info(f"Processed A{i+1}: {fact.answer_sa}")
                    # logger.info(f"Generated sentence: {fact.sentence}") if not args.no_speakers and not args.no_narrative else ""
        except Exception as e:
            logger.error(f"Error writing output file: {e}")
            raise
    
    print_token_summary()
    # with gzip.open(args.output, "rt", encoding="utf-8") as f:
    #     data = [json.loads(line) for line in f if line.strip()]
    #     print(data)


if __name__ == "__main__":
    main()
