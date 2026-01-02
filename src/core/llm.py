from openai import AsyncOpenAI
from typing import List, Dict, Any, Optional
from src.core.config import global_config

class LLMClient:
    def __init__(self, target_model_label: Optional[str] = None):
        self.target_label = target_model_label
        
        # Initial load
        if self.target_label:
             self.api_base, self.api_key, self.model_name = global_config.get_model_config(self.target_label)
        else:
             self.api_base, self.api_key, self.model_name = global_config.get_llm_config()
             
        self.client = AsyncOpenAI(
            base_url=self.api_base,
            api_key=self.api_key,
        )

    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Any = "auto",
        temperature: float = 0.7,
        response_format: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        stream: bool = False
    ) -> Any:
        """
        client.chat.completions.create 的包装器。
        Wrapper for client.chat.completions.create
        """
        # If no specific target label was set during init, we treat this as the "Global/Active" client
        # and reload config to support dynamic switching.
        if not self.target_label:
            self.api_base, self.api_key, self.model_name = global_config.get_llm_config()
            self.client.base_url = self.api_base
            self.client.api_key = self.api_key
        
        # Use overridden model if provided, else use the configured model
        target_model = model if model else self.model_name

        params = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = tool_choice
        if response_format:
            params["response_format"] = response_format

        response = await self.client.chat.completions.create(**params)
        
        if stream:
            return response
        else:
            return response.choices[0].message


global_llm_client = LLMClient()
