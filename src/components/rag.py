import boto3
from botocore.config import Config
from utils.config import load_configs

agentcore_config = load_configs()
kb_id = agentcore_config.get("knowledge_base")
region = agentcore_config.get("aws", {}).get("region", "ap-southeast-1")
model = agentcore_config.get("agent")

client = boto3.client("bedrock-agent-runtime", region_name=region)

def ask_kb(query: str) -> dict:
    
    resp = client.retrieve_and_generate(
        input={"text": query},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": kb_id,
                "modelArn": model
            }
        }
    )
    return {
        "answer": resp.get("output", {}).get("text", ""),
        "citations": resp.get("citations", [])
    }
