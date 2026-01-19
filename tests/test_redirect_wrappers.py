"""
Tests for redirect wrapper tools
"""

import pytest
import sys
import os
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

os.chdir(Path(__file__).parent.parent.parent)

from src.utils.loader import load_capabilities  # noqa: E402
from src.runtime_tools.redirect_wrapper_tools import (  # noqa: E402
    RedirectToFileTool,
    RedirectToMemTool,
    RedirectToFileAndMemTool,
)
from src.runtime_tools.shared_memory import get_shared_memory, reset_shared_memory  # noqa: E402
from src.runtime_tools.shared_fs_tools import (  # noqa: E402
    SharedReadFileTool,
    SharedDeleteFileTool,
)

load_capabilities()  # noqa: E402


@pytest.fixture(autouse=True)
def reset_state():
    """Reset memory and clean up files before each test"""
    reset_shared_memory()
    yield
    reset_shared_memory()


@pytest.mark.asyncio
async def test_redirect_to_file_basic():
    """Test basic redirect to file functionality"""
    tool = RedirectToFileTool()
    read_tool = SharedReadFileTool()
    delete_tool = SharedDeleteFileTool()

    # Redirect get_system_info output to file
    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        file="test_output.txt",
        mode="w",
    )

    # Check that result contains redirect message
    assert "Output redirected to" in result
    assert ".OneAgent/test_output.txt" in result

    # Verify file was created and has content - use SharedReadFileTool directly
    file_content = await read_tool.execute(filename="test_output.txt")
    assert file_content is not None
    assert "system" in file_content.lower()

    # Cleanup
    await delete_tool.execute(filename="test_output.txt")


@pytest.mark.asyncio
async def test_redirect_to_file_append():
    """Test append mode for file redirection"""
    tool = RedirectToFileTool()
    read_tool = SharedReadFileTool()
    delete_tool = SharedDeleteFileTool()

    # First write
    await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        file="append_test.txt",
        mode="w",
    )

    # Append more content
    await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        file="append_test.txt",
        mode="a",
    )

    # Verify file has content from both writes
    file_content = await read_tool.execute(filename="append_test.txt")
    assert file_content is not None
    assert "system" in file_content.lower()

    # Cleanup
    await delete_tool.execute(filename="append_test.txt")


@pytest.mark.asyncio
async def test_redirect_to_file_silent():
    """Test silent mode - no redirect message in output"""
    tool = RedirectToFileTool()
    read_tool = SharedReadFileTool()
    delete_tool = SharedDeleteFileTool()

    # Redirect with silent=True
    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        file="silent_test.txt",
        mode="w",
        silent=True,
    )

    # Result should NOT contain redirect message
    assert "Output redirected to" not in result

    # But file should still be created
    file_content = await read_tool.execute(filename="silent_test.txt")
    assert file_content is not None

    # Cleanup
    await delete_tool.execute(filename="silent_test.txt")


@pytest.mark.asyncio
async def test_return_original_false():
    """Test return_original=False returns empty string and file is still created"""
    tool = RedirectToFileTool()
    read_tool = SharedReadFileTool()
    delete_tool = SharedDeleteFileTool()

    # Redirect with return_original=False
    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        file="empty_test.txt",
        mode="w",
        return_original=False,
    )

    # Should return empty string
    assert result == ""

    # But file should be created with content
    file_content = await read_tool.execute(filename="empty_test.txt")
    assert file_content is not None
    assert "system" in file_content.lower()

    # Cleanup
    await delete_tool.execute(filename="empty_test.txt")


@pytest.mark.asyncio
async def test_redirect_to_mem_basic():
    """Test basic redirect to shared memory"""
    tool = RedirectToMemTool()

    # Redirect to memory
    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
    )

    # Check result message
    assert "[Output copied to shared memory" in result

    # Verify memory has content
    memory_content = get_shared_memory().read()
    assert "system" in memory_content.lower()


@pytest.mark.asyncio
async def test_redirect_to_mem_silent():
    """Test silent mode for memory redirect"""
    tool = RedirectToMemTool()

    # Redirect with silent=True
    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        silent=True,
    )

    # Result should NOT contain redirect message
    assert "Output redirected to shared memory" not in result

    # But memory should still have content
    memory_content = get_shared_memory().read()
    assert "system" in memory_content.lower()


@pytest.mark.asyncio
async def test_redirect_to_both():
    """Test redirect to both file and memory"""
    tool = RedirectToFileAndMemTool()
    read_tool = SharedReadFileTool()
    delete_tool = SharedDeleteFileTool()

    # Redirect to both
    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        file="both_test.txt",
        mode="w",
    )

    # Check result message mentions both
    assert "Output redirected to" in result
    assert ".OneAgent/both_test.txt" in result
    assert "shared memory" in result.lower()

    # Verify file was created
    file_content = await read_tool.execute(filename="both_test.txt")
    assert file_content is not None
    assert "system" in file_content.lower()

    # Verify memory has content
    memory_content = get_shared_memory().read()
    assert "system" in memory_content.lower()

    # Cleanup
    await delete_tool.execute(filename="both_test.txt")


@pytest.mark.asyncio
async def test_invalid_tool_name():
    """Test with invalid tool name"""
    tool = RedirectToFileTool()

    result = await tool.execute(
        tool_name="nonexistent_tool",
        tool_params={},
        file="test.txt",
        mode="w",
    )

    # Should return error message
    assert "Error: Tool 'nonexistent_tool' not found" in result


@pytest.mark.asyncio
async def test_missing_required_params():
    """Test with missing required parameters (file is missing)"""
    tool = RedirectToFileTool()

    result = await tool.execute(
        tool_name="get_system_info",
        tool_params={},
        mode="w",
    )

    # Should return error about missing parameters
    assert "Error" in result
    assert "required parameters" in result.lower()
    assert "'file' are required" in result.lower()
