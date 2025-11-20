import os
import boto3
import json

# Lambda function to trigger indexing for Bedrock Knowledge Base
def lambda_handler(event, context):
    kb_id = os.environ.get('KNOWLEDGE_BASE_ID')
    region = os.environ.get('REGION')

    if not kb_id:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'KNOWLEDGE_BASE_ID not set.'})
        }

    client = boto3.client('bedrock-agent', region_name=region)

    try:
        # Get the first Data Source from the Knowledge Base
        data_sources = client.list_data_sources(knowledgeBaseId=kb_id)
        if not data_sources['dataSourceSummaries']:
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Data Source not found.'})
            }

        data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']

        # Start Ingestion Job
        response = client.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )

        ingestion_job_id = response['ingestionJob']['ingestionJobId']

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Ingestion job started for KB {kb_id}',
                'knowledgeBaseId': kb_id,
                'dataSourceId': data_source_id,
                'ingestionJobId': ingestion_job_id
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
