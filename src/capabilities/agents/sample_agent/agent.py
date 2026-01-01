from typing import Optional
from src.core.capability import BaseAgent

class SampleAgent(BaseAgent):
    name = "sample_agent"
    description = "A sample agent to demonstrate the directory-based structure."
    system_prompt = "You are a helpful sample agent. You can use your specific tools."
    
    async def execute(self, instruction: str, context: Optional[str] = None) -> str:
        # In a real agent, this would involve LLM calls or complex logic.
        # Here we just echo for demonstration.
        context_msg = f" with context: {context}" if context else ""
        return f"[SampleAgent] Processed instruction: '{instruction}'{context_msg}. Tools available: {self.allowed_tools}"
