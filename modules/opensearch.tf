# Encryption Security Policy
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${lower(var.project)}-encryption-policy"
  type = "encryption"

  policy = jsonencode({
    Rules = [
      {
        ResourceType = "collection"
        Resource     = ["collection/${lower(var.project)}-collection"]
      }
    ]
    AWSOwnedKey = true
  })
}

# Network Security Policy
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${lower(var.project)}-network-policy"
  type = "network"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "collection"
          Resource     = ["collection/${lower(var.project)}-collection"]
        }
      ]
      AllowFromPublic = true
    }
  ])
}

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "rag" {
  name = "${lower(var.project)}-collection"
  type = "VECTORSEARCH"

  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network
  ]

  tags = {
    Name    = "${var.project}-Collection"
    Project = var.project
  }
}

# Data Access Policy
resource "aws_opensearchserverless_access_policy" "data_access" {
  name = "${lower(var.project)}-data-access-policy"
  type = "data"

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/${lower(var.project)}-collection/*"]
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
          Resource     = ["collection/${lower(var.project)}-collection"]
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

# Access Policy for Bedrock Knowledge Base Role 
resource "aws_opensearchserverless_access_policy" "rag_data_access" {
  name = "${var.project}-kb-access"
  type = "data"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.project}-kb-service-role", # Tên Role Knowledge Base
        ]
        Action = [
          "aoss:CreateIndex",
          "aoss:DescribeIndex",
          "aoss:UpdateIndex",
          "aoss:DeleteIndex",
          "aoss:ReadDocument",
          "aoss:WriteDocument",
          "aoss:DescribeCollection"
        ]
        Resource = [
          "arn:aws:opensearchserverless:${var.region}:${data.aws_caller_identity.current.account_id}:collection/${aws_opensearchserverless_collection.rag_collection.id}",
          "arn:aws:opensearchserverless:${var.region}:${data.aws_caller_identity.current.account_id}:index/*"
        ]
      },
    ]
  })
}