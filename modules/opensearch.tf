resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name = "${var.project}-encrypt-policy"
  type = "encryption"
  
  # Using key default of AWS (AWSOwnedKey)
  policy = jsonencode([
    {
    "Rules" : [
      {
        "ResourceType" : "collection",
        "Resource" : ["collection/${var.project}-kb-collection"] #static name
      }
    ],
    "AWSOwnedKey" : true 
    }
  ])
}

resource "aws_opensearchserverless_security_policy" "network_policy" {
  name = "${var.project}-network-policy"
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
          aws_iam_role.kb_service_role.arn,
          data.aws_caller_identity.current.arn
        ]
        Action = [
          "aoss:*" 
        ]
        Resource = [
          aws_opensearchserverless_collection.rag_collection.arn,
          "${aws_opensearchserverless_collection.rag_collection.arn}/*"
        ]
      },
    ]
  })

  depends_on = [
    aws_opensearchserverless_collection.rag_collection,
    aws_iam_role.kb_service_role
  ]
}