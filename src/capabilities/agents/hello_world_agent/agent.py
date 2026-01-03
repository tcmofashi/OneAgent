"""
Hello World Agent - 标准子 Agent 示例

继承自 ReactAgent，演示如何使用 ReAct 基类快速创建子 Agent。
只需定义 name, description, allowed_tools 即可获得完整的 ReAct 能力。
"""
from src.core.react_agent import ReactAgent


class HelloWorldAgent(ReactAgent):
    """
    标准子 Agent 示例：Hello World Agent
    
    继承自 ReactAgent，自动获得：
    - ReAct 循环能力
    - 工具调用处理
    - report_status 结束信号
    
    只需定义：
    - name: Agent 名称
    - description: Agent 描述
    - allowed_tools: 允许使用的工具列表
    - model_role (可选): 从 config.toml 选择模型角色
    """
    name = "hello_world_agent"
    description = "A simple agent that receives greetings and responds with a verified message. Demonstrates the standard sub-agent workflow."
    
    # 允许使用的工具列表（必须包含 report_status）
    allowed_tools = ["greeting_tool", "report_status"]
    
    # 可选：指定模型角色（对应 config.toml 中的 llm.functional_roles.xxx）
    # model_role = "code_generation"  # 使用代码生成专用模型
    # 或直接指定模型标签
    # model_label = "v3-2"
