from strands.agent.conversation_manager import SummarizingConversationManager

class CountingSCM(SummarizingConversationManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.summarize_count = 0
    def reduce_context(self, *args, **kwargs):
        self.summarize_count += 1
        return super().reduce_context(*args, **kwargs)

def build_conversation_manager(cfg) -> SummarizingConversationManager:
    """
    cfg: dict từ utils.config_manager.load_config()
    schema gợi ý:
      conversation_manager:
        type: summarizing
        summary_ratio: 0.3
        preserve_recent_messages: 10
        summarization_prompt: "..."  # hoặc đường dẫn file
        summarization_model_id: null  # nếu muốn model rẻ hơn cho summarize
    """
    cm_cfg = (cfg or {}).get("conversation_manager", {})
    ratio = cm_cfg.get("summary_ratio", 0.3)
    preserve = cm_cfg.get("preserve_recent_messages", 10)
    prompt = cm_cfg.get("summarization_prompt", "").strip()

    # nếu bạn có summarization_agent riêng, khởi tạo ở đây (tùy nhu cầu)
    kwargs = {
        "summary_ratio": ratio,
        "preserve_recent_messages": preserve,
    }
    if prompt:
        kwargs["summarization_system_prompt"] = prompt

    return CountingSCM(**kwargs)
