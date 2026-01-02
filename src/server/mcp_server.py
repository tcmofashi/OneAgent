import asyncio
import argparse
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from src.runtime_tools.report_status import ReportStatusTool

# Global Identity
AGENT_IDENTITY = "unknown"

async def run_mcp_server():
    server = Server(name="oneagent-mcp")

    # Define the Standard Sub-Agent Toolset
    # These are the tools that ANY OneAgent Sub-Agent (Python or CLI) *must* have access to
    # to participate in the OneAgent protocol.
    standard_tools = {
        "report_status": ReportStatusTool()
    }

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """
        List the Standard Sub-Agent Tools.
        External agents (like Claude) use these to communicate with the OneAgent framework.
        """
        tools_list = []
        for name, tool_instance in standard_tools.items():
            tools_list.append(
                Tool(
                    name=tool_instance.name,
                    description=tool_instance.description,
                    inputSchema=tool_instance.parameters
                )
            )
        return tools_list

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent | ImageContent | EmbeddedResource]:
        """
        Execute a standard tool.
        """
        if name not in standard_tools:
            raise ValueError(f"Tool {name} not found in Standard Sub-Agent Toolset")
        
        tool_instance = standard_tools[name]
        
        print(f"[OneAgent Runtime] [Agent:{AGENT_IDENTITY}] Calling {name}...", file=sys.stderr, flush=True)
        try:
            # We execute the tool directly. 
            # Note: For report_status, the result usually needs to be parsed by the Orchestrator.
            # In the CLI context, the CLI agent sees the result text.
            result = await tool_instance.execute(**arguments)
            
            print(f"[OneAgent Runtime] [Agent:{AGENT_IDENTITY}] {name} Success", file=sys.stderr, flush=True)
            return [TextContent(type="text", text=str(result))]
        except Exception as e:
            print(f"[OneAgent Runtime] [Agent:{AGENT_IDENTITY}] {name} Failed: {e}", file=sys.stderr, flush=True)
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    print("[OneAgent Runtime] Starting Standard Sub-Agent Interface...", file=sys.stderr, flush=True)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OneAgent Runtime MCP Server")
    parser.add_argument("--agent-name", type=str, default="anonymous", help="Identity of the sub-agent connecting to the runtime")
    args = parser.parse_args()
    
    AGENT_IDENTITY = args.agent_name
    print(f"[OneAgent Runtime] Initializing for Sub-Agent: {AGENT_IDENTITY}", file=sys.stderr, flush=True)

    asyncio.run(run_mcp_server())
