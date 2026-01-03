"""
ReactAgent - 具有原生 ReAct 循环能力的 Agent 基类

提供标准的 ReAct (Reason + Act) 循环实现，支持：
- 从 config.toml 选择模型
- 自动工具调用和结果处理
- report_status 作为终止信号
- 可配置的最大迭代次数
"""
import json
from typing import Optional, List, Dict, Any

from src.core.capability import BaseAgent
from src.core.config import global_config
from src.core.llm import LLMClient
from src.core.registry import global_registry


class ReactAgent(BaseAgent):
    """
    具有原生 ReAct 循环能力的 Agent 基类
    
    特性：
    - 内置 ReAct 循环，自动处理工具调用
    - 支持从 config.toml 配置模型（通过 model_role 或 model_label）
    - 以 report_status 调用作为任务结束信号
    - 可覆盖 max_iterations 控制循环次数
    
    使用方式：
    1. 继承此类
    2. 设置 name, description, allowed_tools
    3. 可选设置 model_role 或 model_label 来配置模型
    """
    
    # 模型配置：优先使用 model_role，否则使用 model_label
    # model_role: 对应 config.toml 中的 llm.functional_roles.xxx
    # model_label: 直接指定模型标签（如 'v3-2', 'glm'）
    model_role: Optional[str] = None  # e.g., "code_generation", "orchestrator"
    model_label: Optional[str] = None  # e.g., "v3-2", "glm"
    
    # ReAct 循环配置
    max_iterations: int = 10  # 最大迭代次数
    
    def get_model_label(self) -> Optional[str]:
        """
        获取要使用的模型标签
        优先级：model_role -> model_label -> active_model_label
        """
        if self.model_role:
            # 从 functional_roles 获取
            role_label = global_config.get(f"llm.functional_roles.{self.model_role}")
            if role_label:
                return role_label
        
        if self.model_label:
            return self.model_label
        
        # 使用默认激活模型
        return global_config.get("llm.active_model_label")
    
    async def execute(
        self, 
        instruction: str, 
        context: Optional[str] = None,
        upstream_capabilities: Optional[str] = None
    ) -> str:
        """
        标准 ReAct 执行流程：
        1. 构建完整的系统提示
        2. 初始化 LLM 客户端（使用配置的模型）
        3. 执行 ReAct 循环，处理工具调用
        4. 以 report_status 调用结束，返回状态
        """
        language = global_config.get("core.language", "zh")
        
        # 1. 获取模型配置
        target_model_label = self.get_model_label()
        
        # 初始化 LLM 客户端
        if target_model_label:
            print(f"[{self.name}] 使用模型: {target_model_label}")
            client = LLMClient(target_model_label=target_model_label)
        else:
            print(f"[{self.name}] 使用默认模型")
            client = LLMClient()
        
        # 2. 构建完整的系统提示
        full_system_prompt = self.build_full_prompt(
            instruction=instruction,
            context=context or "",
            upstream_capabilities=upstream_capabilities or "",
            language=language
        )
        
        # 3. 准备消息
        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": instruction}
        ]
        
        # 4. 获取工具 Schema
        tools_schemas = self.get_allowed_tool_schemas()
        
        print(f"[{self.name}] 开始执行任务: {instruction[:50]}...")
        print(f"[{self.name}] 可用工具: {', '.join(self.allowed_tools)}")
        
        # 5. ReAct 循环
        for iteration in range(self.max_iterations):
            print(f"[{self.name}] 迭代 {iteration + 1}/{self.max_iterations}")
            
            # 调用 LLM
            response_msg = await client.chat_completion(
                messages=messages,
                tools=tools_schemas,
                tool_choice="auto"
            )
            
            # 检查是否有工具调用
            if response_msg.tool_calls:
                # 将 assistant 消息添加到历史
                messages.append({
                    "role": "assistant",
                    "content": response_msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                        }
                        for tc in response_msg.tool_calls
                    ]
                })
                
                for tool_call in response_msg.tool_calls:
                    function_name = tool_call.function.name
                    
                    # 解析工具参数
                    try:
                        function_args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as e:
                        tool_result = f"[FAILURE] Invalid JSON arguments: {e}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                        continue
                    
                    print(f"[{self.name}] 调用工具: {function_name}")
                    
                    # 执行工具
                    tool_instance = global_registry.get_capability(function_name)
                    if not tool_instance:
                        tool_result = f"[FAILURE] Tool {function_name} not found."
                    else:
                        tool_result = await tool_instance.execute(**function_args)
                    
                    # 添加工具结果到历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })
                    
                    # 检查是否是 report_status 调用 - 这是结束信号
                    if function_name == "report_status":
                        print(f"[{self.name}] 任务完成，状态已报告")
                        return tool_result
            else:
                # 没有工具调用，检查是否有文本回复
                content = response_msg.content or ""
                if content:
                    # LLM 没有调用工具就返回了文本，提示它必须调用 report_status
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user", 
                        "content": "请调用 report_status 工具报告你的任务结果。"
                    })
        
        # 达到最大迭代次数
        return f"[FAILURE] Max iterations ({self.max_iterations}) reached without calling report_status"
