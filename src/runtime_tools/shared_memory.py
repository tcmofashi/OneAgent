"""
Shared Memory System for OneAgent Agents.

Provides a 4K circular buffer as the first level of shared memory
for all sub-agents to communicate and exchange information.
"""

import threading
from collections import deque
from typing import Optional
from datetime import datetime


class SharedMemory:
    """
    Thread-safe 4K circular buffer for agent-to-agent communication.

    Memory Size: 4096 characters (4KB)
    Implementation: collections.deque with maxlen
    Thread Safety: threading.Lock
    """

    def __init__(self, max_size: int = 4096):
        """
        Initialize shared memory buffer.

        Args:
            max_size: Maximum buffer size in characters (default: 4096)
        """
        self._max_size = max_size
        self._buffer = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._write_count = 0

    def write(self, content: str) -> None:
        """
        Write content to shared memory.

        If content exceeds available space, oldest entries are automatically
        removed by the deque (FIFO behavior).

        Args:
            content: String content to write
        """
        with self._lock:
            self._buffer.append(content)
            self._write_count += 1

    def read(self, lines: Optional[int] = None) -> str:
        """
        Read content from shared memory.

        Args:
            lines: Number of recent lines to read. None = all lines

        Returns:
            Concatenated content with newline separator
        """
        with self._lock:
            if lines is None:
                return "\n".join(self._buffer)
            else:
                return "\n".join(list(self._buffer)[-lines:])

    def read_last(self) -> Optional[str]:
        """
        Read the most recent entry from shared memory.

        Returns:
            Last entry as string, or None if buffer is empty
        """
        with self._lock:
            if not self._buffer:
                return None
            return self._buffer[-1]

    def clear(self) -> None:
        """Clear all content from shared memory."""
        with self._lock:
            self._buffer.clear()
            self._write_count = 0

    def info(self) -> dict:
        """
        Get memory statistics.

        Returns:
            Dictionary with usage information
        """
        with self._lock:
            return {
                "total_capacity": self._max_size,
                "current_entries": len(self._buffer),
                "total_writes": self._write_count,
                "last_updated": datetime.now().isoformat(),
                "utilization_percent": round(
                    len(self._buffer) / self._max_size * 100, 2
                ),
            }


# Global singleton instance
_global_shared_memory: Optional[SharedMemory] = None


def get_shared_memory() -> SharedMemory:
    """
    Get the global shared memory instance.

    Returns:
        SharedMemory singleton instance
    """
    global _global_shared_memory
    if _global_shared_memory is None:
        _global_shared_memory = SharedMemory()
    return _global_shared_memory


def reset_shared_memory(max_size: int = 4096) -> SharedMemory:
    """
    Reset the global shared memory instance (useful for testing).

    Args:
        max_size: New buffer size

    Returns:
        New SharedMemory instance
    """
    global _global_shared_memory
    _global_shared_memory = SharedMemory(max_size=max_size)
    return _global_shared_memory
