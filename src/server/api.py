"""
FastAPI 应用入口
集成 WebSocket 和 HTTP 网关，提供统一的 API 接口
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from src.core.root_one_agent import RootOneAgent
from src.server.ws_gateway import OneAgentWebSocketGateway
from src.server.http_gateway import OneAgentHTTPGateway


app = FastAPI(
    title="OneAgent Nested API",
    description="嵌套 OneAgent 编排系统 - 统一 API 接口",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root_one_agent: RootOneAgent = None
ws_gateway: OneAgentWebSocketGateway = None
http_gateway: OneAgentHTTPGateway = None


@app.on_event("startup")
async def startup_event():
    """启动事件：初始化 RootOneAgent 和网关"""
    global root_one_agent, ws_gateway, http_gateway

    root_one_agent = RootOneAgent(
        name="RootOneAgent", description="顶层 OneAgent，支持嵌套编排和外部 API"
    )

    await root_one_agent.start()

    ws_gateway = OneAgentWebSocketGateway(root_one_agent)
    http_gateway = OneAgentHTTPGateway(root_one_agent)


@app.on_event("shutdown")
async def shutdown_event():
    """关闭事件：清理资源"""
    global root_one_agent

    if root_one_agent:
        await root_one_agent.stop()


@app.get("/")
async def root():
    """根路径"""
    return {"name": "OneAgent Nested API", "version": "1.0.0", "status": "running"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    global ws_gateway

    await ws_gateway.handle_connection(websocket)


@app.post("/api/agent/nested_call")
async def nested_call(request: dict):
    """
    嵌套调用端点

    支持 SSE 流式输出
    """
    from src.models.requests import NestedCallRequest

    request_obj = NestedCallRequest(**request)
    global http_gateway

    return await http_gateway.nested_call_endpoint(request_obj)


@app.get("/api/agent/capabilities")
async def get_capabilities(agent_id: str, recursive: bool = False):
    """
    能力树查询端点

    Args:
        agent_id: Agent ID
        recursive: 是否递归查询
    """
    global http_gateway

    return await http_gateway.get_capabilities_endpoint(
        agent_id=agent_id, recursive=recursive
    )


@app.post("/api/session/create")
async def create_session(request: dict):
    """
    创建会话端点

    Args:
        request: 会话创建请求
    """
    from src.models.requests import CreateSessionRequest

    request_obj = CreateSessionRequest(**request)
    global http_gateway

    return await http_gateway.create_session_endpoint(
        parent_agent_id=request_obj.parent_agent_id,
        parent_session_id=request_obj.parent_session_id,
        timeout=request_obj.timeout,
        metadata=request_obj.metadata,
    )


@app.post("/api/session/close")
async def close_session(request: dict):
    """
    关闭会话端点

    Args:
        request: 会话关闭请求
    """
    from src.models.requests import CloseSessionRequest

    request_obj = CloseSessionRequest(**request)
    global http_gateway

    return await http_gateway.close_session_endpoint(request_obj.session_id)


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """
    获取会话端点

    Args:
        session_id: 会话 ID
    """
    global http_gateway

    return await http_gateway.get_session_endpoint(session_id)


@app.post("/api/heartbeat")
async def heartbeat(request: dict):
    """
    心跳端点

    Args:
        request: 心跳请求
    """
    from src.models.requests import HeartbeatRequest

    request_obj = HeartbeatRequest(**request)

    try:
        session = await root_one_agent.get_session(request_obj.session_id)
        if session:
            return {"status": "pong"}
        else:
            return {"status": "error", "message": "Session not found"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
