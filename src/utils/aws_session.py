"""
AWS Session utility for handling both SSO and regular credentials
"""
import boto3
from botocore.exceptions import ProfileNotFound, NoCredentialsError
import os


def create_aws_session(profile_name=None, region_name=None):
    """
    Create an AWS session that works with both SSO and regular credentials.
    
    Args:
        profile_name: AWS profile name (optional)
        region_name: AWS region (optional)
    
    Returns:
        boto3.Session: Configured AWS session
    """
    region = region_name or os.getenv("AWS_REGION", "us-east-1")
    
    # If no profile specified or profile is "default", try without profile first
    if not profile_name or profile_name == "default":
        try:
            # Try creating session without profile (uses default credentials)
            session = boto3.Session(region_name=region)
            # Test if credentials work
            session.client('sts').get_caller_identity()
            return session
        except (NoCredentialsError, Exception):
            # Fall back to trying with default profile
            if profile_name != "default":
                profile_name = "default"
    
    # Try with specified profile
    if profile_name:
        try:
            session = boto3.Session(profile_name=profile_name, region_name=region)
            # Test if credentials work
            session.client('sts').get_caller_identity()
            return session
        except ProfileNotFound:
            print(f"Profile '{profile_name}' not found in AWS config")
        except Exception as e:
            print(f"Error with profile '{profile_name}': {e}")
    
    # Last resort: try without any profile
    try:
        session = boto3.Session(region_name=region)
        session.client('sts').get_caller_identity()
        return session
    except Exception as e:
        raise Exception(f"Could not create AWS session. Please check your AWS credentials. Error: {e}")


def create_bedrock_client(profile_name=None, region_name=None):
    """
    Create a Bedrock client with proper session handling.
    
    Args:
        profile_name: AWS profile name (optional)
        region_name: AWS region (optional)
    
    Returns:
        boto3.client: Bedrock runtime client
    """
    session = create_aws_session(profile_name, region_name)
    return session.client("bedrock-runtime")