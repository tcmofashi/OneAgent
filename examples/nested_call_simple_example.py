"""
嵌套 OneAgent 简单示例
演示 RootOneAgent 和 SubOneAgent 的基本使用
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.root_one_agent import RootOneAgent
from src.core.sub_one_agent import SubOneAgent


async def main():
    root_one_agent = RootOneAgent(
        name="RootOneAgent",
        description="顶层 OneAgent，支持嵌套编排和外部 API",
    )

    await root_one_agent.start()

    web_agent = SubOneAgent(
        agent_id="web_agent_001",
        name="WebAgent",
        description="网页浏览代理（模拟）",
        parent_agent_id=root_one_agent.id,
        runtime_tools=[],
    )

    code_agent = SubOneAgent(
        agent_id="code_agent_001",
        name="CodeAgent",
        description="编程代理（模拟）",
        parent_agent_id=root_one_agent.id,
        runtime_tools=[],
    )

    await root_one_agent.register_sub_agent(web_agent)
    await root_one_agent.register_sub_agent(code_agent)

    print("\n=== 查询 RootOneAgent 能力树 ===")
    root_capabilities = await root_one_agent.get_capabilities_tree(
        agent_id=root_one_agent.id, recursive=True
    )
    print(f"Agent: {root_capabilities['agent']['name']}")
    print(f"Children: {len(root_capabilities['children'])}")
    print(f"Runtime Tools: {len(root_capabilities['runtime_tools'])}")

    original_web_execute = web_agent.execute

    async def mock_web_execute(instruction, context=None, upstream_capabilities=None):
        return f"WebAgent 执行完成: {instruction}"

    original_code_execute = code_agent.execute

    async def mock_code_execute(instruction, context=None, upstream_capabilities=None):
        return f"CodeAgent 执行完成: {instruction}"

    web_agent.execute = mock_web_execute
    code_agent.execute = mock_code_execute

    print("\n=== 演示嵌套调用 ===")

    print("\n[1] RootOneAgent -> WebAgent: 浏览网页")
    result1 = await root_one_agent.call_nested_agent(
        agent_id=web_agent.id,
        instruction="访问百度首页",
        timeout=60,
    )

    if result1["status"] == "success":
        print(f"结果: {result1['result']}")
    else:
        print(f"错误: {result1['result']}")

    print("\n[2] RootOneAgent -> CodeAgent: 分析代码")
    result2 = await root_one_agent.call_nested_agent(
        agent_id=code_agent.id,
        instruction="分析 Python 代码",
        timeout=60,
    )

    if result2["status"] == "success":
        print(f"结果: {result2['result']}")
    else:
        print(f"错误: {result2['result']}")

    print("\n[3] RootOneAgent -> WebAgent: 流式输出")
    result3 = await root_one_agent.call_nested_agent(
        agent_id=web_agent.id,
        instruction="长时间任务",
        timeout=120,
        expect_stream=True,
    )

    if result3["status"] == "success":
        print("流式输出结果:")
        if result3.get("output_stream"):
            async for chunk in result3["output_stream"]:
                print(chunk, end="", flush=True)
        print("\n")
    else:
        print(f"错误: {result3['result']}")

    print("\n=== 演示会话管理 ===")

    session_id = await root_one_agent.create_nested_session(
        parent_agent_id=root_one_agent.id, timeout=60
    )
    print(f"创建会话: {session_id}")

    retrieved_session = await root_one_agent.get_session(session_id)
    print(f"查询会话: {retrieved_session.session_id}")

    success = await root_one_agent.close_nested_session(session_id)
    print(f"关闭会话: {success}")

    await root_one_agent.stop()
    print("\n=== 示例完成 ===")


if __name__ == "__main__":
    asyncio.run(main())
