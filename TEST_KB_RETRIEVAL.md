# Knowledge Base Retrieval Testing Guide

This guide shows you how to test the integrated Knowledge Base retrieval functionality in your AWS CloudOps Agent runtime.

## Prerequisites

1. **Deploy Infrastructure**: Make sure your Terraform infrastructure is deployed
2. **Upload Documents**: Upload some test documents to your S3 documents bucket
3. **Run Ingestion**: Trigger the ingestion Lambda to index documents in the Knowledge Base

## Step 1: Get Your Knowledge Base ID

Get the Knowledge Base ID from Terraform outputs:

```bash
cd /home/dli2hc/repo/ai_agent
terraform output -raw knowledge_base_id
```

Or from AWS Console:
1. Go to Amazon Bedrock Console
2. Navigate to Knowledge Bases
3. Copy your Knowledge Base ID

## Step 2: Set Environment Variables

Set the required environment variables:

```bash
# Export Knowledge Base ID (replace with your actual ID)
export KNOWLEDGE_BASE_ID="your-kb-id-from-terraform-output"

# Export Bedrock region (where your KB and OpenSearch are)
export BEDROCK_REGION="ap-southeast-2"
```

## Step 3: Run the Test Script

Run the automated test suite:

```bash
cd /home/dli2hc/repo/ai_agent/src
python ops/test_kb_retrieval.py
```

This will run 3 tests:
1. **Direct Tool Call**: Tests the KB retrieval tools directly
2. **Agent Integration**: Tests the agent using KB tools (non-streaming)
3. **Streaming Integration**: Tests streaming responses with KB tools

## Step 4: Test with Full Agent Runtime

### Option A: Test Locally

1. **Start the agent runtime**:
   ```bash
   cd /home/dli2hc/repo/ai_agent/src

   # Make sure environment variables are set
   export KNOWLEDGE_BASE_ID="your-kb-id"
   export BEDROCK_REGION="ap-southeast-2"

   # Start the runtime
   python agent_runtime.py
   ```

2. **In another terminal, test with curl**:
   ```bash
   curl -X POST http://localhost:8080/invocations \
     -H "Content-Type: application/json" \
     -d '{
       "prompt": "Search the knowledge base for AWS Lambda information",
       "session_id": "test-session",
       "actor_id": "test-user"
     }'
   ```

### Option B: Test with JWT Client (if deployed to AWS)

If you've deployed your runtime to AWS with JWT authentication:

```bash
cd /home/dli2hc/repo/ai_agent/src

# Make sure your config has the runtime ARN
python ops/invoke_agent_jwt.py
```

Then try queries like:
- `"Search the knowledge base for AWS Lambda"`
- `"What documentation do we have about S3?"`
- `"Quick search for VPC configuration"`

## Step 5: Test via API Gateway (Direct Lambda)

You can also test the standalone retrieve Lambda via API Gateway:

```bash
# Get your API endpoint
cd /home/dli2hc/repo/ai_agent
API_ENDPOINT=$(terraform output -raw api_endpoint)

# Test the retrieve endpoint
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AWS Lambda",
    "max_results": 3
  }'
```

## Expected Results

### Successful Test Output

When tests pass, you should see:

```
✅ PASSED: Direct Tool Call
✅ PASSED: Agent Integration
✅ PASSED: Streaming Integration
```

### Example Agent Response

When the agent uses KB retrieval, you'll see:

```
🔍 Searching the knowledge base for AWS Lambda information...
✅ Found 3 relevant documents about AWS Lambda

📄 Document 1 (Relevance Score: 0.8542)
📍 Source: s3://your-bucket/lambda-guide.pdf
📝 Content:
AWS Lambda is a serverless compute service that lets you run code without provisioning or managing servers...
```

## Troubleshooting

### Error: "KNOWLEDGE_BASE_ID not set"
- Make sure you exported the environment variable
- Check with: `echo $KNOWLEDGE_BASE_ID`

### Error: "No documents found"
- Make sure you've uploaded documents to the S3 documents bucket
- Run the ingestion Lambda to index documents
- Wait a few minutes for indexing to complete

### Error: "The specified knowledge base does not exist"
- Verify your Knowledge Base ID is correct
- Check the region matches where your KB was created
- Run: `aws bedrock-agent list-knowledge-bases --region ap-southeast-2`

### Error: "Access Denied"
- Check your IAM permissions
- Make sure your Lambda execution role has `bedrock:Retrieve` permission
- Verify the runtime has access to Bedrock Agent Runtime

## Sample Test Queries

Try these queries with your agent:

1. **Documentation Search**:
   - "Search the knowledge base for AWS Lambda best practices"
   - "What documentation do we have about S3 security?"
   - "Find information about VPC networking"

2. **Quick Lookups**:
   - "Quick search for IAM roles"
   - "Look up CloudFormation syntax"

3. **Combined Queries** (uses both AWS tools and KB retrieval):
   - "Search the KB for Lambda info, then list my Lambda functions"
   - "Find our S3 documentation and show me my buckets"

## Verify Integration

To verify the tools are properly integrated:

1. Check agent runtime logs for:
   ```
   🛠️ Total tools available: X (searched: Y, local: 6)
   ```
   Should show 6 local tools (including the 2 KB retrieval tools)

2. When agent uses KB tools, logs should show:
   ```
   🔍 Retrieving from KB: your-kb-id in ap-southeast-2
   ✅ Found N relevant documents
   ```

## Next Steps

Once testing is successful:

1. **Deploy to Production**: Deploy your agent runtime with the KB tools
2. **Add More Documents**: Upload more documentation to improve KB coverage
3. **Monitor Usage**: Track which queries use KB retrieval vs AWS tools
4. **Optimize Prompts**: Update agent prompts based on usage patterns
