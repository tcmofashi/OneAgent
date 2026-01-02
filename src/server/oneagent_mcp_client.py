#!/usr/bin/env python3
"""
OneAgent MCP Server for Claude Code

这是一个纯 Python 实现的 MCP 服务器，专门用于让 Claude Code 作为子代理与 OneAgent 框架通信。
通过读取 OneAgent 的 config.toml 获取服务器地址配置。

使用场景：
- Claude 被 OneAgent 调用执行任务时，使用此 MCP 向 OneAgent 报告状态
- 平时不需要调用此 MCP

启动方式：
    python oneagent_mcp_client.py --agent-name "claude_agent"
"""

import asyncio
import argparse
import sys
import json
import urllib.request
import urllib.error
from typing import Any, Dict, List
from pathlib import Path

# --- MCP SDK Imports ---
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
except ImportError:
    print("[OneAgent MCP] Error: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

try:
    import toml
except ImportError:
    print("[OneAgent MCP] Error: toml package not installed. Run: pip install toml", file=sys.stderr)
    sys.exit(1)


# --- Configuration from OneAgent config.toml ---
def load_server_config() -> tuple[str, int]:
    """
    从 OneAgent 的 config.toml 读取服务器配置。
    Returns (host, port).
    """
    # 查找配置文件路径
    script_dir = Path(__file__).parent
    config_path = script_dir.parent.parent / "config" / "config.toml"
    
    if not config_path.exists():
        print(f"[OneAgent MCP] Warning: config.toml not found at {config_path}, using defaults", file=sys.stderr)
        return "localhost", 8000
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = toml.load(f)
        
        server_config = config.get("server", {})
        host = server_config.get("host", "localhost")
        port = server_config.get("port", 8000)
        return host, port
    except Exception as e:
        print(f"[OneAgent MCP] Warning: Failed to load config: {e}, using defaults", file=sys.stderr)
        return "localhost", 8000


# --- Load Configuration ---
SERVER_HOST, SERVER_PORT = load_server_config()
ONEAGENT_SERVER_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
AGENT_IDENTITY = "claude_agent"


def http_post(url: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simple HTTP POST request using urllib (no external dependencies).
    """
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "detail": e.read().decode('utf-8', errors='replace')}
    except urllib.error.URLError as e:
        return {"error": f"URL Error: {e.reason}"}
    except Exception as e:
        return {"error": str(e)}


# --- Standard Sub-Agent Tool Definition ---
TOOLS = {
    "report_status": {
        "name": "report_status",
        "description": """Report the final status of your task execution.
Use this to finish your work, report errors, or REJECT tasks that are out of your scope.

重要说明：
- 此工具仅在被 OneAgent 调用执行任务时使用
- 平时对话中不需要调用此工具""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["SUCCESS", "FAILURE", "REJECTED", "INTERRUPTED"],
                    "description": "The outcome of the task. Use INTERRUPTED to ask for help/upstream tools."
                },
                "result": {
                    "type": "string",
                    "description": "The result of the execution (if SUCCESS) or error message (if FAILURE)."
                },
                "reason": {
                    "type": "string",
                    "description": "Detailed reason for FAILURE or REJECTED."
                },
                "mismatch_detail": {
                    "type": "string",
                    "description": "If status is REJECTED, explain WHY this task is out of your scope."
                }
            },
            "required": ["status", "result"]
        }
    }
}


async def execute_tool(name: str, arguments: dict) -> str:
    """
    Execute a tool by calling OneAgent HTTP API.
    """
    if name == "report_status":
        status = arguments.get("status", "SUCCESS")
        result = arguments.get("result", "")
        reason = arguments.get("reason", "")
        mismatch_detail = arguments.get("mismatch_detail", "")
        
        output = f"[{status}] {result}"
        if reason:
            output += f"\nReason: {reason}"
        if mismatch_detail:
            output += f"\nMismatch: {mismatch_detail}"
        
        # Report to OneAgent via HTTP
        url = f"{ONEAGENT_SERVER_URL}/api/agent/status"
        payload = {
            "agent_id": AGENT_IDENTITY,
            "status": status,
            "message": output,
            "result": result
        }
        
        api_result = http_post(url, payload)
        
        if "error" in api_result:
            return f"{output}\n(Note: Failed to report to OneAgent server: {api_result.get('error')})"
        
        return output
    
    else:
        return f"Unknown tool: {name}"


async def run_mcp_server():
    """
    Run the MCP server using stdio transport.
    """
    server = Server(name="oneagent-mcp")

    @server.list_tools()
    async def list_tools() -> List[Tool]:
        tools_list = []
        for name, tool_def in TOOLS.items():
            tools_list.append(
                Tool(
                    name=tool_def["name"],
                    description=tool_def["description"],
                    inputSchema=tool_def["inputSchema"]
                )
            )
        return tools_list

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> List[TextContent | ImageContent | EmbeddedResource]:
        if name not in TOOLS:
            raise ValueError(f"Tool {name} not found")
        
        print(f"[OneAgent Runtime] [Agent:{AGENT_IDENTITY}] Calling {name}...", file=sys.stderr, flush=True)
        try:
            result = await execute_tool(name, arguments)
            print(f"[OneAgent Runtime] [Agent:{AGENT_IDENTITY}] {name} Success", file=sys.stderr, flush=True)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            print(f"[OneAgent Runtime] [Agent:{AGENT_IDENTITY}] {name} Failed: {e}", file=sys.stderr, flush=True)
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    print(f"[OneAgent Runtime] Starting MCP (Server: {ONEAGENT_SERVER_URL})", file=sys.stderr, flush=True)
    print(f"[OneAgent Runtime] Agent Identity: {AGENT_IDENTITY}", file=sys.stderr, flush=True)
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


def main():
    global AGENT_IDENTITY
    
    parser = argparse.ArgumentParser(
        description="OneAgent Runtime MCP Server for Claude Code",
        epilog=f"从 config.toml 读取服务器配置 (当前: {ONEAGENT_SERVER_URL})"
    )
    parser.add_argument(
        "--agent-name", 
        type=str, 
        default="claude_agent",
        help="Identity of the sub-agent"
    )
    
    args = parser.parse_args()
    AGENT_IDENTITY = args.agent_name
    
    print(f"[OneAgent Runtime] Initializing: {AGENT_IDENTITY}", file=sys.stderr, flush=True)
    asyncio.run(run_mcp_server())


if __name__ == "__main__":
    main()
