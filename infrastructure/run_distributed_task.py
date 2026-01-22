#!/usr/bin/env python3
"""
分布式任务测试脚本
目标：root节点编排所有sub节点执行ps命令获取进程数，然后汇总结果
"""

import asyncio
import json
import httpx
from datetime import datetime
import time


class DistributedTaskClient:
    """分布式任务客户端"""

    def __init__(self, root_url="http://localhost:8000"):
        self.root_url = root_url
        self.sub_nodes = {
            "sub-0": "http://localhost:8001",
            "sub-1": "http://localhost:8002",
            "sub-2": "http://localhost:8003",
        }

    async def check_health(self, url):
        """检查节点健康状态"""
        try:
            async with httpx.AsyncClient(timeout=5.0, trust_env=False) as client:
                response = await client.get(f"{url}/api/capabilities")
                return response.status_code == 200
        except Exception as e:
            print(f"  ❌ 健康检查失败 {url}: {e}")
            return False

    async def wait_for_cluster_ready(self, max_wait=120):
        """等待所有节点就绪"""
        print("\n⏳ 等待集群节点就绪...")
        all_ready = False
        start_time = time.time()

        while not all_ready and (time.time() - start_time) < max_wait:
            print(f"\n  检查节点状态 (已等待 {int(time.time() - start_time)}s)...")

            # 检查root节点
            root_ready = await self.check_health(self.root_url)
            print(f"  🟢 Root节点 (root-0): {'✅ 就绪' if root_ready else '❌ 未就绪'}")

            # 检查所有sub节点
            sub_status = {}
            all_sub_ready = True
            for name, url in self.sub_nodes.items():
                ready = await self.check_health(url)
                sub_status[name] = ready
                all_sub_ready = all_sub_ready and ready
                print(f"  🟡 {name}: {'✅ 就绪' if ready else '❌ 未就绪'}")

            all_ready = root_ready and all_sub_ready
            if all_ready:
                print("\n✅ 所有节点已就绪！")
                return True

            await asyncio.sleep(5)

        print("\n❌ 超时：集群未能在规定时间内就绪")
        return False

    async def get_capabilities(self, url):
        """获取节点能力树"""
        try:
            async with httpx.AsyncClient(timeout=10.0, trust_env=False) as client:
                response = await client.get(f"{url}/api/capabilities")
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"  ❌ 获取能力失败 {url}: {e}")
        return None

    async def call_remote_agent(self, url, instruction):
        """调用远程代理"""
        try:
            async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
                response = await client.post(f"{url}/api/sessions")
                if response.status_code != 200:
                    print(f"  ❌ 创建session失败: HTTP {response.status_code}")
                    return None
                session_id = response.json()["session_id"]
                print(f"  🔑 Session ID: {session_id}")

                payload = {
                    "message": f"使用qwen_bridge_agent执行任务: {instruction}",
                    "session_id": session_id,
                }

                print(f"\n  📤 调用 {url}: {instruction}")

                response = await client.post(
                    f"{url}/api/chat/stream",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                    timeout=120.0,
                )

                if response.status_code == 200:
                    result_text = ""
                    current_event = ""
                    for line in response.iter_lines():
                        if line.startswith("event:"):
                            current_event = line[6:].strip()
                            continue
                        if line.startswith("data:"):
                            data = line[5:].strip()
                            if data == "[DONE]":
                                break
                            try:
                                if current_event == "message":
                                    result_text += data
                                elif current_event == "step":
                                    event_data = json.loads(data)
                                    if event_data.get("type") == "answer_chunk":
                                        result_text += event_data.get("content", "")
                                    elif event_data.get("type") == "answer_done":
                                        result_text += event_data.get("content", "")
                            except:
                                pass
                    print(f"  📥 响应长度: {len(result_text)} 字符")
                    print(f"  📥 响应预览: {result_text[:300]}...")
                    return result_text
                else:
                    print(f"  ❌ 调用失败: HTTP {response.status_code}")
                    return None

        except Exception as e:
            print(f"  ❌ 调用异常: {e}")
            import traceback

            traceback.print_exc()
            return None

    async def execute_distributed_task(self):
        """执行分布式任务：root节点调用所有sub节点获取进程数"""
        print("\n" + "=" * 80)
        print("🚀 开始分布式任务测试")
        print("=" * 80)
        print(f"\n⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 步骤1: 查询root节点能力树
        print("\n【步骤1】查询Root节点能力树")
        root_caps = await self.get_capabilities(self.root_url)
        if root_caps:
            print(f"  ✅ Root节点能力树已加载")
            print(f"  📊 可用Agent数量: {len(root_caps.get('children', []))}")
        else:
            print(f"  ❌ 无法获取Root节点能力树")
            return False

        # 步骤2: 查询每个sub节点能力树
        print("\n【步骤2】查询所有Sub节点能力树")
        for name, url in self.sub_nodes.items():
            caps = await self.get_capabilities(url)
            if caps:
                print(f"  ✅ {name} 能力树已加载")
            else:
                print(f"  ❌ {name} 能力树加载失败")

        # 步骤3: Root节点调用每个sub节点获取进程数
        print("\n【步骤3】Root节点调用Sub节点获取进程数")
        task_instruction = "首先使用update_agent_tasks工具记录任务：'- [ ] qwen_bridge_agent: 使用qwen-code执行命令ps aux并统计进程数量'，然后调用qwen_bridge_agent执行该任务。返回精确的进程数量数字结果。"

        results = {}
        for name, url in self.sub_nodes.items():
            print(f"\n  🎯 调用 {name}...")
            result = await self.call_remote_agent(url, task_instruction)
            results[name] = result
            if result and "Task Completed" in result:
                print(f"  ✅ {name} 任务完成")
            else:
                print(f"  ⚠️  {name} 任务可能未成功")

        # 步骤4: 汇总结果
        print("\n【步骤4】汇总所有节点结果")
        print(f"\n{'=' * 80}")
        print("📊 任务结果汇总")
        print(f"{'=' * 80}")

        success_count = 0
        for name, result in results.items():
            status = "✅ 成功" if result and "Task Completed" in result else "❌ 失败"
            print(f"\n{name}:")
            print(f"  状态: {status}")
            if result:
                # 尝试提取进程数
                if "Status: success" in result:
                    print(f"  结果: 执行成功")
                else:
                    print(f"  结果片段: {result[:300]}...")

        # 验证所有节点都成功
        all_success = all(r and "Task Completed" in r for r in results.values())
        success_count = sum(1 for r in results.values() if r and "Task Completed" in r)

        print(f"\n{'=' * 80}")
        print(f"📈 总体统计")
        print(f"{'=' * 80}")
        print(f"  总节点数: {len(self.sub_nodes)}")
        print(f"  成功节点: {success_count}")
        print(f"  失败节点: {len(self.sub_nodes) - success_count}")
        print(f"  成功率: {success_count / len(self.sub_nodes) * 100:.1f}%")

        if all_success:
            print(f"\n🎉 分布式任务测试成功！所有节点都成功执行了任务。")
        else:
            print(
                f"\n⚠️  分布式任务测试部分成功：{success_count}/{len(self.sub_nodes)} 节点成功"
            )

        print(f"\n⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return all_success


async def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🐳 OneAgent Docker分布式任务测试")
    print("任务: Root节点编排Sub节点获取进程数")
    print("=" * 80)

    client = DistributedTaskClient()

    # 等待集群就绪
    if not await client.wait_for_cluster_ready():
        print("\n❌ 集群未就绪，无法执行任务")
        return False

    # 执行分布式任务
    success = await client.execute_distributed_task()

    return success


if __name__ == "__main__":
    result = asyncio.run(main())
    exit(0 if result else 1)
