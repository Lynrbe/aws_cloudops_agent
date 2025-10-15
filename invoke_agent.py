import boto3
import json

client = boto3.client('bedrock-agentcore', region_name='ap-southeast-2')
payload = json.dumps({
    "input": {"prompt": "Explain machine learning in simple terms"}
})

response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:...:runtime/aws_cloudops_agent-scdvs',
    runtimeSessionId='dfmeoagmdfmeoagmascsdvlshmt',  # Must be 33+ chars
    payload=payload,
    qualifier="DEFAULT" # Optional
)
response_body = response['response'].read()
response_data = json.loads(response_body)
print("Agent Response:", response_data)