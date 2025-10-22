from strands import Agent
from strands.models import BedrockModel
from strands_tools import use_aws
from strands.agent.conversation_manager import SummarizingConversationManager
import time
import asyncio # Cần cho việc chạy stream

class AwsCloudOpsAgent:
    def __init__(self):

        # 1. Khởi tạo Model
        self.model = BedrockModel(
            model_id="apac.anthropic.claude-sonnet-4-20250514-v1:0",
        )

        # 2. Khởi tạo Summarizing Conversation Manager (SCM)
        self.conversation_manager = SummarizingConversationManager(
            summary_ratio=0.3,          # Summarize 30% of messages when context reduction is needed
            preserve_recent_messages=6,  # Always keep 6 most recent messages
            # Cải thiện 1: Thêm .strip() cho prompt
            summarization_system_prompt=self._get_summarization_prompt().strip(),
        ) 

        # 3. Khởi tạo Agent
        self.agent = Agent(
            model=self.model,
            # Cải thiện 2: Chỉ giữ tools cần thiết
            tools=[use_aws],
            # Cải thiện 1: Thêm .strip() cho prompt
            system_prompt=self._get_system_prompt().strip(),
            conversation_manager=self.conversation_manager,
        )

         # --- Metrics Tổng cộng dồn (Cải thiện 3) ---
        self.total_tokens = 0
        self.total_turns = 0
        self.overflow_events = 0       
        self.summarize_invocations = 0 

        # --- State Trackers cho Metrics Delta ---
        self._last_stream_usage = None
        self._last_overflow_count = 0
        self._last_summarize_count = 0


    def _get_summarization_prompt(self) -> str:
        # ... (giữ nguyên nội dung) ...
        return """
        You are summarizing an AWS CloudOps conversation. Produce concise bullet points that:
        - Keep service names, regions, ARNs, resource IDs, CLI/SDK commands, key parameters and exit codes
        - Preserve architecture decisions, trade-offs, and cost/security implications
        - Capture tool usage/results pairs (tool name → key result)
        - Omit chit-chat; focus on actions, findings, and next steps
        Format as bullet points only.
        """
    
    def _get_system_prompt(self) -> str:
        # ... (giữ nguyên nội dung) ...
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
    
    # Thêm các hàm helper cho Metrics (Cải thiện 3)
    def _pick_tokens_from_usage(self, u):
        if u is None: return 0, 0
        if isinstance(u, dict):
            it = u.get("input_tokens") or u.get("inputTokens")
            ot = u.get("output_tokens") or u.get("outputTokens")
            return int(it or 0), int(ot or 0)
        it = getattr(u, "input_tokens", 0) or getattr(u, "inputTokens", 0)
        ot = getattr(u, "output_tokens", 0) or getattr(u, "outputTokens", 0)
        return int(it or 0), int(ot or 0)

    def _extract_usage_tokens(self, result):
        usage = getattr(result, "usage", None)
        it, ot = self._pick_tokens_from_usage(usage)
        if (it == 0 and ot == 0) and hasattr(result, "response"):
            resp = getattr(result, "response", None)
            if isinstance(resp, dict) and "usage" in resp:
                i2, o2 = self._pick_tokens_from_usage(resp.get("usage"))
                it, ot = (i2 or it), (o2 or ot)
        if it == 0 and ot == 0 and self._last_stream_usage:
            it, ot = self._pick_tokens_from_usage(self._last_stream_usage)
        return it, ot
    
    def _update_scm_metrics(self, latency: float, it: int, ot: int, result=None):
        self.total_turns += 1
        cm = self.conversation_manager
        
        current_overflow = getattr(cm, "overflow_count", self._last_overflow_count)
        current_summarize = getattr(cm, "summarize_count", self._last_summarize_count)
        
        ov_delta = current_overflow - self._last_overflow_count
        sv_delta = current_summarize - self._last_summarize_count
        
        self.overflow_events += ov_delta
        self.summarize_invocations += sv_delta
        
        self._last_overflow_count = current_overflow
        self._last_summarize_count = current_summarize

        print(
            f"[METRIC] turn={self.total_turns} tokens+={it}/{ot} "
            f"latency={latency:.2f}s overflow_delta={ov_delta} summarize_delta={sv_delta}"
        )


    def chat(self, message: str):
        """Process user message and return response (Blocking)"""
        t0 = time.time()
        try:
            result = self.agent(message)
        except Exception as e:
            return f"Sorry, I encountered an error: {e}"
        
        t1 = time.time()
        it, ot = self._extract_usage_tokens(result)
        self.total_tokens += (it + ot)
        
        # Cập nhật metrics
        self._update_scm_metrics(latency=(t1 - t0), it=it, ot=ot, result=result)
        
        return result
        
    async def stream(self, message: str):
        """Process user message and return response (Streaming)"""
        t0 = time.time()
        self._last_stream_usage = None # Reset usage tracker
        
        try:
            async for event in self.agent.stream_async(message):
                # Cải thiện 4: Xử lý stream event chi tiết hơn
                data = getattr(event, "data", None) or event.get("data")
                if isinstance(data, str):
                    yield data
                    
                # Gom usage khi kết thúc
                ev_type = getattr(event, "type", None) or event.get("type")
                meta = getattr(event, "metadata", None) or event.get("metadata")
                if ev_type in ("message_stop", "response_completed", "messageStop") and isinstance(meta, dict):
                    if "usage" in meta:
                        self._last_stream_usage = meta["usage"]

            t1 = time.time()
            it, ot = self._pick_tokens_from_usage(self._last_stream_usage)
            self.total_tokens += (it + ot)
            
            # Cập nhật metrics
            self._update_scm_metrics(latency=(t1 - t0), it=it, ot=ot, result=None)

        except Exception as e:
            yield f"\nSorry, I encountered an error: {str(e)}"
            t1 = time.time()
            self._update_scm_metrics(latency=(t1 - t0), it=0, ot=0, result=None)
            return


def main():
    agent = AwsCloudOpsAgent()
        
if __name__ == "__main__":
    main()