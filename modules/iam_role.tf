# Role chung cho tất cả các Lambda Functions
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project}-lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })
}

# Policy cho phép Lambda truy cập Logs, S3, Bedrock, và OpenSearch
resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project}-lambda-policy"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Quyền CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      # Quyền đọc/ghi S3 và truy cập Artifacts
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
          "s3:PutObject",
        ]
        Resource = [
          "${aws_s3_bucket.rag_artifacts.arn}/*",
          "${aws_s3_bucket.rag_documents.arn}/*",
          aws_s3_bucket.rag_artifacts.arn,
          aws_s3_bucket.rag_documents.arn,
        ]
      },
      # Quyền Bedrock (triển khai API Gateway sau)
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock-agent:StartIngestionJob", # Dùng cho Lambda Ingest
          "bedrock-agent:ListDataSources",
        ]
        Resource = "*"
      },
      # Quyền OpenSearch
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = aws_opensearchserverless_collection.rag_collection.arn
      }
    ]
  })
}