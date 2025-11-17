terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# =================================================================
# VARIABLES
# =================================================================
variable "aws_region" {
  type        = string
  default     = "ap-southeast-1"
  description = "AWS region"
}

variable "project_name" {
  type        = string
  default     = "MyRAGAgent"
  description = "Base name for all resources"
}

variable "embedding_model_arn" {
  type        = string
  default     = "arn:aws:bedrock:ap-southeast-1::foundation-model/amazon.titan-embed-text-v2:0"
  description = "ARN of the Foundation Model used to create Embeddings"
}

variable "vector_store_index_name" {
  type        = string
  default     = "rag-agent-index"
  description = "Name of the Index (Table) in OpenSearch (must be lowercase, no spaces)"
}

variable "s3_bucket_name_prefix" {
  type        = string
  default     = "myragagent-documents-store"
  description = "Prefix for S3 Bucket name"
}

# =================================================================
# DATA SOURCES
# =================================================================
data "aws_caller_identity" "current" {}

# =================================================================
# S3 BUCKET
# =================================================================
resource "aws_s3_bucket" "rag_documents" {
  bucket = "${var.s3_bucket_name_prefix}-${data.aws_caller_identity.current.account_id}-${var.aws_region}"

  tags = {
    Name    = "${var.project_name}-RAGDocuments"
    Project = var.project_name
  }

  # Optional: if you want Terraform to force delete bucket with objects on destroy,
  # uncomment the following line.
  # force_destroy = true
}

resource "aws_s3_bucket_versioning" "rag_documents" {
  bucket = aws_s3_bucket.rag_documents.id

  versioning_configuration {
    status = "Enabled"
  }
}

# =================================================================
# OPENSEARCH SERVERLESS
# =================================================================

# Encryption Security Policy
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${lower(var.project_name)}-encryption-policy"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${lower(var.project_name)}-collection"]
      }
    ]
    AWSOwnedKey = true
  })
}

# Network Security Policy
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${lower(var.project_name)}-network-policy"
  type = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${lower(var.project_name)}-collection"]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "rag" {
  name = "${lower(var.project_name)}-collection"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network
  ]

  tags = {
    Name    = "${var.project_name}-Collection"
    Project = var.project_name
  }
}

