"""
HTTP 网关
处理 HTTP 请求，支持 SSE 流式输出
"""

import json
from datetime import datetime
from typing import AsyncGenerator, Optional
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from src.core.root_one_agent import RootOneAgent
from src.models.requests import (
    NestedCallRequest,
    GetCapabilitiesRequest,
    CreateSessionRequest,
    CloseSessionRequest,
    HeartbeatRequest,
)
from src.models.responses import (
    ApiResponse,
    SSEMessageEvent,
    SSECompleteEvent,
    SSEErrorEvent,
)


class OneAgentHTTPGateway:
    """
    HTTP 网关实现

    特性：
    - 处理 HTTP 请求
    - 支持 SSE 流式输出
    - 嵌套 Agent 调用
    - 能力树查询
    - 会话管理
    """

    def __init__(self, root_one_agent: RootOneAgent):
        self.root_one_agent = root_one_agent

    async def nested_call_endpoint(self, request: NestedCallRequest):
        """
        嵌套调用端点

        Args:
            request: 嵌套调用请求

        Returns:
            StreamingResponse (SSE 流）
        """

        async def output_generator():
            try:
                result = await self.root_one_agent.call_nested_agent(
                    agent_id=request.agent_id,
                    instruction=request.instruction,
                    context=request.context,
                    parameters=request.parameters,
                    timeout=request.timeout,
                    expect_stream=request.expect_stream,
                )

                start_data = {
                    "type": "start",
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(start_data)}\n\n"

                if result.get("output_stream"):
                    output_stream = result["output_stream"]
                    async for chunk in output_stream():
                        event_data = {
                            "type": "output",
                            "content": chunk,
                            "timestamp": datetime.utcnow().isoformat(),
                            "done": False,
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                else:
                    if result.get("result"):
                        event_data = {
                            "type": "output",
                            "content": result["result"],
                            "timestamp": datetime.utcnow().isoformat(),
                            "done": False,
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"

                complete_data = {
                    "type": "complete",
                    "status": result.get("status", "success"),
                    "timestamp": datetime.utcnow().isoformat(),
                    "done": True,
                }
                yield f"data: {json.dumps(complete_data)}\n\n"

            except Exception as e:
                error_data = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat(),
                }
                yield f"data: {json.dumps(error_data)}\n\n"

        return StreamingResponse(
            content=output_generator(), media_type="text/event-stream"
        )

    async def get_capabilities_endpoint(self, agent_id: str, recursive: bool = False):
        """
        能力树查询端点

        Args:
            agent_id: Agent ID
            recursive: 是否递归查询

        Returns:
            能力树数据
        """
        try:
            capabilities = await self.root_one_agent.get_capabilities_tree(
                agent_id=agent_id, recursive=recursive
            )

            return {"status": "success", "data": capabilities}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def create_session_endpoint(
        self,
        parent_agent_id: str,
        parent_session_id: Optional[str] = None,
        timeout: int = 1800,
        metadata: Optional[dict] = None,
    ):
        """
        创建会话端点

        Args:
            parent_agent_id: 父 Agent ID
            parent_session_id: 父会话 ID
            timeout: 超时时间
            metadata: 会话元数据

        Returns:
            会话创建响应
        """
        try:
            session_id = await self.root_one_agent.create_nested_session(
                parent_agent_id=parent_agent_id,
                parent_session_id=parent_session_id if parent_session_id else None,
                timeout=timeout,
                metadata=metadata if metadata is not None else {},
            )

            return {"status": "success", "session_id": session_id}

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def close_session_endpoint(self, session_id: str):
        """
        关闭会话端点

        Args:
            session_id: 会话 ID

        Returns:
            会话关闭响应
        """
        try:
            success = await self.root_one_agent.close_nested_session(session_id)

            if success:
                return {"status": "success", "message": f"Session {session_id} closed"}
            else:
                raise HTTPException(status_code=404, detail="Session not found")

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session_endpoint(self, session_id: str):
        """
        获取会话端点

        Args:
            session_id: 会话 ID

        Returns:
            会话数据
        """
        try:
            session = await self.root_one_agent.get_session(session_id)

            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

            return {"status": "success", "data": session.dict()}

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
