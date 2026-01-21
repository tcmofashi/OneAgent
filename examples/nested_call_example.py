"""
嵌套 OneAgent 使用示例
演示如何使用 RootOneAgent 和 SubOneAgent 进行嵌套编排
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.root_one_agent import RootOneAgent
from src.core.sub_one_agent import SubOneAgent


async def main():
    """
    主函数：演示嵌套 OneAgent 的使用
    """

    # 1. 创建顶层 RootOneAgent
    root_one_agent = RootOneAgent(
        name="RootOneAgent", description="顶层 OneAgent，支持嵌套编排和外部 API"
    )

    await root_one_agent.start()

    # 2. 创建几个 SubOneAgent
    # 示例：Web Agent（假设拥有 runtime 工具）
    web_agent = SubOneAgent(
        agent_id="web_agent_001",
        name="WebAgent",
        description="网页浏览代理。拥有以下 runtime 工具：playwright_navigate, playwright_click, playwright_screenshot。这些工具不嵌入能力树，在 description 中详细说明。",
        parent_agent_id=root_one_agent.id,
        runtime_tools=[],  # 这里可以传入实际的 runtime 工具列表
    )

    # 示例：Code Agent（假设拥有大量自有工具，如 Qwen Code）
    code_agent = SubOneAgent(
        agent_id="code_agent_001",
        name="CodeAgent",
        description="编程代理，拥有大量自有工具：code_analyze, code_execute, code_fix, code_test, code_refactor。由于工具数量众多，无法被能力树自动获取，因此在 description 中详细说明。",
        parent_agent_id=root_one_agent.id,
        runtime_tools=[],  # 这里可以传入实际的 runtime 工具列表
    )

    # 3. 注册子 Agent 到 RootOneAgent
    await root_one_agent.register_sub_agent(web_agent)
    await root_one_agent.register_sub_agent(code_agent)

    # 4. 查询能力树（演示 runtime 工具单独列出）
    print("\n=== 查询 RootOneAgent 能力树 ===")
    root_capabilities = await root_one_agent.get_capabilities_tree(
        agent_id=root_one_agent.id, recursive=True
    )
    print(f"Agent: {root_capabilities['agent']['name']}")
    print(f"Children: {len(root_capabilities['children'])}")
    print(f"Runtime Tools: {len(root_capabilities['runtime_tools'])}")

    print("\n=== 查询 WebAgent 能力树 ===")
    web_capabilities = await root_one_agent.get_capabilities_tree(
        agent_id=web_agent.id, recursive=False
    )
    print(f"Agent: {web_capabilities['agent']['name']}")
    print(f"Description: {web_capabilities['agent']['description']}")
    print(f"Runtime Tools: {len(web_capabilities['runtime_tools'])}")

    print("\n=== 查询 CodeAgent 能力树 ===")
    code_capabilities = await root_one_agent.get_capabilities_tree(
        agent_id=code_agent.id, recursive=False
    )
    print(f"Agent: {code_capabilities['agent']['name']}")
    print(f"Description (注意：此 Agent 的自有工具在 description 中详细说明）:")
    print(f"  {code_capabilities['agent']['description']}")

    # 5. 演示嵌套调用
    print("\n=== 演示嵌套调用 ===")

    # 5.1 调用 WebAgent（从 RootOneAgent）
    print("\n[1] RootOneAgent -> WebAgent: 浏览网页")
    result = await root_one_agent.call_nested_agent(
        agent_id=web_agent.id,
        instruction="访问百度首页并获取标题",
        context="演示嵌套调用",
        timeout=60,
    )

    if result["status"] == "success":
        print(f"结果: {result['result']}")
    else:
        print(f"错误: {result['result']}")

    # 5.2 调用 CodeAgent（从 RootOneAgent）
    print("\n[2] RootOneAgent -> CodeAgent: 分析代码")
    result = await root_one_agent.call_nested_agent(
        agent_id=code_agent.id,
        instruction="分析以下 Python 代码，找出潜在问题：\nprint('Hello, World!')",
        context="演示嵌套调用",
        timeout=60,
    )

    if result["status"] == "success":
        print(f"结果: {result['result']}")
    else:
        print(f"错误: {result['result']}")

    # 5.3 演示流式输出调用
    print("\n[3] RootOneAgent -> WebAgent: 流式输出")
    result = await root_one_agent.call_nested_agent(
        agent_id=web_agent.id,
        instruction="模拟长时间任务，流式输出结果",
        context="演示流式输出",
        timeout=120,
        expect_stream=True,
    )

    if result["status"] == "success":
        print("流式输出结果:")
        if result.get("output_stream"):
            async for chunk in result["output_stream"]:
                print(chunk, end="", flush=True)
        print("\n")
    else:
        print(f"错误: {result['result']}")

    # 6. 演示会话管理
    print("\n=== 演示会话管理 ===")

    # 6.1 创建会话
    session_id = await root_one_agent.create_nested_session(
        parent_agent_id=root_one_agent.id, timeout=60, metadata={"demo": True}
    )
    print(f"创建会话: {session_id}")

    # 6.2 查询会话
    session = await root_one_agent.get_session(session_id)
    print(f"查询会话: {session.session_id}, 状态: {session.status}")

    # 6.3 关闭会话
    success = await root_one_agent.close_nested_session(
        session_id=session_id, reason="demo_complete"
    )
    print(f"关闭会话: {success}")

    # 停止 RootOneAgent
    await root_one_agent.stop()

    print("\n=== 示例完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
