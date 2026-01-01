from typing import List, Dict, Any
from src.core.llm import LLMClient
from src.core.config import global_config

from src.core.templates import get_template

# Removed hardcoded COMPRESSION_PROMPT

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
        orchestrator_plan: str,
        upstream_tools: str = ""
    ) -> Dict[str, str]:
        """
        基于以下内容压缩上下文：
        - history: 迄今为止的对话。
        - target_task: 现在需要做什么。
        - agent_description: 谁在做 (能力)。
        - orchestrator_plan: 大局 (任务列表)。
        - upstream_tools: 上级可用能力 (只读)。
        
        Compresses context based on:
        - history: The conversation so far.
        - target_task: What needs to be done now.
        - agent_description: Who is doing it (Capabilities).
        - orchestrator_plan: The bigger picture (Task List).
        - upstream_tools: Read-only upstream capabilities to inform the agent.
        """
        # Get dynamic system prompt
        system_prompt = get_template("COMPRESSOR_SYSTEM")
        
        user_content = f"""## 1. Target Agent Profile
{agent_description}

## 2. Orchestrator Plan
{orchestrator_plan}

## 3. Specific Task for this Agent
{target_task}

## 4. Full History
{str(history)}

## 5. Upstream Capabilities (Read-Only)
{upstream_tools}
"""
        messages = [
            {"role": "system", "content": system_prompt},
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
