import os
import boto3
import json

# Hàm Lambda này kích hoạt việc indexing cho Bedrock Knowledge Base
def lambda_handler(event, context):
    kb_id = os.environ.get('KNOWLEDGE_BASE_ID')
    region = os.environ.get('REGION')
    
    if not kb_id:
        return {'statusCode': 500, 'body': json.dumps('KNOWLEDGE_BASE_ID not set.')}
        
    client = boto3.client('bedrock-agent', region_name=region)
    
    # Giả định Knowledge Base có 1 Data Source duy nhất
    data_sources = client.list_data_sources(knowledgeBaseId=kb_id)
    if not data_sources['dataSourceSummaries']:
        return {'statusCode': 404, 'body': json.dumps('Data Source not found.')}
        
    data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']
    
    # Bắt đầu Job Indexing
    client.start_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=data_source_id
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': f'Ingestion job started for KB {kb_id}.'})
    }