"""
Shared File System Tools for OneAgent Runtime Tools.

Provides CRUD operations for files within .OneAgent directory for
all sub-agents to share and persist data.

Security: All file operations are restricted to .OneAgent directory.
Agents cannot access files outside this sandbox.
"""

import os
import glob as glob_module
from pathlib import Path
from typing import Dict, Any, Optional

from src.core.capability import BaseTool


# Resolve .OneAgent directory relative to project root
# shared_fs_tools.py is at: src/runtime_tools/shared_fs_tools.py
# Need 4 .parent calls to reach project root: runtime_tools -> src -> OneAgent
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ONEAGENT_DIR = PROJECT_ROOT / ".OneAgent"


def _ensure_oneagent_dir():
    """Ensure .OneAgent directory exists."""
    ONEAGENT_DIR.mkdir(parents=True, exist_ok=True)


def _validate_path(filename: str) -> tuple[bool, Path, str]:
    """
    Validate filename is safe and within .OneAgent directory.

    Returns:
        (is_valid, full_path, error_message)
    """
    # Reject absolute paths
    if os.path.isabs(filename):
        return (
            False,
            Path(),
            "Absolute paths are not allowed. Use relative paths within .OneAgent/ directory.",
        )

    # Reject empty filenames
    if not filename or not filename.strip():
        return False, Path(), "Filename cannot be empty."

    # Resolve the full path
    _ensure_oneagent_dir()
    full_path = (ONEAGENT_DIR / filename).resolve()

    # Security: Ensure path doesn't escape .OneAgent directory
    try:
        full_path.relative_to(ONEAGENT_DIR.resolve())
    except ValueError:
        return (
            False,
            Path(),
            f"Path escapes .OneAgent directory. You can only access files within .OneAgent/. Attempted: {filename}",
        )

    return True, full_path, ""


class SharedSaveToFileTool(BaseTool):
    """Save content to a file in the .OneAgent directory."""

    name: str = "shared_save_to_file"
    description: str = """Save content to a file in the .OneAgent/ directory.

Use this to persist data that needs to be shared between agents.

IMPORTANT:
- Files can ONLY be saved to .OneAgent/ directory
- Use relative paths (e.g., "result.txt", "data/output.json")
- Subdirectories will be created automatically
- Default mode is 'write' (overwrites existing file)
- Use mode='append' to add to existing file"""

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Relative path to file within .OneAgent/ (e.g., 'result.txt', 'data/output.json')",
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file",
            },
            "mode": {
                "type": "string",
                "enum": ["write", "append"],
                "description": "Write mode: 'write' (overwrite) or 'append' (add to end). Default: 'write'",
            },
        },
        "required": ["filename", "content"],
    }

    async def execute(self, filename: str, content: str, mode: str = "write") -> str:
        try:
            # Validate path
            is_valid, full_path, error = _validate_path(filename)
            if not is_valid:
                return f"Error: {error}"

            # Ensure parent directories exist
            full_path.parent.mkdir(parents=True, exist_ok=True)

            # Determine write mode
            file_mode = "a" if mode == "append" else "w"

            # Write content
            with open(full_path, file_mode, encoding="utf-8") as f:
                f.write(content)

            action = "appended to" if mode == "append" else "saved to"
            return f"Successfully {action} file: .OneAgent/{filename} ({len(content)} characters)"

        except Exception as e:
            return f"Error saving file: {str(e)}"


