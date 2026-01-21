"""
嵌套 OneAgent 集成测试
测试端到端的功能
"""

import pytest
import asyncio
import httpx
from src.server.api import app


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查端点"""
    # Start the app
    await app.router.startup()

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_capabilities_endpoint():
    """测试能力树查询端点"""
    await app.router.startup()

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # 查询 RootOneAgent 的能力树
        response = await client.get(
            "/api/agent/capabilities?agent_id=RootOneAgent&recursive=true"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data


@pytest.mark.asyncio
async def test_nested_call_non_stream():
    """测试非流式嵌套调用 - 需要 Mock Agent"""
    # 注意：此测试需要注册测试用的 SubOneAgent
    # 实际使用时需要确保有可用的子代理
    pass


@pytest.mark.asyncio
async def test_nested_call_stream():
    """测试流式嵌套调用 - 需要 Mock Agent"""
    # 注意：此测试需要注册测试用的 SubOneAgent
    pass


@pytest.mark.asyncio
async def test_session_lifecycle():
    """测试会话生命周期"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # 1. 创建会话
        create_response = await client.post(
            "/api/session/create",
            json={"parent_agent_id": "RootOneAgent", "timeout": 60},
        )

        assert create_response.status_code == 200
        session_id = create_response.json()["session_id"]
        assert session_id is not None

        # 2. 获取会话
        get_response = await client.get(f"/api/session/{session_id}")
        assert get_response.status_code == 200
        session_data = get_response.json()
        assert session_data["data"]["parent_agent_id"] == "RootOneAgent"

        # 3. 关闭会话
        close_response = await client.post(
            "/api/session/close", json={"session_id": session_id}
        )

        assert close_response.status_code == 200
        assert close_response.json()["message"] is not None


@pytest.mark.asyncio
async def test_heartbeat():
    """测试心跳端点"""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        # 1. 创建会话
        create_response = await client.post(
            "/api/session/create",
            json={"parent_agent_id": "RootOneAgent", "timeout": 60},
        )
        session_id = create_response.json()["session_id"]

        # 2. 发送心跳
        heartbeat_response = await client.post(
            "/api/heartbeat", json={"session_id": session_id}
        )

        assert heartbeat_response.status_code == 200
        data = heartbeat_response.json()
        assert data["status"] == "pong"

        # 3. 发送心跳到不存在的会话
        invalid_heartbeat = await client.post(
            "/api/heartbeat", json={"session_id": "invalid_session_id"}
        )

        assert invalid_heartbeat.status_code == 200
        data = invalid_heartbeat.json()
        assert data["status"] == "error"
        assert "not found" in data["message"]


@pytest.mark.asyncio
async def test_error_handling():
    """测试错误处理"""
    await app.router.startup()

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/agent/nested_call",
            json={"agent_id": "non_existent_agent", "instruction": "测试"},
        )

        assert response.status_code == 200
        content = []
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                content.append(line[6:])
        last_event = content[-1]
        assert '"status": "error"' in last_event or '"type": "error"' in last_event

        response = await client.get("/api/session/invalid_session")
        assert response.status_code == 404

        response = await client.post(
            "/api/session/close", json={"session_id": "invalid_session"}
        )

        assert response.status_code == 404

        # 3. 关闭不存在的会话
        response = await client.post(
            "/api/session/close", json={"session_id": "invalid_session"}
        )

        assert response.status_code == 404
