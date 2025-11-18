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