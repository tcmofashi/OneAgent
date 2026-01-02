import json
from typing import Optional
from src.core.capability import BaseAgent
from src.core.config import global_config
from src.core.llm import LLMClient
from src.core.registry import global_registry


class HelloWorldAgent(BaseAgent):
    """
    标准子 Agent 示例：Hello World Agent
    
    遵循标准子 Agent 工作流：
    - 输入：instruction, context, upstream_capabilities
    - 工具：greeting_tool, report_status
    - 输出：通过 report_status 结束执行
    """
    name = "hello_world_agent"
    description = "A simple agent that receives greetings and responds with a verified message. Demonstrates the standard sub-agent workflow."
    
    # 子 Agent 可自定义的专属提示
    system_prompt = """
你擅长处理问候相关的任务。
当收到问候请求时，使用 greeting_tool 生成正式回复。
完成后，必须调用 report_status 报告结果。
"""
    
    # 允许使用的工具列表（必须包含 report_status）
    allowed_tools = ["greeting_tool", "report_status"]
    
    async def execute(
        self, 
        instruction: str, 
        context: Optional[str] = None,
        upstream_capabilities: Optional[str] = None
    ) -> str:
        """
        标准子 Agent 执行流程：
        1. 构建完整的系统提示（标准模板 + 自定义提示）
        2. 执行 LLM 循环，允许调用工具
        3. 以 report_status 调用结束，返回状态
        """
        client = LLMClient()
        language = global_config.get("core.language", "zh")
        
        # 1. 构建完整的系统提示
        full_system_prompt = self.build_full_prompt(
            context=context or "",
            upstream_capabilities=upstream_capabilities or "",
            language=language
        )
        
        # 2. 准备消息
        messages = [
            {"role": "system", "content": full_system_prompt},
            {"role": "user", "content": f"任务指令: {instruction}"}
        ]
        
        # 3. 获取工具 Schema
        tools_schemas = self.get_allowed_tool_schemas()
        
        print(f"[{self.name}] 开始执行任务: {instruction[:50]}...")
        
        # 4. ReAct 循环
        max_iterations = 5
        for iteration in range(max_iterations):
            print(f"[{self.name}] 迭代 {iteration + 1}/{max_iterations}")
            
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
                    function_args = json.loads(tool_call.function.arguments)
                    
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
        return "[FAILURE] Max iterations reached without calling report_status"
