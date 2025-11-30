# Lambda Ingestion - triggers KB ingestion when files uploaded to S3
# MUST be in same region as S3 Documents bucket (ap-southeast-2) for S3 event trigger
# Uses artifact uploaded to S3 by CI workflow

resource "aws_lambda_function" "ingest" {
  provider = aws.bedrock  # Deploy to ap-southeast-2 (same as S3 Documents and Knowledge Base)

  function_name = "${var.project}-ingest"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "lambda_handler.lambda_handler"
  runtime       = "python3.12"

  # Use artifact from S3 bucket uploaded by CI workflow
  s3_bucket        = var.artifact_bucket_name
  s3_key           = var.ingest_artifact_key
  source_code_hash = filebase64sha256("${path.module}/../assets/ingest_lambda/lambda_handler.py")

  timeout     = 30
  memory_size = 512

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.kb.id
      REGION            = var.bedrock_region
    }
  }
}