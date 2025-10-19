import os
import boto3
from config import CONFIG

# Environment variables
aws_region = os.getenv("AWS_REGION", "us-east-1")
sso_profile = os.getenv("SSO_PROFILE", "nfarzi-dev")

# Initialize session
from utils.aws_session import create_aws_session
session = create_aws_session(profile_name=sso_profile if sso_profile != "default" else None, region_name=aws_region)
resource_groups = session.client('resourcegroupstaggingapi')
bedrock = session.client('bedrock')

# Find resources tagged with research:summary_evaluation
response = resource_groups.get_resources(
    ResourceTypeFilters=['bedrock:application-inference-profile'],
    TagFilters=[
        {'Key': 'APPLICATION', 'Values': ['AI Research']},
            {'Key': 'ENVIRONMENT', 'Values': ['development']},
            {'Key': 'MODULE', 'Values': ['SummaryEvaluatorRD']},
            # {'Key': 'SUBMODULE', 'Values':[f'arn:aws:bedrock:{CONFIG.aws_region}::foundation-model/{CONFIG.model_path}','depositon_file_name:test','summary_file_name:test']}
                ]
)


# Collect profiles with creation dates
profiles = []
for resource in response['ResourceTagMappingList']:
    arn = resource['ResourceARN']
    profile_id = arn.split('/')[-1]
    try:
        profile_details = bedrock.get_inference_profile(inferenceProfileIdentifier=profile_id)
        creation_time = profile_details['createdAt']
        profiles.append({
            'profile_id': profile_id,
            'arn': arn,
            'createdAt': creation_time
        })
        print(f"{resource} {profile_id} {creation_time}")
    except Exception as e:
        print(f"Failed to get details for {profile_id}: {e}")

# Sort profiles by creation date
profiles.sort(key=lambda x: x['createdAt'])

# Keep the oldest (first in sorted list), delete the rest
if profiles:
    oldest_profile = profiles[0]
    print(f"Keeping oldest profile: {oldest_profile['profile_id']} (Created: {oldest_profile['createdAt']})")
    
    for profile in profiles[1:]:  # Skip the oldest
        print(f"Deleting profile: {profile['profile_id']} (Created: {profile['createdAt']})")
        try:
            bedrock.delete_inference_profile(inferenceProfileIdentifier=profile['profile_id'])
            print(f"Deleted: {profile['profile_id']}")
        except Exception as e:
            print(f"Failed to delete {profile['profile_id']}: {e}")
else:
    print("No profiles found.")

# Delete each tagged profile
# for resource in response['ResourceTagMappingList']:
#     arn = resource['ResourceARN']
#     profile_id = arn.split('/')[-1]
#     profile_details = bedrock.get_inference_profile(inferenceProfileIdentifier=profile_id)
#     creation_time = profile_details['createdAt']
#     print(resource, profile_id, creation_time )
    # print(f"Deleting profile: {profile_id}")
    
    # try:
    #     bedrock.delete_inference_profile(inferenceProfileIdentifier=profile_id)
    #     print(f"Deleted: {profile_id}")
    # except Exception as e:
    #     print(f"Failed to delete {profile_id}: {e}")
