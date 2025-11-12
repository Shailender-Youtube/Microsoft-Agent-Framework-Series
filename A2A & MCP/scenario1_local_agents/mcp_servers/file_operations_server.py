"""
MCP File Operations Server for Scenario 1
==========================================
This server provides file operation tools to agents via the Model Context Protocol.

Tools Provided:
- read_file: Read contents of a file
- write_file: Write content to a file
- list_files: List files in a directory
- delete_file: Delete a file
- file_info: Get information about a file

Usage:
    python file_operations_server.py
"""

import os
import pathlib
from datetime import datetime
from typing import List
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("file-operations-server")

# Base directory for file operations (for security, restrict to a specific folder)
BASE_DIR = pathlib.Path("./agent_workspace")
BASE_DIR.mkdir(exist_ok=True)


def get_safe_path(filename: str) -> pathlib.Path:
    """Get a safe path within the base directory.
    
    Args:
        filename: Requested filename or path
        
    Returns:
        Path object within the base directory
        
    Raises:
        ValueError: If path tries to escape base directory
    """
    requested_path = BASE_DIR / filename
    resolved_path = requested_path.resolve()
    
    # Ensure the path is within BASE_DIR
    if not str(resolved_path).startswith(str(BASE_DIR.resolve())):
        raise ValueError(f"Access denied: Path {filename} is outside allowed directory")
    
    return resolved_path


# MCP Tool: Read File
@mcp.tool()
def read_file(filename: str) -> str:
    """Read and return the contents of a file.

    Args:
        filename: Name of the file to read (relative to workspace)
        
    Returns:
        String containing file contents or error message
    """
    try:
        file_path = get_safe_path(filename)
        
        if not file_path.exists():
            return f"Error: File '{filename}' does not exist."
        
        if not file_path.is_file():
            return f"Error: '{filename}' is not a file."
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return f"Contents of {filename}:\n{content}"
    
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except UnicodeDecodeError:
        return f"Error: Unable to read '{filename}' as text file. It may be a binary file."
    except Exception as e:
        return f"Error reading file: {str(e)}"


# MCP Tool: Write File
@mcp.tool()
def write_file(filename: str, content: str, append: bool = False) -> str:
    """Write content to a file.

    Args:
        filename: Name of the file to write to (relative to workspace)
        content: Content to write to the file
        append: If True, append to file; if False, overwrite (default: False)
        
    Returns:
        Success or error message
    """
    try:
        file_path = get_safe_path(filename)
        
        # Create parent directories if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        action = "appended to" if append else "written to"
        return f"Successfully {action} {filename} ({len(content)} characters)"
    
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


# MCP Tool: List Files
@mcp.tool()
def list_files(directory: str = ".", pattern: str = "*") -> str:
    """List files in a directory.

    Args:
        directory: Directory to list (relative to workspace, default: current)
        pattern: Glob pattern to match files (default: "*" for all files)
        
    Returns:
        String containing list of files or error message
    """
    try:
        dir_path = get_safe_path(directory)
        
        if not dir_path.exists():
            return f"Error: Directory '{directory}' does not exist."
        
        if not dir_path.is_dir():
            return f"Error: '{directory}' is not a directory."
        
        # Get matching files
        files = list(dir_path.glob(pattern))
        
        if not files:
            return f"No files found matching pattern '{pattern}' in {directory}"
        
        # Format file list with details
        file_list = []
        for file_path in sorted(files):
            rel_path = file_path.relative_to(BASE_DIR)
            size = file_path.stat().st_size if file_path.is_file() else 0
            modified = datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            file_type = "DIR" if file_path.is_dir() else "FILE"
            file_list.append(f"{file_type:4} {size:>10} bytes  {modified}  {rel_path}")
        
        return f"Files in {directory}:\n" + "\n".join(file_list)
    
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error listing files: {str(e)}"


# MCP Tool: Delete File
@mcp.tool()
def delete_file(filename: str) -> str:
    """Delete a file.

    Args:
        filename: Name of the file to delete (relative to workspace)
        
    Returns:
        Success or error message
    """
    try:
        file_path = get_safe_path(filename)
        
        if not file_path.exists():
            return f"Error: File '{filename}' does not exist."
        
        if file_path.is_dir():
            return f"Error: '{filename}' is a directory. Use rmdir to remove directories."
        
        file_path.unlink()
        return f"Successfully deleted {filename}"
    
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error deleting file: {str(e)}"


# MCP Tool: File Info
@mcp.tool()
def file_info(filename: str) -> str:
    """Get detailed information about a file.

    Args:
        filename: Name of the file (relative to workspace)
        
    Returns:
        String containing file information
    """
    try:
        file_path = get_safe_path(filename)
        
        if not file_path.exists():
            return f"Error: '{filename}' does not exist."
        
        stat = file_path.stat()
        
        info = f"""
File Information for: {filename}
{'=' * 50}
Type: {'Directory' if file_path.is_dir() else 'File'}
Size: {stat.st_size} bytes
Created: {datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}
Modified: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}
Accessed: {datetime.fromtimestamp(stat.st_atime).strftime('%Y-%m-%d %H:%M:%S')}
Absolute Path: {file_path.resolve()}
"""
        return info
    
    except ValueError as e:
        return f"Security Error: {str(e)}"
    except Exception as e:
        return f"Error getting file info: {str(e)}"


def main():
    """Run the MCP file operations server."""
    port = int(os.getenv("MCP_FILE_SERVER_PORT", "8002"))
    
    print(f"📁 Starting File Operations MCP Server on port {port}")
    print(f"📡 Server name: {mcp.name}")
    print(f"📂 Workspace directory: {BASE_DIR.resolve()}")
    print(f"🔧 Available tools: read_file, write_file, list_files, delete_file, file_info")
    print(f"🚀 Server ready for agent connections...")
    
    # Run server with stdio transport (for local agent connections)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
