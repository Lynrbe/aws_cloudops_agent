from strands import Agent
from strands.models import BedrockModel
from strands_tools import use_aws
from strands.agent.conversation_manager import SummarizingConversationManager
from strands_tools import calculator

class AwsCloudOpsAgent:
    def __init__(self):

        # Initialize Bedrock model with Claude 4 Sonnet
        self.model = BedrockModel(
            model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        )

        # Create the summarizing conversation manager with default settings
        self.conversation_manager = SummarizingConversationManager(
            summary_ratio=0.3,  # Summarize 30% of messages when context reduction is needed
            preserve_recent_messages=10,  # Always keep 10 most recent messages
            summarization_system_prompt=self._get_summarization_prompt()
        ) 

        # Initialize the agent with AWS tools
        self.agent = Agent(
            model=self.model,
            tools=[use_aws],
            system_prompt=self._get_system_prompt(),
            conversation_manager=self.conversation_manager,
        )

    def _get_summarization_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """
        You are summarizing an AWS CloudOps conversation. Produce concise bullet points that:
        - Keep service names, regions, ARNs, resource IDs, CLI/SDK commands, key parameters and exit codes
        - Preserve architecture decisions, trade-offs, and cost/security implications
        - Capture tool usage/results pairs (tool name → key result)
        - Omit chit-chat; focus on actions, findings, and next steps
        Format as bullet points only.
        """
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """
        You are an AWS CloudOps Agent, a friendly and knowledgeable assistant specializing in AWS cloud operations.
        
        Your capabilities:
        - Retrieve information about AWS services and resources
        - Provide architecture solutions based on user scenarios
        - Offer best practices and recommendations
        - Help troubleshoot AWS-related issues

        Guidelines:
        - Provide clear, concise explanations suitable for beginners
        - When suggesting architectures, explain the reasoning behind service choices
        - Always consider cost-effectiveness and security best practices
        - Use the use_aws tool to interact with AWS services when needed
        
        Response format:
        - Use bullet points for clarity
        - Include practical examples when possible
        - End with helpful next steps or recommendations
        """
    
    def chat(self, message: str):
        """Process user message and return response"""
        try:
            result = self.agent(message)
            return result
        
        except Exception as e:
            return f"Sorry, I encountered an error: {e}"
        
    async def stream(self, message: str):
        """Process user message and return response"""
        try:
            async for event in self.agent.stream_async(message):
                if "data" in event:
                    # Only stream text chunks to the client
                    yield event["data"]

        except Exception as e:
            yield f"Sorry, I encountered an error: {str(e)}"


def main():
    """Main interactive loop"""
    agent = AwsCloudOpsAgent()


if __name__ == "__main__":
    main()
