# Lambda Ingestion (Sử dụng Artifact ZIP từ GitHub Actions)
# MUST be in same region as S3 Documents bucket (ap-southeast-2) for S3 event trigger
resource "aws_lambda_function" "ingest" {
  provider = aws.bedrock  # Deploy to ap-southeast-2 (same as S3 Documents and Knowledge Base)

  function_name = "${var.project}-ingest"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.12"

  s3_bucket = data.aws_s3_bucket.rag_artifacts.bucket
  # Key được truyền từ GitHub Actions
  s3_key    = var.ingest_artifact_key

  timeout     = 30
  memory_size = 512

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.kb.id
      REGION            = var.bedrock_region
    }
  }
}