class SharedReadFileTool(BaseTool):
    """Read content from a file in the .OneAgent directory."""

    name: str = "shared_read_file"
    description: str = """Read content from a file in the .OneAgent/ directory.

IMPORTANT:
- Files can ONLY be read from .OneAgent/ directory
- Use relative paths (e.g., "result.txt", "data/output.json")
- For large files, use offset and limit for pagination"""

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Relative path to file within .OneAgent/ (e.g., 'result.txt', 'data/output.json')",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-indexed). Default: 0",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read. Default: all lines",
            },
        },
        "required": ["filename"],
    }

    async def execute(
        self, filename: str, offset: int = 0, limit: Optional[int] = None
    ) -> str:
        try:
            # Validate path
            is_valid, full_path, error = _validate_path(filename)
            if not is_valid:
                return f"Error: {error}"

            # Check file exists
            if not full_path.exists():
                return f"Error: File not found: .OneAgent/{filename}"

            if not full_path.is_file():
                return f"Error: Path is not a file: .OneAgent/{filename}"

            # Read content
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            total_lines = len(lines)

            # Apply offset and limit
            if offset < 0:
                offset = 0

            if limit is not None and limit > 0:
                selected_lines = lines[offset : offset + limit]
            else:
                selected_lines = lines[offset:]

            content = "".join(selected_lines)

            # Build response
            if offset > 0 or limit is not None:
                end_line = offset + len(selected_lines)
                return f"File: .OneAgent/{filename} (lines {offset + 1}-{end_line} of {total_lines})\n\n{content}"
            else:
                return f"File: .OneAgent/{filename} ({total_lines} lines)\n\n{content}"

        except UnicodeDecodeError:
            return f"Error: File is not a text file or uses unsupported encoding: .OneAgent/{filename}"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class SharedListFilesTool(BaseTool):
    """List files in the .OneAgent directory."""

    name: str = "shared_list_files"
    description: str = """List files in the .OneAgent/ directory.

Returns a list of all files (and optionally subdirectories) in the .OneAgent/ directory.
Use the pattern parameter for glob-style filtering (e.g., "*.txt", "data/*.json")."""

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to filter files (e.g., '*.txt', '**/*.json'). Default: '*' (all files)",
            },
            "include_dirs": {
                "type": "boolean",
                "description": "Whether to include directories in the listing. Default: false",
            },
        },
    }

    async def execute(self, pattern: str = "*", include_dirs: bool = False) -> str:
        try:
            _ensure_oneagent_dir()

            # Use glob to find matching files
            search_pattern = ONEAGENT_DIR / pattern
            matches = list(glob_module.glob(str(search_pattern), recursive=True))

            # Filter and format results
            results = []
            for match_path in matches:
                path = Path(match_path)

                # Skip directories unless requested
                if path.is_dir() and not include_dirs:
                    continue

                # Get relative path from .OneAgent dir
                try:
                    rel_path = path.relative_to(ONEAGENT_DIR)
                except ValueError:
                    continue

                # Add type indicator and size
                if path.is_dir():
                    results.append(f"[DIR]  {rel_path}/")
                else:
                    size = path.stat().st_size
                    if size < 1024:
                        size_str = f"{size} B"
                    elif size < 1024 * 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size / (1024 * 1024):.1f} MB"
                    results.append(f"[FILE] {rel_path} ({size_str})")

            if not results:
                return f"No files found in .OneAgent/ matching pattern: {pattern}"

            results.sort()
            return f"Files in .OneAgent/ (pattern: {pattern}):\n\n" + "\n".join(results)

        except Exception as e:
            return f"Error listing files: {str(e)}"


class SharedDeleteFileTool(BaseTool):
    """Delete a file from the .OneAgent directory."""

    name: str = "shared_delete_file"
    description: str = """Delete a file from the .OneAgent/ directory.

IMPORTANT:
- Files can ONLY be deleted from .OneAgent/ directory
- Use relative paths (e.g., "result.txt", "data/output.json")
- Cannot delete directories (only files)"""

    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Relative path to file within .OneAgent/ to delete",
            }
        },
        "required": ["filename"],
    }

    async def execute(self, filename: str) -> str:
        try:
            # Validate path
            is_valid, full_path, error = _validate_path(filename)
            if not is_valid:
                return f"Error: {error}"

            # Check file exists
            if not full_path.exists():
                return f"Error: File not found: .OneAgent/{filename}"

            if full_path.is_dir():
                return f"Error: Cannot delete directories. Path is a directory: .OneAgent/{filename}"

            # Delete file
            full_path.unlink()

            return f"Successfully deleted file: .OneAgent/{filename}"

        except PermissionError:
            return f"Error: Permission denied when deleting: .OneAgent/{filename}"
        except Exception as e:
            return f"Error deleting file: {str(e)}"
