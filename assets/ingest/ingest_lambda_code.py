import os
import json
import boto3
import logging

# Cấu hình logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Lấy ID của Knowledge Base từ biến môi trường (Được truyền từ CloudFormation)
KNOWLEDGE_BASE_ID = os.environ.get('KNOWLEDGE_BASE_ID')

# Khởi tạo Bedrock Agent Client
bedrock_agent_client = boto3.client('bedrock-agent')

def lambda_handler(event, context):
    """
    Hàm xử lý chính. Kích hoạt bởi S3 Event Notification khi có file mới được tải lên.
    Mục tiêu: Gọi API Bedrock StartIngestionJob.
    """
    logger.info("--- Bắt đầu Ingestion Job ---")
    logger.info(f"Sự kiện nhận được: {json.dumps(event)}")

    if not KNOWLEDGE_BASE_ID:
        logger.error("Lỗi: Biến môi trường KNOWLEDGE_BASE_ID chưa được thiết lập.")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Missing KNOWLEDGE_BASE_ID'})
        }

    try:
        # 1. Liệt kê Data Sources để lấy ID
        response = bedrock_agent_client.list_data_sources(
            knowledgeBaseId=KNOWLEDGE_BASE_ID
        )
        
        data_sources = response.get('dataSourceSummaries', [])
        if not data_sources:
            logger.error(f"Lỗi: Không tìm thấy Data Source nào cho Knowledge Base ID: {KNOWLEDGE_BASE_ID}")
            return {
                'statusCode': 404,
                'body': json.dumps({'message': 'No data sources found'})
            }

        # 2. Lấy Data Source ID đầu tiên (vì bạn chỉ có 1 S3 Data Source)
        data_source_id = data_sources[0]['dataSourceId']
        logger.info(f"Tìm thấy Data Source ID: {data_source_id}")

        # 3. Kích hoạt Ingestion Job
        ingestion_response = bedrock_agent_client.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=data_source_id
        )

        job_id = ingestion_response['ingestionJob']['ingestionJobId']
        logger.info(f"Đã kích hoạt Ingestion Job thành công. Job ID: {job_id}")

        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Ingestion job started successfully. Job ID: {job_id}'})
        }

    except Exception as e:
        logger.error(f"Lỗi khi kích hoạt Ingestion Job: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'message': f'Failed to start ingestion job: {str(e)}'})
        }