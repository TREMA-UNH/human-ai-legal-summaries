import boto3

def retrieve_or_create_inference_profile(config):
    aws_region: str = config.aws_region
    model_path: str = config.model_path
    sso_profile: str = config.sso_profile

    from src.utils.aws_session import create_aws_session
    session = create_aws_session(profile_name=sso_profile if sso_profile != "default" else None, region_name=aws_region)
    bedrock = session.client('bedrock')
    resource_groups = session.client('resourcegroupstaggingapi')

    # Step 1: Try to retrieve existing profile using required cost tags
    model_arn = f'arn:aws:bedrock:{aws_region}::foundation-model/{model_path}'
    response = resource_groups.get_resources(
        ResourceTypeFilters=['bedrock:application-inference-profile'],
        TagFilters=[
            {'Key': 'APPLICATION', 'Values': ['AI Research']},
            {'Key': 'ENVIRONMENT', 'Values': ['development']},
            {'Key': 'MODULE', 'Values': ['SummaryEvaluatorRD']},
            {'Key': 'SUBMODULE', 'Values': [model_arn]}
            # {'Key': 'SUBMODULE', 'Values':[f'arn:aws:bedrock:{aws_region}::foundation-model/{model_path}','depositon_file_name:test','summary_file_name:test']}
        ]
    )

    if response['ResourceTagMappingList']:
        profile_arn = response['ResourceTagMappingList'][0]['ResourceARN']
        print(f"Found Existing Profile: {profile_arn}")
        return profile_arn

    # Step 2: If not found, create a new one with required tags
    response = bedrock.create_inference_profile(
        inferenceProfileName='summary_evaluation',
        modelSource={
            'copyFrom': f'arn:aws:bedrock:{aws_region}::foundation-model/{model_path}'
        },
        tags=[
            {'key': 'APPLICATION', 'value': 'AI Research'},
            {'key': 'ENVIRONMENT', 'value': 'development'},
            {'key': 'MODULE', 'value': 'SummaryEvaluatorRD'},
            {'key': 'SUBMODULE', 'value': model_arn}
        ]
    )
    profile_arn = response['inferenceProfileArn']
    print(f"Created New Profile: {profile_arn}")
    return profile_arn
