import os
import boto3
import json

# Hàm Lambda này thực hiện truy vấn RAG
def lambda_handler(event, context):
    kb_id = os.environ.get('KNOWLEDGE_BASE_ID')
    region = os.environ.get('REGION')
    
    # Lấy câu hỏi từ API Gateway event
    try:
        body = json.loads(event.get('body', '{}'))
        query = body.get('query', 'What is the product?')
    except:
        query = "Default query"

    client = boto3.client('bedrock-agent-runtime', region_name=region)
    
    # Gọi API Retrieve của Bedrock
    response = client.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={'text': query},
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 3
            }
        }
    )
    
    # Trả về kết quả truy xuất (References)
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(response['retrievalResults'])
    }