# Data Access Policy
resource "aws_opensearchserverless_access_policy" "data_access" {
  name = "${lower(var.project_name)}-data-access-policy"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/${lower(var.project_name)}-collection/*"]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DescribeIndex",
            "aoss:UpdateIndex",
            "aoss:DeleteIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
        },
        {
          ResourceType = "collection"
          Resource     = ["collection/${lower(var.project_name)}-collection"]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
        }
      ]
      Principal = [aws_iam_role.knowledge_base.arn]
    }
  ])

  depends_on = [
    aws_iam_role.knowledge_base,
    aws_opensearchserverless_collection.rag
  ]
}

# =================================================================
# IAM ROLE FOR KNOWLEDGE BASE
# =================================================================
resource "aws_iam_role" "knowledge_base" {
  name = "${var.project_name}-KnowledgeBaseRole"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name    = "${var.project_name}-KnowledgeBaseRole"
    Project = var.project_name
  }
}

resource "aws_iam_role_policy" "knowledge_base_permissions" {
  name = "KnowledgeBasePermissions"
  role = aws_iam_role.knowledge_base.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.rag_documents.arn,
          "${aws_s3_bucket.rag_documents.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["aoss:APIAccessAll"]
        Resource = aws_opensearchserverless_collection.rag.arn
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = var.embedding_model_arn
      }
    ]
  })
}

# =================================================================
# Create OpenSearch index via local-exec (so Bedrock KB can reference it)
# =================================================================
# This null_resource will run a bash script that:
# - verifies aws + jq available
# - calls aws opensearchserverless create-index
# - polls get-index until status becomes ACTIVE/READY
resource "null_resource" "create_opensearch_index" {
  triggers = {
    collection_id = aws_opensearchserverless_collection.rag.id
    index_name    = lower(var.vector_store_index_name)
    region        = var.aws_region
  }

  provisioner "local-exec" {
    interpreter = ["bash", "-c"]
    command = <<-EOT
      set -euo pipefail

      COLLECTION_ID="${aws_opensearchserverless_collection.rag.id}"
      INDEX_NAME="${lower(var.vector_store_index_name)}"
      REGION="${var.aws_region}"

      echo "Checking aws cli and jq availability..."
      if ! command -v aws >/dev/null 2>&1; then
        echo "ERROR: aws CLI not found in PATH." >&2
        exit 2
      fi
      if ! command -v jq >/dev/null 2>&1; then
        echo "ERROR: jq not found in PATH. Please install jq." >&2
        exit 2
      fi

      echo "Creating OpenSearch Serverless index '$INDEX_NAME' in collection '$COLLECTION_ID' (region $REGION)..."

      # Create index (if exists, ignore error and continue to poll)
      if aws opensearchserverless create-index --id "$COLLECTION_ID" --index-name "$INDEX_NAME" --region "$REGION" 2>/tmp/create_idx_err.log; then
        echo "Create-index API accepted."
      else
        echo "create-index returned non-zero. Details:"
        cat /tmp/create_idx_err.log || true
        echo "Continuing to poll for index readiness (it may already exist or be in progress)."
      fi

      # Poll until index status becomes ACTIVE or READY (timeout after ~5 minutes)
      MAX_RETRIES=60
      SLEEP_SECONDS=5
      i=0
      while [ $i -lt $MAX_RETRIES ]; do
        i=$((i+1))
        # Query get-index
        aws opensearchserverless get-index --id "$COLLECTION_ID" --index-name "$INDEX_NAME" --region "$REGION" >/tmp/get_idx_out.json 2>/tmp/get_idx_err.log || true
        if jq -e '.status' /tmp/get_idx_out.json >/dev/null 2>&1; then
          STATUS=$(jq -r '.status' /tmp/get_idx_out.json)
          echo "Index status: $STATUS (attempt $i/$MAX_RETRIES)"
          if [ "$STATUS" = "ACTIVE" ] || [ "$STATUS" = "READY" ]; then
            echo "Index is ready."
            exit 0
          fi
        else
          # handle not found or other messages
          if grep -q "ResourceNotFoundException" /tmp/get_idx_err.log 2>/dev/null; then
            echo "Index not found yet (attempt $i/$MAX_RETRIES)."
          else
            echo "get-index output (if any):"
            cat /tmp/get_idx_out.json || true
            echo "get-index stderr (if any):"
            cat /tmp/get_idx_err.log || true
          fi
        fi
        sleep $SLEEP_SECONDS
      done

      echo "Timed out waiting for index to become ACTIVE/READY. See /tmp/get_idx_out.json and /tmp/get_idx_err.log for details."
      exit 1
    EOT
  }

  depends_on = [
    aws_opensearchserverless_collection.rag
  ]
}

# =================================================================
# BEDROCK KNOWLEDGE BASE
# =================================================================
resource "aws_bedrockagent_knowledge_base" "rag" {
  name     = "${var.project_name}-KnowledgeBase"
  role_arn = aws_iam_role.knowledge_base.arn

  description = "Knowledge Base for ${var.project_name} RAG System"

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = var.embedding_model_arn
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.rag.arn
      vector_index_name = var.vector_store_index_name
      field_mapping {
        vector_field   = "vector"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }

  depends_on = [
    aws_opensearchserverless_access_policy.data_access,
    aws_iam_role_policy.knowledge_base_permissions,
    null_resource.create_opensearch_index
  ]

  tags = {
    Name    = "${var.project_name}-KnowledgeBase"
    Project = var.project_name
  }
}

# =================================================================
# BEDROCK DATA SOURCE
# =================================================================
resource "aws_bedrockagent_data_source" "s3" {
  name              = "${var.project_name}-S3DataSource"
  knowledge_base_id = aws_bedrockagent_knowledge_base.rag.id

  description = "S3 Data Source for ${var.project_name} Knowledge Base"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.rag_documents.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 512
        overlap_percentage = 20
      }
    }
  }

  depends_on = [
    aws_bedrockagent_knowledge_base.rag
  ]
}

# =================================================================
# OUTPUTS
# =================================================================
output "s3_bucket_name" {
  description = "S3 Bucket name for RAG documents"
  value       = aws_s3_bucket.rag_documents.id
}

output "s3_bucket_arn" {
  description = "S3 Bucket ARN for RAG documents"
  value       = aws_s3_bucket.rag_documents.arn
}

output "opensearch_collection_arn" {
  description = "OpenSearch Serverless Collection ARN"
  value       = aws_opensearchserverless_collection.rag.arn
}

output "opensearch_collection_endpoint" {
  description = "OpenSearch Serverless Collection Endpoint"
  value       = aws_opensearchserverless_collection.rag.collection_endpoint
}

output "knowledge_base_role_arn" {
  description = "IAM Role ARN for Knowledge Base"
  value       = aws_iam_role.knowledge_base.arn
}

output "vector_index_name" {
  description = "Vector index name used for Knowledge Base"
  value       = var.vector_store_index_name
}

output "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID"
  value       = aws_bedrockagent_knowledge_base.rag.id
}

output "knowledge_base_arn" {
  description = "Bedrock Knowledge Base ARN"
  value       = aws_bedrockagent_knowledge_base.rag.arn
}

output "data_source_id" {
  description = "Bedrock Data Source ID"
  value       = aws_bedrockagent_data_source.s3.id
}
