"""
Memory I/O Tools for OneAgent Runtime Tools.

Provides standard input/output tools for the 4K shared circular buffer
memory system, allowing all sub-agents to read/write shared information.
"""

from typing import Dict, Any
from src.core.capability import BaseTool
from src.runtime_tools.shared_memory import get_shared_memory


class MemoryWriteTool(BaseTool):
    """Write content to the shared 4K memory buffer."""

    name: str = "memory_write"
    description: str = """Write content to the shared 4K memory buffer (4KB circular buffer).

This buffer is shared across all sub-agents and provides fast temporary storage.

IMPORTANT:
- Buffer size: 4096 characters
- When buffer is full, oldest content is automatically removed (FIFO)
- Content is stored as separate entries with newlines
- Use for quick agent-to-agent communication
- For persistent storage, use file system tools (.OneAgent directory)

Examples:
- "Agent A result: Task completed successfully"
- "Intermediate result: 75% progress achieved"
- "Request: Please process this data..." """

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": "Content to write to shared memory",
            }
        },
        "required": ["content"],
    }

    async def execute(self, **kwargs) -> str:
        content = kwargs.get("content", "")
        try:
            shared_memory = get_shared_memory()
            shared_memory.write(content)

            current_entries = len(shared_memory._buffer)
            return f"Successfully written to shared memory ({len(content)} chars, {current_entries} total entries)"
        except Exception as e:
            return f"Error writing to shared memory: {str(e)}"


class MemoryReadTool(BaseTool):
    """Read content from the shared 4K memory buffer."""

    name: str = "memory_read"
    description: str = """Read content from the shared 4K memory buffer.

You can read all content or specify number of recent entries.

Parameters:
- lines: Number of recent entries to read. If not provided, reads all content.
  Default: None (all entries)"""

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "lines": {
                "type": "integer",
                "description": "Number of recent entries to read. Default: None (read all)",
                "default": None,
            }
        },
    }

    async def execute(self, **kwargs) -> str:
        lines = kwargs.get("lines", None)
        try:
            shared_memory = get_shared_memory()
            content = shared_memory.read(lines=lines)

            if not content:
                return "Shared memory is empty"

            return f"Shared memory content:\n\n{content}"
        except Exception as e:
            return f"Error reading shared memory: {str(e)}"


class MemoryClearTool(BaseTool):
    """Clear all content from the shared 4K memory buffer."""

    name: str = "memory_clear"
    description: str = """Clear all content from the shared 4K memory buffer.

This operation removes ALL entries from the shared memory.
Use with caution - other agents may have stored important data."""

    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> str:
        try:
            shared_memory = get_shared_memory()
            shared_memory.clear()

            return "Successfully cleared shared memory buffer"
        except Exception as e:
            return f"Error clearing shared memory: {str(e)}"


class MemoryInfoTool(BaseTool):
    """Get statistics and information about the shared 4K memory buffer."""

    name: str = "memory_info"
    description: str = """Get statistics and usage information about the shared 4K memory buffer.

Returns:
- total_capacity: Total buffer size in characters
- current_entries: Number of entries currently in buffer
- total_writes: Total number of write operations
- utilization_percent: Buffer utilization percentage
- last_updated: Timestamp of last update"""

    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    async def execute(self, **kwargs) -> str:
        try:
            shared_memory = get_shared_memory()
            info = shared_memory.info()

            return (
                f"Shared Memory Statistics:\n"
                f"- Total Capacity: {info['total_capacity']} characters\n"
                f"- Current Entries: {info['current_entries']}\n"
                f"- Total Writes: {info['total_writes']}\n"
                f"- Utilization: {info['utilization_percent']}%\n"
                f"- Last Updated: {info['last_updated']}"
            )
        except Exception as e:
            return f"Error getting memory info: {str(e)}"
