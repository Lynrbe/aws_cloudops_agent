import boto3

client = boto3.client('bedrock-agentcore-control')

response = client.create_agent_runtime(
    agentRuntimeName='aws_cloudops_agent',
    agentRuntimeArtifact={
        'containerConfiguration': {
            'containerUri': '....:latest'
        }
    },
    networkConfiguration={"networkMode": "PUBLIC"},
    roleArn='arn:aws:iam::010382427026:role/AgentRuntimeRole'
)

print(f"Agent Runtime created successfully!")
print(f"Agent Runtime ARN: {response['agentRuntimeArn']}")
print(f"Status: {response['status']}")