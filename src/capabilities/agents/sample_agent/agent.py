from typing import Optional
from src.core.capability import BaseAgent
from src.core.config import global_config

class SampleAgent(BaseAgent):
    name = "sample_agent"
    description = "A sample agent to demonstrate the directory-based structure."
    
    # Local bilingual system prompts
    SYSTEM_PROMPTS = {
        "zh": "你是一个乐于助人的示例 Agent。你可以使用你指定的工具。",
        "en": "You are a helpful sample agent. You can use your specific tools."
    }

    # 我们使用属性或 init 来获取动态 Prompt
    # We use a property or init to get the dynamic prompt
    @property
    def system_prompt(self):
        lang = global_config.get("core.language", "en")
        return self.SYSTEM_PROMPTS.get(lang, self.SYSTEM_PROMPTS["en"])
    
    async def execute(self, instruction: str, context: Optional[str] = None) -> str:
        # 在真实的 Agent 中，这将涉及 LLM 调用或复杂的逻辑。
        # In a real agent, this would involve LLM calls or complex logic.
        # 在这里我们只是为了演示而进行回显。
        # Here we just echo for demonstration.
        context_msg = f" with context: {context}" if context else ""
        return f"[SampleAgent] Processed instruction: '{instruction}'{context_msg}. Tools available: {self.allowed_tools}. System Prompt: {self.system_prompt[:20]}..."
