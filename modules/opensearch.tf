resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name = "${var.project}-kb-encryption-policy"
  type = "encryption"
  
  # Using key default of AWS (AWSOwnedKey)
  policy = jsonencode({
    "Rules" : [
      {
        "ResourceType" : "collection",
        "Resource" : ["collection/${var.project}-kb-collection"] #static name
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
          "Resource" : ["collection/${var.project}-kb-collection"]
        }
      ],
      "AllowFromPublic" : true 
    }
  ])
}

# 3. OpenSearch Serverless Collection
resource "aws_opensearchserverless_collection" "rag_collection" {
  name = "${var.project}-kb-collection"
  type = "VECTORSEARCH"
  
  depends_on = [
    aws_opensearchserverless_security_policy.encryption_policy,
    aws_opensearchserverless_security_policy.network_policy
  ]
}

# 4. Access Policy 
resource "aws_opensearchserverless_access_policy" "rag_data_access" {
  name = "${var.project}-kb-access"
  type = "data"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = [
          aws_iam_role.kb_service_role.arn
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
          aws_opensearchserverless_collection.rag_collection.arn,
          "${aws_opensearchserverless_collection.rag_collection.arn}/*"
        ]
      },
    ]
  })

  # Đảm bảo Collection được tạo trước khi áp dụng Access Policy
  depends_on = [
    aws_opensearchserverless_collection.rag_collection,
    aws_iam_role.kb_service_role
  ]
}