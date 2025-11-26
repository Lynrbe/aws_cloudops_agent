#!/bin/bash
# Script to update Knowledge Base ID in config and redeploy runtime

set -e

echo "🔧 Updating Knowledge Base configuration..."
echo ""

# Get KB ID from Terraform
cd /home/dli2hc/repo/ai_agent

if [ ! -f "terraform.tfstate" ]; then
    echo "❌ Error: terraform.tfstate not found"
    echo "Please deploy Terraform infrastructure first"
    exit 1
fi

KB_ID=$(terraform output -raw knowledge_base_id 2>/dev/null)

if [ -z "$KB_ID" ] || [ "$KB_ID" == "null" ]; then
    echo "❌ Error: Could not get Knowledge Base ID from Terraform"
    echo "Please make sure Terraform is deployed and KB is created"
    exit 1
fi

echo "✅ Found Knowledge Base ID: $KB_ID"
echo ""

# Update static-config.yaml
CONFIG_FILE="config/static-config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: $CONFIG_FILE not found"
    exit 1
fi

# Use sed to update the KB ID
echo "📝 Updating $CONFIG_FILE..."
sed -i "s/^  id: \"\".*$/  id: \"$KB_ID\"/" "$CONFIG_FILE"

# Verify the update
if grep -q "id: \"$KB_ID\"" "$CONFIG_FILE"; then
    echo "✅ Configuration updated successfully!"
    echo ""
    echo "Updated configuration:"
    grep -A 2 "^knowledge_base:" "$CONFIG_FILE"
else
    echo "❌ Error: Failed to update configuration"
    exit 1
fi

echo ""
echo "🚀 Ready to redeploy runtime with KB tools!"
echo ""
echo "Next steps:"
echo "1. Make sure your Docker image includes the KB tools"
echo "2. Build and push Docker image:"
echo "   cd /home/dli2hc/repo/ai_agent"
echo "   # Build your Docker image with updated code"
echo ""
echo "3. Deploy runtime:"
echo "   cd src"
echo "   python ops/deploy_runtime.py"
echo ""
echo "4. Test with:"
echo "   python ops/invoke_agent_jwt.py"
echo "   Then ask: 'search the knowledge base for AWS Lambda'"
