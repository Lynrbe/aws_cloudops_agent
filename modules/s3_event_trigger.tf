# S3 Event Notification to trigger Lambda Ingestion automatically
# when new files are uploaded to docs/ prefix

# Allow S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3_invoke" {
  provider = aws.bedrock
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.rag_documents.arn
}

# S3 Bucket Notification - trigger Lambda on new file upload
resource "aws_s3_bucket_notification" "document_upload_trigger" {
  provider = aws.bedrock
  bucket = aws_s3_bucket.rag_documents.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "docs/"  # Only trigger for files in docs/ folder
    filter_suffix       = ""       # All file types
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
