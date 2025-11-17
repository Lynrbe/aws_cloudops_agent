# 🚀 AWS CloudOps Agent

A beginner-friendly AWS operations agent built with AWS Strands Agent SDK and  Amazon Bedrock Claude 4 Sonnet.

## ✨ Features

- 📊 **AWS Resource Discovery**: Query your AWS resources and services
- 🏗️ **Architecture Design**: Get architecture recommendations based on your scenarios
- 💡 **Best Practices**: Receive AWS best practices and security recommendations
- 🔍 **Troubleshooting**: Get help with AWS-related issues
- 🎨 **User-Friendly Interface**: Rich console interface with emojis and visual indicators

## 🏛️ Initial Architecture

![AWS CloudOps Agent Architecture](docs/aws-strands-agent.drawio.svg)

## 🛠️ Setup

### Prerequisites

- Python 3.11+
- AWS CLI configured with appropriate credentials
- uv package manager
- Docker

### Installation

1. Clone or navigate to the project directory:

```bash
cd C:\\ws\\aws-cloudops-agent

```

2. Install dependencies:

```bash
uv sync

```

3. Configure AWS credentials:

```bash
aws configure

```

## 🚀 Usage

### Option 1: CLI Mode

Run the agent in interactive CLI mode:

```bash
uv run src\agent_cli.py
```

### Option 2: AgentCore Local Testing

Run with Bedrock AgentCore toolkit for local testing:

```bash
# Start the agent server
uv run src\agent_streaming.py

# In another terminal, test with curl
curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d "{\"prompt\": \"Hello!\"}"

# Or use the test scripts
uv run src\test_agent_local.py  # Python test
.\test_local.ps1                # PowerShell test
.\test_local.bat                # Batch test
```

### Option 3: Deploy to AWS AgentCore

```bash
# Quick deploy with script
.\deploy.ps1                    # PowerShell
.\deploy.bat                    # Batch

# Or manual deployment
pip install bedrock-agentcore-starter-toolkit
agentcore configure --entrypoint src/agent_streaming.py --non-interactive
agentcore launch

# Invoke deployed agent
agentcore invoke '{"prompt": "Hello from AWS!"}'

# Check status
agentcore status
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed deployment instructions.  
See [LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md) for local testing.

### Example Interactions

**Resource Discovery:**

```sh
You: Show me my EC2 instances
Agent: 📊 Here are your EC2 instances...

```

**Architecture Design:**

```ini
You: Design a web app architecture for high availability
Agent: 🏗️ For a highly available web application, I recommend...

```

**Best Practices:**

```yaml
You: What's the best way to store user data securely?
Agent: 🔒 For secure user data storage, consider these options...

```

## 📁 Project Structure

```ini
aws-cloudops-agent/
├── src/
│   ├── agent_cli.py                    # CLI entry point
│   ├── agent_streaming.py              # AgentCore streaming wrapper
│   ├── agent_fastapi.py                # FastAPI web interface
│   ├── aws_cloudops_agent.py           # Main agent implementation
│   ├── test_agent_local.py             # Local testing script
│   ├── deploy_agent.py                 # Agent deployment utilities
│   └── invoke_agent.py                 # Agent invocation utilities
├── assets/
│   ├── AgentRuntimeRole.json           # AWS IAM role configuration
│   ├── assume-role-policy.json         # Role assumption policy
│   ├── simple-trust-policy.json        # Simple trust policy
│   └── trust-policy.json               # Trust policy configuration
├── docs/
│   ├── AWS-CloudOps-Agent.pptx         # Presentation
│   ├── aws-strands-agent.drawio        # Architecture diagram
│   ├── aws-strands-agent.drawio.svg    # Architecture diagram (SVG)
│   └── ROADMAP.md                      # Project roadmap
├── dockerfile                          # Docker configuration
├── deploy.ps1                          # PowerShell deployment script
├── deploy.bat                          # Batch deployment script
├── test_local.ps1                      # PowerShell test script
├── test_local.bat                      # Batch test script
├── DEPLOYMENT_GUIDE.md                 # Deployment guide
├── LOCAL_TESTING_GUIDE.md              # Local testing guide
├── QUICK_START.md                      # Quick start reference
├── pyproject.toml                      # Project configuration
├── requirements.txt                    # Dependencies
├── uv.lock                             # Dependency lock file
└── README.md                           # This file
```

## 📖 Documentation

### 🎯 Start Here
- **[GETTING_STARTED.md](GETTING_STARTED.md)** - Complete beginner's guide (start here!)
- **[QUICK_START.md](QUICK_START.md)** - Fast reference for common commands

### 🚀 Deployment
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment instructions
- **[DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)** - Overview and quick reference
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Track your deployment progress
- **[docs/DEPLOYMENT_ARCHITECTURE.md](docs/DEPLOYMENT_ARCHITECTURE.md)** - Architecture diagrams

### 🧪 Testing & Troubleshooting
- **[LOCAL_TESTING_GUIDE.md](LOCAL_TESTING_GUIDE.md)** - Local testing instructions
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

## 🤝 Contributing

This is a minimal implementation focused on simplicity and user experience. Feel free to extend with additional features!

## 📝 License

MIT License - feel free to use and modify as needed.