# Triển khai tất cả các tài nguyên
module "s3" {
  source = "./s3.tf"
}

module "opensearch" {
  source = "./opensearch.tf"
}

module "bedrock_kb" {
  source = "./bedrock_kb.tf"
}

module "iam" {
  source = "./iam.tf"
}

module "lambda_ingest" {
  source = "./lambda_ingest.tf"
}

module "lambda_retrieve" {
  source = "./lambda_retrieve.tf"
}