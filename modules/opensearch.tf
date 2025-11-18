resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name = "${var.project}-kb-encryption-policy"
  type = "encryption"
  
  policy = jsonencode({
    "Rules" : [
      {
        "ResourceType" : "collection",
        "Resource" : ["collection/${aws_opensearchserverless_collection.rag_collection.name}"]
      }
    ],
    "AWSOwnedKey" : true 
  })
}

resource "aws_opensearchserverless_security_policy" "network_policy" {
  name = "${var.project}-kb-network-policy"
  type = "network"
  
  policy = jsonencode([
    {
      "Rules" : [
        {
          "ResourceType" : "collection",
          "Resource" : ["collection/${aws_opensearchserverless_collection.rag_collection.name}"]
        }
      ],
      "AllowFromPublic" : true 
    }
  ])
}

# OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "rag_collection" {
  name = "${var.project}-kb-collection" 
  type = "VECTORSEARCH"
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