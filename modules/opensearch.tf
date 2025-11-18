resource "aws_opensearchserverless_security_policy" "encryption_policy" {
  name = "${var.project}-encrypt-policy"
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

  policy = jsonencode([
    {
      Rules = [
        {
          ResourceType = "index"
          Resource     = ["index/${lower(var.project)}-kb-collection/*"]
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
          Resource     = ["collection/${lower(var.project)}-kb-collection"]
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