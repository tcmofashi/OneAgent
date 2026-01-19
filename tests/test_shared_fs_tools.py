"""
Tests for shared file system tools.
"""

import pytest
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

# Change to project root to test properly
os.chdir(Path(__file__).parent.parent.parent.parent)

from src.runtime_tools.shared_fs_tools import (
    SharedSaveToFileTool,
    SharedReadFileTool,
    SharedListFilesTool,
    SharedDeleteFileTool,
)
from src.runtime_tools.shared_memory import reset_shared_memory, get_shared_memory


@pytest.fixture(autouse=True)
def reset_memory():
    """Reset shared memory before each test."""
    reset_shared_memory()
    yield
    reset_shared_memory()


@pytest.mark.asyncio
async def test_save_and_read():
    """Test basic save and read functionality."""
    save_tool = SharedSaveToFileTool()
    read_tool = SharedReadFileTool()

    await save_tool.execute(filename="test.txt", content="Test content line 1\n")
    result = await read_tool.execute(filename="test.txt")

    assert "Test content line 1" in result
    assert "test.txt" in result

    # Cleanup
    await SharedDeleteFileTool().execute(filename="test.txt")


@pytest.mark.asyncio
async def test_append_mode():
    """Test append mode for writing."""
    save_tool = SharedSaveToFileTool()
    read_tool = SharedReadFileTool()

    await save_tool.execute(
        filename="append_test.txt", content="Line 1\n", mode="append"
    )
    await save_tool.execute(
        filename="append_test.txt", content="Line 2\n", mode="append"
    )

    result = await read_tool.execute(filename="append_test.txt")
    lines = result.split("\n")

    assert "Line 1" in result
    assert "Line 2" in result

    # Cleanup
    await SharedDeleteFileTool().execute(filename="append_test.txt")


@pytest.mark.asyncio
async def test_list_files():
    """Test list files functionality."""
    list_tool = SharedListFilesTool()

    result = await list_tool.execute()

    # Deleted files should not appear
    assert "append_test.txt" not in result
    assert "test.txt" not in result


@pytest.mark.asyncio
async def test_delete_nonexistent_file():
    """Test deleting a non-existent file."""
    delete_tool = SharedDeleteFileTool()

    result = await delete_tool.execute(filename="nonexistent.txt")
    assert "Error:" in result


@pytest.mark.asyncio
async def test_path_security_absolute_path():
    """Test that absolute paths are rejected."""
    save_tool = SharedSaveToFileTool()

    result = await save_tool.execute(filename="/etc/passwd", content="malicious")
    assert "Error:" in result
    assert "Absolute paths are not allowed" in result


@pytest.mark.asyncio
async def test_path_security_traversal():
    """Test that path traversal attacks are rejected."""
    save_tool = SharedSaveToFileTool()

    result = await save_tool.execute(
        filename="../../../etc/passwd", content="malicious"
    )
    assert "Error:" in result
    assert "Path escapes" in result


@pytest.mark.asyncio
async def test_create_subdirectory():
    """Test creating files in subdirectories."""
    save_tool = SharedSaveToFileTool()
    read_tool = SharedReadFileTool()

    await save_tool.execute(filename="subdir/nested.txt", content="Nested file content")
    result = await read_tool.execute(filename="subdir/nested.txt")

    assert "subdir" in result
    assert "Nested file content" in result

    # Cleanup
    await SharedDeleteFileTool().execute(filename="subdir/nested.txt")


@pytest.mark.asyncio
async def test_empty_filename():
    """Test handling of empty filename."""
    save_tool = SharedSaveToFileTool()

    result = await save_tool.execute(filename="", content="content")
    assert "Error:" in result
    assert "Filename cannot be empty" in result
