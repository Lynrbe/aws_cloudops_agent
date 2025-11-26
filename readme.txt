How to Fix It
Step 1: Update KB Config
cd /home/dli2hc/repo/ai_agent
./update_kb_config.sh
This will:
Get your KB ID from Terraform
Update config/static-config.yaml with the KB ID
Step 2: Rebuild & Push Docker Image Your runtime runs in a Docker container, so you need to rebuild it with the new KB tools:
# Build Docker image (check your Dockerfile location)
docker build -t your-ecr-repo/aws-cloudops-agent:latest .

# Push to ECR
docker push your-ecr-repo/aws-cloudops-agent:latest
Step 3: Redeploy Runtime
cd src
python ops/deploy_runtime.py
This will:
Update the runtime with new Docker image
Set KNOWLEDGE_BASE_ID and BEDROCK_REGION environment variables
Make KB tools available to the agent
Step 4: Test
python ops/invoke_agent_jwt.py
Then ask: "search the knowledge base for AWS Lambda" The agent should now use the retrieve_from_knowledge_base tool!