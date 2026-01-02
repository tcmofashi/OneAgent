
import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager

from src.core.config import Config
from src.utils.loader import load_capabilities
from src.core.session import SessionManager
from src.core.orchestrator import Orchestrator
from src.core.registry import global_registry

# Setup Logging
logger = logging.getLogger("WebServer")
logging.basicConfig(level=logging.INFO)

# Global State
active_orchestrator: Optional[Orchestrator] = None
active_orchestrators: Dict[str, Orchestrator] = {}  # Per-session orchestrators

def get_orchestrator(session_id: str) -> Orchestrator:
    """Get or create an Orchestrator for the given session."""
    if session_id not in active_orchestrators:
        active_orchestrators[session_id] = Orchestrator(session_id=session_id)
    return active_orchestrators[session_id]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing OneAgent Web Server...")
    Config() # Load config
    load_capabilities() # Load tools/agents
    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class SessionAction(BaseModel):
    action: str # resume, rewind
    arg: Optional[Any] = None # rewind index

# --- Routes ---

@app.get("/api/sessions")
async def list_sessions():
    return SessionManager.list_sessions()

@app.post("/api/sessions")
async def create_session():
    """Create a new blank session"""
    mgr = SessionManager() # New ID
    return {"session_id": mgr.session_id}

@app.post("/api/sessions/{session_id}/resume")
async def resume_session(session_id: str):
    global active_orchestrator
    try:
        active_orchestrator = Orchestrator(session_id=session_id)
        return {"status": "success", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions/{session_id}/rewind")
async def rewind_session(session_id: str, payload: SessionAction):
    global active_orchestrator
    if not payload.arg:
         raise HTTPException(status_code=400, detail="Missing rewind index")
    
    # 1. Load session if not active
    mgr = SessionManager(session_id)
    if not mgr.loaded:
         raise HTTPException(status_code=404, detail="Session not found")
         
    # 2. Truncate
    index = int(payload.arg)
    mgr.truncate_history(index)
    
    # 3. Reload active orchestrator if it matches
    # if active_orchestrator and active_orchestrator.session.session_id == session_id: # Deprecated
    if session_id in active_orchestrators:
        active_orchestrators[session_id] = Orchestrator(session_id=session_id) # Reload
        
    return {"status": "success", "new_history_len": len(mgr.history)}

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Legacy SSE Endpoint (Deprecated)
    """
    session_id = request.session_id
    if not session_id:
        return JSONResponse({"error": "Session ID required"}, status_code=400)
    
    active_orchestrator = get_orchestrator(session_id)
    
    async def event_generator():
        yield {"event": "input_ack", "data": "Processing..."}
        try:
            print(f"[WebServer] Starting stream for {request.message[:20]}...")
            async for event in active_orchestrator.run_stream(request.message):
                payload = json.dumps(event)
                print(f"[WebServer] Yielding: {payload}")
                yield {"event": "step", "data": payload}
                if event["type"] == "answer_done":
                     yield {"event": "message", "data": event["content"]}
            yield {"event": "done", "data": "[DONE]"}
        except Exception as e:
            logger.error(f"Stream Error: {e}")
            import traceback
            traceback.print_exc()
            yield {"event": "error", "data": str(e)}

    return EventSourceResponse(event_generator())

@app.websocket("/ws/chat/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    
    try:
        active_orchestrator = get_orchestrator(session_id)
        # Send connection ack
        await websocket.send_json({"type": "system", "content": f"Connected to session {session_id}"})
        
        while True:
            data = await websocket.receive_text()
            
            # Send Input Ack
            await websocket.send_json({"type": "input_ack", "content": "Processing..."})
            
            try:
                # Stream the response
                async for event in active_orchestrator.run_stream(data):
                    # Direct JSON send
                    await websocket.send_json(event)
                    
            except Exception as e:
                logger.error(f"Orchestrator Error: {e}")
                await websocket.send_json({"type": "error", "content": str(e)})
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket Error: {e}")
        try:
             await websocket.close()
        except: pass


# --- Simple MCP SSE Tunnel (Stub) ---
@app.get("/sse")
async def mcp_sse(request: Request):
    """
    Endpoint for MCP Clients to connect via SSE.
    """
    async def notification_generator():
        yield {"event": "endpoint", "data": "/messages"}
        # Keep alive
        while True:
            await asyncio.sleep(10)
            yield {"event": "ping", "data": "pong"}
            
    return EventSourceResponse(notification_generator())

@app.post("/messages")
async def mcp_messages(request: Request):
    """
    Handle MCP Protocol messages (JSON-RPC).
    This needs to map RPC calls to `global_registry`.
    """
    # Parse JSON-RPC
    # Provide tools: list_tools, call_tool
    # This requires implementing MCP Server logic here. 
    # For now, we leave this as a placeholder or we can use the mcp library's SSE server adapter if available.
    return {"jsonrpc": "2.0", "result": {}, "id": 1} # Dummy


# --- Agent Communication API (for Claude MCP Client) ---
class AgentStatusRequest(BaseModel):
    agent_id: str
    status: str  # in_progress, completed, failed, need_help, blocked
    message: str
    result: Optional[str] = None

# Store for agent status reports
agent_status_store: Dict[str, Dict[str, Any]] = {}

@app.post("/api/agent/status")
async def report_agent_status(request: AgentStatusRequest):
    """
    Receive status reports from sub-agents (like Claude).
    """
    agent_status_store[request.agent_id] = {
        "status": request.status,
        "message": request.message,
        "result": request.result,
        "timestamp": asyncio.get_event_loop().time()
    }
    logger.info(f"Agent Status Report: [{request.agent_id}] {request.status} - {request.message}")
    return {"success": True, "agent_id": request.agent_id}


@app.get("/api/agent/context")
async def get_agent_context(agent_id: str):
    """
    Get task context for a sub-agent.
    Currently returns empty context (can be extended to track assigned tasks).
    """
    # TODO: Implement task assignment tracking
    return {
        "agent_id": agent_id,
        "task": None,
        "context": None,
        "message": "No active task assigned to this agent."
    }


@app.get("/api/capabilities")
async def list_capabilities():
    """
    List all available capabilities (tools and agents) in the system.
    """
    return {
        "capabilities": global_registry.get_capabilities_tree_string(),
        "tools": [
            {"name": name, "type": "tool"} 
            for name in global_registry.get_all_tool_schemas()
        ]
    }


# --- Mount Static Frontend ---

app.mount("/", StaticFiles(directory="src/server/static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
