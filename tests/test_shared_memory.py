"""
Tests for shared memory system.
"""

import pytest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))

from src.runtime_tools.shared_memory import get_shared_memory, reset_shared_memory


@pytest.fixture(autouse=True)
def reset_memory():
    """Reset shared memory before each test."""
    reset_shared_memory()
    yield
    reset_shared_memory()


def test_write_and_read():
    """Test basic write and read functionality."""
    shared_memory = get_shared_memory()

    shared_memory.write("Test message 1")
    content = shared_memory.read()
    assert "Test message 1" in content


def test_multiple_writes():
    """Test multiple writes accumulate correctly."""
    shared_memory = get_shared_memory()

    for i in range(5):
        shared_memory.write(f"Message {i}")

    content = shared_memory.read()
    lines = content.split("\n")
    assert len(lines) == 5
    assert "Message 4" in content


def test_fifo_behavior():
    """Test FIFO (First In First Out) behavior when exceeding capacity."""
    # Reset with smaller capacity for testing
    shared_memory = reset_shared_memory(max_size=5)

    # Write 6 messages (capacity is 5)
    for i in range(6):
        shared_memory.write(f"Message {i}")

    content = shared_memory.read()
    lines = content.split("\n")
    assert len(lines) == 5  # Should only have 5 entries
    assert "Message 5" in content  # Latest message exists
    assert "Message 0" not in content  # Oldest message removed


def test_clear_memory():
    """Test clear functionality."""
    shared_memory = get_shared_memory()

    shared_memory.write("Test")
    shared_memory.clear()

    content = shared_memory.read()
    assert content == ""


def test_info():
    """Test info functionality."""
    shared_memory = get_shared_memory()

    info = shared_memory.info()
    assert info["total_capacity"] == 4096
    assert info["current_entries"] == 0
    assert info["utilization_percent"] == 0.0

    # Add some entries
    for i in range(3):
        shared_memory.write(f"Message {i}")

    info = shared_memory.info()
    assert info["current_entries"] == 3


def test_read_last():
    """Test read_last functionality."""
    shared_memory = get_shared_memory()

    for i in range(3):
        shared_memory.write(f"Message {i}")

    last_entry = shared_memory.read_last()
    assert last_entry is not None
    assert "Message 2" in last_entry
