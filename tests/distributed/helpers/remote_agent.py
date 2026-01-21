"""
RemoteAgent - 透明代理，将远程 OneAgent 封装为本地 Agent

使主控 Orchestrator 无需感知远程 vs 本地差异
"""

import httpx
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
from src.core.protocol import ExecutionResult, AgentStatus
from src.core.logger import logger


class RemoteAgent:
    """
    远程 Agent 封装

    功能：
    - 封装 HTTP 请求到远程 OneAgent
    - 统一接口：execute(), stream_execute()
    - 支持流式输出
    - 自动重试和错误处理
    """

    def __init__(
        self,
        agent_id: str,
        name: str,
        remote_url: str,
        timeout: int = 120,
        max_retries: int = 3,
    ):
        self.id = agent_id
        self.name = name
        self.description = f"远程 Agent，地址: {remote_url}"
        self.remote_url = remote_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client: Optional[httpx.AsyncClient] = None

    async def initialize(self):
        """初始化 HTTP 客户端"""
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def shutdown(self):
        """关闭 HTTP 客户端"""
        if self.client:
            await self.client.aclose()

    async def execute(
        self,
        instruction: str,
        context: str = "",
        upstream_capabilities: str = "",
        **kwargs,
    ) -> ExecutionResult:
        """
        执行远程 Agent 调用

        Args:
            instruction: 指令
            context: 上下文
            upstream_capabilities: 上级能力树

        Returns:
            ExecutionResult
        """
        if not self.client:
            await self.initialize()

        # 构造调用消息
        call_msg = {
            "agent_id": self.id,
            "instruction": instruction,
            "context": context,
            "parameters": {"upstream_capabilities": upstream_capabilities},
            "timeout": self.timeout,
            "expect_stream": False,
        }

        # 调用远程 API
        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.remote_url}/api/agent/nested_call",
                    json=call_msg,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                # SSE 流式响应处理
                final_status = "unknown"
                final_result = ""

                # 收集 SSE 事件
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀
                        import json

                        try:
                            event = json.loads(data)
                            if event.get("type") == "complete":
                                final_status = event.get("status", "unknown")
                                break
                            elif event.get("type") == "output" and not event.get(
                                "done", False
                            ):
                                if event.get("content"):
                                    final_result += event["content"]
                            elif event.get("type") == "error":
                                return ExecutionResult(
                                    status=AgentStatus.FAILURE,
                                    result=event.get("message", "Unknown error"),
                                    reason="Remote agent error",
                                )
                        except json.JSONDecodeError:
                            continue

                # 返回结果
                if final_status == "success":
                    return ExecutionResult(
                        status=AgentStatus.SUCCESS, result=final_result or "执行成功"
                    )
                else:
                    return ExecutionResult(
                        status=AgentStatus.FAILURE,
                        result=final_result or "执行失败",
                        reason=f"Remote agent returned status: {final_status}",
                    )

            except httpx.TimeoutException as e:
                if attempt == self.max_retries - 1:
                    return ExecutionResult(
                        status=AgentStatus.FAILURE,
                        result=f"Timeout after {self.timeout}s",
                        reason=f"Remote agent timeout after {self.max_retries} retries",
                    )
                await asyncio.sleep(2**attempt)  # 指数退避
                logger.log(
                    event="RETRY_ATTEMPT",
                    content=f"Retry attempt {attempt + 1}/{self.max_retries}",
                    agent="RemoteAgent",
                )

            except httpx.HTTPError as e:
                if attempt == self.max_retries - 1:
                    return ExecutionResult(
                        status=AgentStatus.FAILURE,
                        result=f"HTTP error: {str(e)}",
                        reason=f"Remote agent unreachable after {self.max_retries} retries",
                    )
                await asyncio.sleep(2**attempt)  # 指数退避

            except Exception as e:
                return ExecutionResult(
                    status=AgentStatus.FAILURE,
                    result=f"Unexpected error: {str(e)}",
                    reason="Remote agent communication failed",
                )

        # 默认失败返回
        return ExecutionResult(
            status=AgentStatus.FAILURE,
            result="Max retries exceeded",
            reason="Remote agent unreachable",
        )

    async def stream_execute(
        self, instruction: str, context: str = "", **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式执行远程 Agent

        Yields:
            输出片段
        """
        if not self.client:
            await self.initialize()

        # 使用 SSE 流式接收
        call_msg = {
            "agent_id": self.id,
            "instruction": instruction,
            "context": context,
            "parameters": {},
            "timeout": self.timeout,
            "expect_stream": True,
        }

        try:
            response = await self.client.post(
                f"{self.remote_url}/api/agent/nested_call",
                json=call_msg,
                timeout=self.timeout,
            )
            response.raise_for_status()

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    import json

                    try:
                        event = json.loads(data)
                        if event.get("type") == "output":
                            content = event.get("content", "")
                            if content:
                                yield content
                        elif event.get("type") == "complete":
                            break
                        elif event.get("type") == "error":
                            yield f"[Error] {event.get('message', 'Unknown error')}"
                            break
                    except json.JSONDecodeError:
                        continue

        except Exception as e:
            yield f"[Error] Failed to stream from remote agent: {str(e)}"

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        获取远程 Agent 能力树

        Returns:
            能力树字典
        """
        if not self.client:
            await self.initialize()

        try:
            response = await self.client.get(
                f"{self.remote_url}/api/agent/capabilities",
                params={"agent_id": self.id, "recursive": True},
                timeout=30.0,
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            logger.log(
                event="CAPABILITIES_FETCH_FAILED",
                content=str(e),
                agent=self.name,
            )
            return {
                "status": "error",
                "message": f"Failed to fetch capabilities: {str(e)}",
            }
