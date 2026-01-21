"""
WebSocket 网关
处理 WebSocket 连接、握手、心跳、Agent 调用、能力查询等
"""

import json
import asyncio
from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect
from src.core.root_one_agent import RootOneAgent
from src.models.protocol import (
    MessageType,
    HandshakeMessage,
    ConnectedMessage,
    HeartbeatMessage,
    PongMessage,
    CallAgentMessage,
    GetCapabilitiesMessage,
    OutputMessage,
    CapabilitiesMessage,
    CompleteMessage,
    ErrorMessage,
    parse_message,
)


class OneAgentWebSocketGateway:
    """
    WebSocket 网关实现

    特性：
    - 处理 WebSocket 握手和连接确认
    - 心跳机制（每 30 秒）
    - Agent 调用（支持流式输出）
    - 能力树查询
    - 会话管理
    """

    def __init__(self, root_one_agent: RootOneAgent):
        """
        初始化 WebSocket 网关

        Args:
            root_one_agent: RootOneAgent 实例
        """
        self.root_one_agent = root_one_agent
        self.active_connections: Dict[str, WebSocket] = {}

    async def handle_connection(self, websocket: WebSocket):
        """
        处理 WebSocket 连接

        Args:
            websocket: WebSocket 连接实例
        """
        await websocket.accept()
        session_id = None

        try:
            # 等待握手消息
            handshake_data = await websocket.receive_text()
            handshake_msg = json.loads(handshake_data)
            msg_obj = parse_message(handshake_msg)

            if not isinstance(msg_obj, HandshakeMessage):
                await self._send_error(websocket, "Handshake required")
                await websocket.close(code=1008)
                return

            # 生成或使用已有 session_id
            session_id = msg_obj.session_id or f"ws_session_{id(websocket)}"

            if session_id not in self.active_connections:
                self.active_connections[session_id] = websocket

            # 发送连接确认
            connected_msg = ConnectedMessage(session_id=session_id)
            await websocket.send_text(connected_msg.json())

            # 启动心跳任务
            heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(websocket, session_id)
            )

            # 消息循环
            while True:
                data = await websocket.receive_text()
                msg = json.loads(data)
                msg_obj = parse_message(msg)

                if isinstance(msg_obj, HeartbeatMessage):
                    await self._handle_heartbeat(websocket, msg_obj)
                elif isinstance(msg_obj, CallAgentMessage):
                    await self._handle_call_agent(websocket, msg_obj, session_id)
                elif isinstance(msg_obj, GetCapabilitiesMessage):
                    await self._handle_get_capabilities(websocket, msg_obj)
                else:
                    await self._send_error(
                        websocket, f"Unknown message type: {msg_obj.type}"
                    )

        except WebSocketDisconnect:
            pass
        except Exception as e:
            await self._send_error(websocket, str(e))
        finally:
            # 清理连接
            if session_id and session_id in self.active_connections:
                del self.active_connections[session_id]
            if "heartbeat_task" in locals():
                heartbeat_task.cancel()

    async def _heartbeat_loop(self, websocket: WebSocket, session_id: str):
        """
        心跳循环

        Args:
            websocket: WebSocket 连接
            session_id: 会话 ID
        """
        try:
            while True:
                await asyncio.sleep(30)
                pong_msg = PongMessage(timestamp=None)
                await websocket.send_text(pong_msg.json())
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"心跳错误: {e}")

    async def _handle_heartbeat(self, websocket: WebSocket, msg: HeartbeatMessage):
        """
        处理心跳消息

        Args:
            websocket: WebSocket 连接
            msg: 心跳消息
        """
        pong_msg = PongMessage(timestamp=msg.timestamp)
        await websocket.send_text(pong_msg.json())

    async def _handle_call_agent(
        self, websocket: WebSocket, msg: CallAgentMessage, session_id: str
    ):
        """
        处理 Agent 调用消息

        Args:
            websocket: WebSocket 连接
            msg: 调用消息
            session_id: 会话 ID
        """
        try:
            # 调用嵌套 Agent
            result = await self.root_one_agent.call_nested_agent(
                agent_id=msg.target_agent_id,
                instruction=msg.instruction,
                context=msg.context,
                parameters=msg.parameters,
                timeout=msg.timeout,
                expect_stream=msg.expect_stream,
            )

            # 流式输出
            if result.get("output_stream"):
                output_stream = result["output_stream"]

                async def stream_gen():
                    try:
                        async for chunk in output_stream():
                            output_msg = OutputMessage(
                                session_id=session_id, content=chunk, done=False
                            )
                            await websocket.send_text(output_msg.json())
                    except Exception as e:
                        await self._send_error(websocket, f"流式输出错误: {e}")

                asyncio.create_task(stream_gen())
            else:
                # 单次输出
                if result.get("result"):
                    output_msg = OutputMessage(
                        session_id=session_id, content=result["result"], done=False
                    )
                    await websocket.send_text(output_msg.json())

            # 发送完成消息
            complete_msg = CompleteMessage(
                session_id=session_id, result=result.get("status", "success")
            )
            await websocket.send_text(complete_msg.json())

        except Exception as e:
            await self._send_error(websocket, f"Agent 调用错误: {e}")

    async def _handle_get_capabilities(
        self, websocket: WebSocket, msg: GetCapabilitiesMessage
    ):
        """
        处理能力树查询消息

        Args:
            websocket: WebSocket 连接
            msg: 查询消息
        """
        try:
            capabilities = await self.root_one_agent.get_capabilities_tree(
                agent_id=msg.agent_id, recursive=msg.recursive
            )

            capabilities_msg = CapabilitiesMessage(session_id=None, data=capabilities)
            await websocket.send_text(capabilities_msg.json())

        except Exception as e:
            await self._send_error(websocket, f"能力查询错误: {e}")

    async def _send_error(self, websocket: WebSocket, message: str, code: int = None):
        """
        发送错误消息

        Args:
            websocket: WebSocket 连接
            message: 错误信息
            code: 错误代码
        """
        error_msg = ErrorMessage(message=message, code=code)
        await websocket.send_text(error_msg.json())
