#!/usr/bin/env python3
"""
Script to create OpenSearch Serverless index for Bedrock Knowledge Base.
This must be run before creating the Knowledge Base.
"""

import boto3
import json
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth

def create_opensearch_index(
    collection_endpoint,
    index_name,
    region='ap-southeast-1'
):
    """
    Create an index in OpenSearch Serverless collection.

    Args:
        collection_endpoint: The OpenSearch collection endpoint (without https://)
        index_name: Name of the index to create
        region: AWS region
    """

    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()

    # Create auth for OpenSearch
    auth = AWSV4SignerAuth(credentials, region, 'aoss')

    # Remove https:// if present
    host = collection_endpoint.replace('https://', '')

    # Create OpenSearch client
    client = OpenSearch(
        hosts=[{'host': host, 'port': 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=300
    )

    # Check if index already exists
    if client.indices.exists(index=index_name):
        print(f"Index '{index_name}' already exists.")
        return

    # Define index mapping for Bedrock Knowledge Base
    index_body = {
        "settings": {
            "index.knn": True,
            "number_of_shards": 2,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "vector": {
                    "type": "knn_vector",
                    "dimension": 1024,  # Titan Embed Text v2 uses 1024 dimensions
                    "method": {
                        "name": "hnsw",
                        "engine": "faiss",
                        "parameters": {
                            "ef_construction": 512,
                            "m": 16
                        }
                    }
                },
                "text": {
                    "type": "text"
                },
                "metadata": {
                    "type": "text"
                },
                "AMAZON_BEDROCK_TEXT_CHUNK": {
                    "type": "text",
                    "index": False
                },
                "AMAZON_BEDROCK_METADATA": {
                    "type": "text",
                    "index": False
                }
            }
        }
    }

    # Create the index
    response = client.indices.create(index=index_name, body=index_body)
    print(f"Index '{index_name}' created successfully!")
    print(f"Response: {json.dumps(response, indent=2)}")


if __name__ == "__main__":
    import sys

    # Get collection endpoint from Terraform output or command line
    if len(sys.argv) > 1:
        collection_endpoint = sys.argv[1]
        index_name = sys.argv[2] if len(sys.argv) > 2 else "rag-agent-index"
    else:
        # Get from Terraform output
        import subprocess
        result = subprocess.run(
            ["terraform", "output", "-json"],
            cwd="/home/dli2hc/awscloudopsagent/ai_agent/src/components",
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            print("Error: Could not get Terraform outputs")
            print("Usage: python3 create_opensearch_index.py <collection_endpoint> [index_name]")
            sys.exit(1)

        outputs = json.loads(result.stdout)
        collection_endpoint = outputs.get("opensearch_collection_endpoint", {}).get("value")
        index_name = outputs.get("vector_index_name", {}).get("value", "rag-agent-index")

        if not collection_endpoint:
            print("Error: Could not find opensearch_collection_endpoint in Terraform outputs")
            sys.exit(1)

    print(f"Creating index '{index_name}' in collection: {collection_endpoint}")
    create_opensearch_index(collection_endpoint, index_name)
