# Terraform variables for RAG Infrastructure

aws_region               = "ap-southeast-1"
project_name             = "MyRAGAgent"
embedding_model_arn      = "arn:aws:bedrock:ap-southeast-1::foundation-model/amazon.titan-embed-text-v2:0"
vector_store_index_name  = "rag-agent-index"
s3_bucket_name_prefix    = "myragagent-documents-store"
