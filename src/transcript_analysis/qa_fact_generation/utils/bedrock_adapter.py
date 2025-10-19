from logging import config
import boto3
from botocore.exceptions import ClientError
import logging
import time
import sys
from backend.log_pipeline import log_each_generation
from make_inference_profile import retrieve_or_create_inference_profile
from src.transcript_analysis.models.TokenTracker import token_tracker
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryError
)
from typing import Any, Dict, List, Optional, Type
from config import CONFIG
logger = logging.getLogger(__name__)
inference_prof = retrieve_or_create_inference_profile(CONFIG)
CSV_LOG_PATH = "/Users/nfarzi/Documents/nextpoint/deposition-pipeline-ui_/public/evaluation_pipeline_run_log.csv"



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

def initialize_bedrock_model(CONFIG: config) -> boto3.client:
    try:
        # Initialize session with a specific profile
        print(CONFIG.sso_profile)
        session = boto3.Session(profile_name=CONFIG.sso_profile)
        creds = session.get_credentials().get_frozen_credentials()

        print("AWS_ACCESS_KEY_ID =", creds.access_key)
        print("AWS_SECRET_ACCESS_KEY =", creds.secret_key)
        print("AWS_SESSION_TOKEN =", creds.token)
        bedrock = session.client("bedrock-runtime", region_name=CONFIG.aws_region, )

        return bedrock
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        raise


# Bedrock pricing per 1000 tokens from aws website( can add dynamically retrieve them later)
BEDROCK_PRICING = {
    'anthropic.claude-3-5-sonnet-20241022-v2:0': {
        
        'input': 0.003,   # $0.003 per 1k input tokens
        'output': 0.015   # $0.015 per 1k output tokens
    },
    'anthropic.claude-3-5-sonnet-20240620-v1:0': {
        
        'input': 0.003,   # $0.003 per 1k input tokens
        'output': 0.015   # $0.015 per 1k output tokens
    },
    "amazon.nova-sonic-v1:0":{
        'input': 0.00006,   # $0.003 per 1k input tokens
        'output': 0.00024   # $0.015 per 1k output tokens
    },
    "amazon.nova-pro-v1:0": {
        'input': 0.0008,   # $0.80 per 1k input tokens
        'output': 0.0032   # $3.20 per 1k output tokens
    }
}

def calculate_cost(model_id: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate cost based on model pricing"""
    pricing = BEDROCK_PRICING.get(model_id, {'input': 0.001, 'output': 0.005})  # default fallback
    input_cost = (input_tokens / 1000) * pricing['input']
    output_cost = (output_tokens / 1000) * pricing['output']
    return input_cost + output_cost


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=4, max=10),
    retry=retry_if_exception_type(ClientError),
    before_sleep=lambda retry_state: logger.info(
        f"Retrying Bedrock API: attempt {retry_state.attempt_number} (waiting longer due to rate limits)"
    ),
)
def generate_structured_output(
    bedrock_client: boto3.client,
    messages: List[Dict[str, Any]],
    tool_schema: Dict[str, Any],
    tool_schema_name: str,
    description: str,
    model_id: str,
    obj: Type[Any],
    max_tokens: int = 10000,
    max_retries: int = 2,
    print_usage: bool = False, 
    temp: float = 0.1,
    top_p: float = 0.1
):
    """
    Generate structured output using Amazon Bedrock Converse API with token and time tracking.

    Args:
        bedrock_client: Boto3 Bedrock runtime client
        messages: List of message dictionaries (now we just use one message but it is expandable for multi-turn conversation)
        tool_schema: JSON schema for structured output
        tool_schema_name: Name of the tool for Bedrock API
        model_id: Bedrock model ID
        obj: Pydantic model class for output validation
        max_tokens: Maximum tokens for generation
        max_retries: Number of retries for invalid tool responses
        print_usage: Whether to print usage stats for this individual call

    Returns:
        Validated Pydantic model instance

    Raises:
        ValueError: If no valid tool response after max_retries
        ClientError: For Bedrock API errors
    """

    
    call_input_tokens = 0
    call_output_tokens = 0
    call_cost = 0.0
    # Start timing the entire function call
    start_time = time.time()

    toolconfig = {
        "tools": [
            {
                "toolSpec": {
                    "name": tool_schema_name,
                    "description": description,
                    "inputSchema": {"json": tool_schema}, # for structured output
                }
            }
        ],
        "toolChoice": {# force claude to use the tool -- 
                       # force claude to get the strcutured output I am passing to it
        "tool": {
            "name": tool_schema_name
        }
    }
    }

    

    try:
        for attempt in range(max_retries):
            try:
                # Time individual API call
                api_start_time = time.time()
                
                response = bedrock_client.converse(
                    modelId=inference_prof,
                    messages=messages,
                    toolConfig=toolconfig,
                    inferenceConfig={"maxTokens": max_tokens,
                                     "temperature": temp,
                                     "topP": top_p
                                     },
                )
                
                api_end_time = time.time()
                api_call_time = api_end_time - api_start_time
                
                # Extract token usage from response
                usage = response.get('usage', {})
                input_tokens = usage.get('inputTokens', 0)
                output_tokens = usage.get('outputTokens', 0)
                
                # Calculate cost for this call
                cost = calculate_cost(model_id, input_tokens, output_tokens)
                
                # Accumulate tokens and cost
                call_input_tokens += input_tokens
                call_output_tokens += output_tokens
                call_cost += cost
                
                # Log individual API call timing if requested
                if print_usage:
                    print(f"API call {attempt + 1} took: {api_call_time:.2f} seconds")
                


                content_list = response["output"]["message"].get("content", [])
                for content in response["output"]["message"]["content"]:
                    if "toolUse" in content:
                        # Calculate total function execution time
                        end_time = time.time()
                        total_call_time = end_time - start_time
                        
                        # Update global tracker
                        token_tracker.update(call_input_tokens, call_output_tokens, call_cost, total_call_time)
                        
                        # Log individual call stats if requested
                        if print_usage:
                            logger.info(f"\nCall {token_tracker.usage.call_count} Summary:")
                            logger.info(f"Model: {model_id}")
                            logger.info(f"Input tokens: {call_input_tokens}, Output tokens: {call_output_tokens}")
                            logger.info(f"Cost: ${call_cost:.4f}")
                            logger.info(f"Total execution time: {total_call_time:.2f} seconds")
                        log_each_generation(description, token_tracker.usage.call_count, call_input_tokens, call_output_tokens, call_cost, total_call_time, CSV_LOG_PATH)
                        return obj(**content["toolUse"]["input"])
                
                logger.warning(
                    f"Attempt {attempt + 1}: No valid tool response, retrying..."
                )
                # Modify prompt for stricter instructions
                # messages[-1]["content"][0][
                #     "text"
                # ] += "\nEnsure output strictly follows the JSON schema."
                
            except ClientError as e:
                logger.error(f"Bedrock API error: {e}")
                raise
        
        # If we get here, all attempts failed
        end_time = time.time()
        total_call_time = end_time - start_time
        token_tracker.update(call_input_tokens, call_output_tokens, call_cost, total_call_time)
        raise ValueError(f"Failed to generate valid tool response after {max_retries} attempts: {content_list}")
    
    except Exception as e:
        # Ensure timing is tracked even if an exception occurs
        end_time = time.time()
        total_call_time = end_time - start_time
        token_tracker.update(call_input_tokens, call_output_tokens, call_cost, total_call_time)
        raise

