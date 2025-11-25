#!/bin/bash
# Setup environment variables for Knowledge Base retrieval testing

echo "🔧 Setting up Knowledge Base environment variables..."
echo ""

# Get Terraform outputs
cd /home/dli2hc/repo/ai_agent

if [ ! -d ".terraform" ]; then
    echo "❌ Error: Terraform not initialized in this directory"
    echo "Please run 'terraform init' first"
    exit 1
fi

# Get Knowledge Base ID
KB_ID=$(terraform output -raw knowledge_base_id 2>/dev/null)

if [ -z "$KB_ID" ]; then
    echo "❌ Error: Could not get Knowledge Base ID from Terraform"
    echo "Make sure Terraform is deployed and knowledge_base_id output exists"
    exit 1
fi

# Get documents bucket name
DOCS_BUCKET=$(terraform output -raw documents_bucket_name 2>/dev/null)

# Get API endpoint
API_ENDPOINT=$(terraform output -raw api_endpoint 2>/dev/null)

# Set region (hardcoded as per your setup)
BEDROCK_REGION="ap-southeast-2"

echo "✅ Knowledge Base Configuration:"
echo "   KB ID: $KB_ID"
echo "   Region: $BEDROCK_REGION"
echo "   Documents Bucket: $DOCS_BUCKET"
echo "   API Endpoint: $API_ENDPOINT"
echo ""

# Export environment variables
export KNOWLEDGE_BASE_ID="$KB_ID"
export BEDROCK_REGION="$BEDROCK_REGION"

echo "✅ Environment variables set:"
echo "   export KNOWLEDGE_BASE_ID=\"$KB_ID\""
echo "   export BEDROCK_REGION=\"$BEDROCK_REGION\""
echo ""

# Create .env file for persistence
cat > .env <<EOF
# Knowledge Base Configuration
KNOWLEDGE_BASE_ID=$KB_ID
BEDROCK_REGION=$BEDROCK_REGION
DOCUMENTS_BUCKET=$DOCS_BUCKET
API_ENDPOINT=$API_ENDPOINT
EOF

echo "✅ Created .env file with configuration"
echo ""
echo "📝 To use these variables in your current shell, run:"
echo "   source setup_kb_env.sh"
echo ""
echo "📝 Or load from .env file:"
echo "   export \$(cat .env | xargs)"
echo ""
echo "🧪 Ready to test! Run:"
echo "   cd src && python ops/test_kb_retrieval.py"
