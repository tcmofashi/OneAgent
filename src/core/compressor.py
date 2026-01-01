from typing import List, Dict, Any
from src.core.llm import LLMClient
from src.core.config import global_config

COMPRESSION_PROMPT = """You are an expert Context Compressor.
Your goal is to distill a long conversation history and a specific new task into a concise "Context Briefing" for a subordinate Agent.

# Inputs
1. **Target Agent Profile**: Credentials and capabilities of the Agent who will receive this task.
2. **Orchestrator Plan**: The current high-level plan and the specific task being assigned.
3. **Full History**: The complete conversation history so far (User inputs + Orchestrator thoughts).

# Your Strategy
- **Analyze Intent**: Understand what the User wants and how this specific task fits into the Orchestrator's plan.
- **Filter Relevancy**: The Target Agent ONLY needs information relevant to its specific job. Remove everything else.
- **Formulate Request**: Rewrite the task into a clear, self-contained instruction that aligns with the Agent's capabilities.

# Output Format (JSON)
{
  "core_request": "The specific, actionable instruction for the agent. Must be clear and unambiguous.",
  "compressed_context": "A summary of relevant background info (e.g., file paths, restrictions, previous errors) necessary for THIS agent to succeed."
}
"""

class ContextCompressor:
    def __init__(self):
        from src.core.config import global_config
        
        # Try to get specialized model label from config
        compressor_label = global_config.get("llm.functional_roles.compressor")
        
        if compressor_label:
            print(f"[Compressor] Using specialized model: {compressor_label}")
            self.llm_client = LLMClient(target_model_label=compressor_label)
        else:
            print("[Compressor] Using default global model")
            self.llm_client = LLMClient() 
        
    async def compress(
        self, 
        history: List[Dict[str, Any]], 
        target_task: str, 
        agent_description: str,
        orchestrator_plan: str
    ) -> Dict[str, str]:
        """
        Compresses context based on:
        - history: The conversation so far.
        - target_task: What needs to be done now.
        - agent_description: Who is doing it (Capabilities).
        - orchestrator_plan: The bigger picture (Task List).
        """
        user_content = f"""## 1. Target Agent Profile
{agent_description}

## 2. Orchestrator Plan
{orchestrator_plan}

## 3. Specific Task for this Agent
{target_task}

## 4. Full History
{str(history)}
"""
        messages = [
            {"role": "system", "content": COMPRESSION_PROMPT},
            {"role": "user", "content": user_content}
        ]
        
        response = await self.llm_client.chat_completion(
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        try:
            import json
            result = json.loads(response.content)
            return result
        except Exception as e:
            print(f"[Compressor] Error parsing JSON: {e}")
            return {
                "core_request": target_task,
                "compressed_context": "Context compression failed. Proceed with caution."
            }

global_compressor = ContextCompressor()
