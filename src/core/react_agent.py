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

import sys
from types import SimpleNamespace
from src.core.capability import BaseAgent
from src.core.config import global_config
from src.core.llm import LLMClient
from src.core.registry import global_registry
from src.utils.context_compressor import compress_context, should_compress


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
    
    def __init__(self):
        super().__init__()
        self.chat_history: List[Dict[str, Any]] = []

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
        
        # 3. 准备/恢复消息历史
        if not self.chat_history:
            # 新任务：初始化历史
            self.chat_history = [
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": instruction}
            ]
        else:
            # 恢复任务：追加新指令
            print(f"[{self.name}] 恢复上下文 (历史长度: {len(self.chat_history)})")
            # 可选：更新 System Prompt 以反映最新的 Context/Capabilities (如果需要)
            if self.chat_history[0]["role"] == "system":
                self.chat_history[0]["content"] = full_system_prompt
            
            self.chat_history.append({"role": "user", "content": instruction})
        
        # 使用 self.chat_history 作为当前会话消息
        messages = self.chat_history

        # 4. 获取工具 Schema
        tools_schemas = self.get_allowed_tool_schemas()
        
        # 确保 report_status 工具始终可用 (这是 Agent 结束任务的唯一方式)
        # Check if report_status is already in schemas
        has_report_status = any(t["function"]["name"] == "report_status" for t in tools_schemas)
        if not has_report_status:
            # Manually retrieve it from global registry
            rs_tool = global_registry.get_capability("report_status")
            if rs_tool:
                tools_schemas.append(rs_tool.to_function_schema())
                print(f"[{self.name}] 自动注入 report_status 工具")
            else:
                print(f"[{self.name}] 警告: 系统中未找到 report_status 工具！")
        
        print(f"[{self.name}] 开始执行任务: {instruction[:50]}...")
        print(f"[{self.name}] 可用工具: {', '.join(self.allowed_tools)}")
        
        # 5. ReAct 循环
        for iteration in range(self.max_iterations):
            print(f"[{self.name}] 迭代 {iteration + 1}/{self.max_iterations}")
            
            # 上下文压缩检查
            if await should_compress(messages):
                messages = await compress_context(messages, keep_turns=5, agent_name=self.name)
            
            # 调用 LLM (启用流式输出)
            print(f"[{self.name}] 思考过程: ", end="", flush=True)
            
            full_content = ""
            tool_calls_dict = {}
            
            stream = await client.chat_completion(
                messages=messages,
                tools=tools_schemas,
                tool_choice="auto",  # Let model decide when to call tools
                stream=True
            )
            
            async for chunk in stream:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                # 处理思考内容 (DeepSeek-R1/Qwen-Thinking style)
                if hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                    print(delta.reasoning_content, end="", flush=True)
                    full_content += delta.reasoning_content

                # 处理常规文本内容 (实时打印)
                if delta.content:
                    print(delta.content, end="", flush=True)
                    full_content += delta.content
                
                # 处理工具调用 (累积)
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        if idx not in tool_calls_dict:
                            tool_calls_dict[idx] = {
                                "id": "", 
                                "function": {"name": "", "arguments": ""}
                            }
                        
                        tc_data = tool_calls_dict[idx]
                        if tc_chunk.id:
                            tc_data["id"] += tc_chunk.id
                        if tc_chunk.function:
                            if tc_chunk.function.name:
                                tc_data["function"]["name"] += tc_chunk.function.name
                            if tc_chunk.function.arguments:
                                tc_data["function"]["arguments"] += tc_chunk.function.arguments
            
            print("") # 思考结束换行
            
            # 重构 response_msg 对象以兼容现有逻辑
            tool_calls = []
            for idx in sorted(tool_calls_dict.keys()):
                tc_data = tool_calls_dict[idx]
                # 使用 SimpleNamespace 模拟对象结构
                tc_obj = SimpleNamespace(
                    id=tc_data["id"],
                    function=SimpleNamespace(
                        name=tc_data["function"]["name"],
                        arguments=tc_data["function"]["arguments"]
                    )
                )
                tool_calls.append(tc_obj)
            
            response_msg = SimpleNamespace(
                content=full_content,
                tool_calls=tool_calls if tool_calls else None
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
                    # 清理 Ali DashScope 流式返回的末尾 {} 问题
                    raw_args = tool_call.function.arguments
                    cleaned_args = raw_args.strip()
                    while cleaned_args.endswith("{}"):
                        cleaned_args = cleaned_args[:-2].strip()
                    
                    try:
                        function_args = json.loads(cleaned_args)
                    except json.JSONDecodeError as e:
                        tool_result = f"[FAILURE] Invalid JSON arguments: {e}. Raw: {raw_args[:100]}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": tool_result
                        })
                        continue
                    
                    print(f"[{self.name}] 调用工具: {function_name}")
                    
                    # 执行工具
                    # 优先查找私有工具，然后是全局注册表
                    tool_instance = self._private_tools.get(function_name) or global_registry.get_capability(function_name)
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
                        # 检查状态，决定是否清理历史
                        status = function_args.get("status", "").upper()
                        if status in ["SUCCESS", "FAILURE", "REJECTED"]:
                            print(f"[{self.name}] 终态 ({status})，清理上下文")
                            self.chat_history = []
                        elif status == "INTERRUPTED":
                            print(f"[{self.name}] 中断状态 (INTERRUPTED)，保留上下文")
                            # 保持 self.chat_history 不变
                        
                        return tool_result
            else:
                # 没有工具调用，检查是否有文本回复
                content = response_msg.content or ""
                if content.strip():
                    # LLM 没有调用工具就返回了文本，提示它必须调用工具
                    messages.append({"role": "assistant", "content": content})
                    messages.append({
                        "role": "user", 
                        "content": "请调用工具来执行下一步操作。"
                    })
                else:
                    # 空响应（无内容，无工具调用）- 这可能是模型问题，提示它
                    print(f"[{self.name}] 警告: 模型返回空响应，尝试提示...")
                    messages.append({
                        "role": "user",
                        "content": "请调用工具来继续执行任务。"
                    })
        
        # 达到最大迭代次数
        print(f"[{self.name}] 达到最大迭代次数，清理上下文")
        self.chat_history = [] # 异常结束也清理，避免坏死循环
        return f"[FAILURE] Max iterations ({self.max_iterations}) reached without calling report_status"
