#!/usr/bin/env python3
"""简单测试脚本 - 验证分布式集群连接"""

import asyncio
import httpx


async def test_all_nodes():
    """测试所有节点连接"""
    urls = {
        "root": "http://localhost:8000",
        "sub-0": "http://localhost:8001",
        "sub-1": "http://localhost:8002",
        "sub-2": "http://localhost:8003",
    }

    print("🔍 测试所有节点连接...\n")

    for name, url in urls.items():
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.get(f"{url}/api/capabilities")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {name} ({url}): OK")
                    print(f"   能力树长度: {len(data.get('capabilities', ''))} 字符")
                    print(f"   工具数量: {len(data.get('tools', []))}")
                else:
                    print(f"❌ {name} ({url}): HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ {name} ({url}): {e}")
        print()

    print("✅ 测试完成")


if __name__ == "__main__":
    asyncio.run(test_all_nodes())
