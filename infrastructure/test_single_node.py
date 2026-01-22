#!/usr/bin/env python3
"""测试单个节点调用"""

import asyncio
import httpx
import time


async def test_single_node():
    """测试单个节点调用 qwen_bridge_agent"""
    print("🔍 测试 sub-0 节点调用...\n")

    client = httpx.AsyncClient(timeout=120.0, trust_env=False)

    try:
        # 创建 session
        print("1. 创建 session...")
        resp = await client.post("http://localhost:8001/api/sessions")
        session_id = resp.json()["session_id"]
        print(f"   ✅ Session ID: {session_id}\n")

        # 发送简单任务
        print("2. 发送任务: 返回 Hello World...")
        payload = {
            "message": "使用qwen_bridge_agent返回Hello World",
            "session_id": session_id,
        }

        start_time = time.time()
        resp = await client.post(
            "http://localhost:8001/api/chat/stream", json=payload, timeout=120.0
        )
        elapsed = time.time() - start_time

        print(f"   响应时间: {elapsed:.2f}秒\n")

        if resp.status_code == 200:
            print("3. 解析 SSE 流...")
            messages = []
            steps = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                        if event.get("event") == "message":
                            msg = event.get("data", "")
                            messages.append(msg)
                        if event.get("event") == "step":
                            step_data = json.loads(event.get("data", "{}"))
                            steps.append(step_data.get("type", "unknown"))
                    except:
                        pass

            print(f"   ✅ 收到 {len(messages)} 条消息")
            print(f"   ✅ 收到 {len(steps)} 个步骤")
            print(f"   步骤类型: {set(steps)}\n")

            if messages:
                print("4. 响应内容:")
                for i, msg in enumerate(messages[:5]):
                    print(f"   [{i}] {msg[:200]}")

            print(f"\n✅ 测试完成")
        else:
            print(f"❌ 失败: HTTP {resp.status_code}")
            print(resp.text)

    except Exception as e:
        print(f"❌ 异常: {e}")
        import traceback

        traceback.print_exc()
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(test_single_node())
