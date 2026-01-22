#!/usr/bin/env python3
"""测试Docker集群是否可访问"""

import httpx
import asyncio


async def test_node(name, url):
    """测试单个节点"""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{url}/api/capabilities")
            if response.status_code == 200:
                data = response.json()
                print(
                    f"✅ {name}: {response.status_code} - {data.get('name', 'unknown')}"
                )
                return True
            else:
                print(f"❌ {name}: HTTP {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ {name}: {e}")
        return False


async def main():
    print("测试Docker集群API可访问性...")
    print("-" * 60)

    nodes = {
        "root-0": "http://127.0.0.1:8000",
        "sub-0": "http://127.0.0.1:8001",
        "sub-1": "http://127.0.0.1:8002",
        "sub-2": "http://127.0.0.1:8003",
    }

    results = {}
    for name, url in nodes.items():
        results[name] = await test_node(name, url)

    print("-" * 60)
    print(f"总结: {sum(results.values())}/{len(results)} 节点可访问")


if __name__ == "__main__":
    asyncio.run(main())
