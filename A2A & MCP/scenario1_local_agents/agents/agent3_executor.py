"""
Executor Agent - Agent 3 for Scenario 1
========================================
This agent executes file operations and other tasks using the File Operations MCP server.

Capabilities:
- Connects to File Operations MCP server
- Receives execution requests from Coordinator Agent
- Performs file operations (read, write, delete, list)
- Returns execution results via A2A communication

Role: Task Executor
"""

import os
import asyncio
from typing import Any, Dict
from openai import AzureOpenAI
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()


class ExecutorAgent:
    """Agent focused on executing tasks and file operations using MCP File tools."""
    
    def __init__(self):
        """Initialize the Executor Agent."""
        self.agent_id = "executor-agent"
        self.name = "Executor Agent"
        self.role = "Task Executor - File Operations"
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
        # Agent instructions
        self.system_instructions = """
        You are an Executor Agent specializing in task execution and file operations.
        
        Your responsibilities:
        1. Execute tasks delegated by the Coordinator Agent
        2. Perform file operations using File MCP tools
        3. Ensure operations complete successfully
        4. Report results back to Coordinator via A2A
        
        Available MCP Tools:
        - read_file(filename): Read contents of a file
        - write_file(filename, content, append): Write content to a file
        - list_files(directory, pattern): List files in a directory
        - delete_file(filename): Delete a file
        - file_info(filename): Get file information
        
        Communication Protocol:
        - You receive execution requests from the Coordinator
        - You execute operations using MCP tools
        - You respond with detailed execution results
        - Include success/failure status and any error messages
        
        Be precise and reliable in your executions.
        Always verify operations completed successfully.
        """
        
        print(f"✅ {self.name} initialized (ID: {self.agent_id})")
        print(f"   Role: {self.role}")
    
    def process_execution_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an execution request from the Coordinator Agent.
        
        Args:
            request: Dictionary containing execution request details
                - operation: Type of operation (e.g., "write_file")
                - parameters: Operation parameters
                - content: Content to process (if applicable)
        
        Returns:
            Dictionary containing execution results
        """
        operation = request.get("operation", "unknown")
        parameters = request.get("parameters", {})
        content = request.get("content", "")
        
        print(f"\n⚙️  {self.name} received execution request:")
        print(f"   Operation: {operation}")
        print(f"   Parameters: {parameters}")
        
        try:
            # Execute the requested operation
            result = self._execute_operation(operation, parameters, content)
            
            return {
                "agent_id": self.agent_id,
                "status": "success",
                "operation": operation,
                "results": result,
                "metadata": {
                    "tool": "File Operations MCP Server"
                }
            }
        
        except Exception as e:
            print(f"❌ Error executing operation: {e}")
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "operation": operation,
                "error": str(e)
            }
    
    def _execute_operation(self, operation: str, parameters: Dict[str, Any], content: str = "") -> Dict[str, Any]:
        """
        Execute a file operation using the REAL File MCP server.
        
        Args:
            operation: Operation to execute
            parameters: Operation parameters
            content: Content for write operations
        
        Returns:
            Operation result from MCP server
        """
        # Import MCP server tools directly
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from mcp_servers.file_operations_server import write_file, read_file, list_files, delete_file, file_info
        
        filename = parameters.get("filename", "weather_report.txt")
        
        print(f"   🔧 Calling File Operations MCP Server...")
        
        if operation == "write_file":
            print(f"   📝 MCP Tool: write_file('{filename}')")
            # Get content from parameters or use default
            file_content = parameters.get("content", content)
            if not file_content:
                file_content = "Weather data saved at " + str(datetime.now())
            
            # Call REAL MCP tool
            result_message = write_file(filename, file_content, append=False)
            print(f"   ✅ MCP Response: {result_message}")
            
            return {
                "filename": filename,
                "bytes_written": len(file_content),
                "message": result_message,
                "mcp_tool": "write_file"
            }
        
        elif operation == "read_file":
            print(f"   📖 MCP Tool: read_file('{filename}')")
            
            # Call REAL MCP tool
            result_content = read_file(filename)
            print(f"   ✅ MCP Response: File read successfully")
            
            return {
                "filename": filename,
                "content": result_content,
                "bytes_read": len(result_content),
                "mcp_tool": "read_file"
            }
        
        elif operation == "list_files":
            directory = parameters.get("directory", ".")
            pattern = parameters.get("pattern", "*")
            print(f"   📂 MCP Tool: list_files('{directory}', '{pattern}')")
            
            # Call REAL MCP tool
            result_list = list_files(directory, pattern)
            print(f"   ✅ MCP Response: Files listed")
            
            return {
                "directory": directory,
                "file_list": result_list,
                "mcp_tool": "list_files"
            }
        
        elif operation == "delete_file":
            print(f"   🗑️  MCP Tool: delete_file('{filename}')")
            
            # Call REAL MCP tool
            result_message = delete_file(filename)
            print(f"   ✅ MCP Response: {result_message}")
            
            return {
                "filename": filename,
                "message": result_message,
                "mcp_tool": "delete_file"
            }
        
        elif operation == "file_info":
            print(f"   ℹ️  MCP Tool: file_info('{filename}')")
            
            # Call REAL MCP tool
            result_info = file_info(filename)
            print(f"   ✅ MCP Response: File info retrieved")
            
            return {
                "filename": filename,
                "info": result_info,
                "mcp_tool": "file_info"
            }
        
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    async def send_to_coordinator(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send execution results back to the Coordinator Agent via A2A.
        
        Args:
            message: Message to send to coordinator
        
        Returns:
            Acknowledgment from coordinator
        """
        print(f"\n📤 Sending results to Coordinator Agent...")
        print(f"   Operation: {message.get('operation', 'unknown')}")
        print(f"   Status: {message.get('status', 'unknown')}")
        
        # Simulate A2A message transmission
        return {
            "status": "delivered",
            "recipient": "coordinator-agent",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main message handler for incoming A2A messages.
        
        Args:
            message: Incoming message from another agent
        
        Returns:
            Response to send back
        """
        message_type = message.get("type", "unknown")
        sender = message.get("sender", "unknown")
        
        print(f"\n📨 Received message from {sender}")
        print(f"   Type: {message_type}")
        
        if message_type == "execution_request":
            # Process execution request
            result = self.process_execution_request(message.get("data", {}))
            return result
        
        elif message_type == "ping":
            # Health check
            return {
                "agent_id": self.agent_id,
                "status": "active",
                "type": "pong"
            }
        
        else:
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "error": f"Unknown message type: {message_type}"
            }


def main():
    """Main function to run the Executor Agent."""
    print("\n" + "="*60)
    print("🤖 Executor Agent (Agent 3) - Starting...")
    print("="*60)
    
    # Initialize agent
    agent = ExecutorAgent()
    
    # Example 1: Write file operation
    print("\n--- Example 1: Write File ---")
    write_request = {
        "type": "execution_request",
        "sender": "coordinator-agent",
        "data": {
            "operation": "write_file",
            "parameters": {
                "filename": "weather_report.txt"
            },
            "content": "Weather Report:\nTemperature: 72°F\nConditions: Sunny"
        }
    }
    
    response = agent.handle_message(write_request)
    print(f"\n✅ Operation completed!")
    print(f"   Response: {json.dumps(response, indent=2)}")
    
    asyncio.run(agent.send_to_coordinator(response))
    
    # Example 2: List files operation
    print("\n--- Example 2: List Files ---")
    list_request = {
        "type": "execution_request",
        "sender": "coordinator-agent",
        "data": {
            "operation": "list_files",
            "parameters": {
                "directory": ".",
                "pattern": "*.txt"
            }
        }
    }
    
    response = agent.handle_message(list_request)
    print(f"\n✅ Operation completed!")
    print(f"   Files found: {response['results']['count']}")
    
    asyncio.run(agent.send_to_coordinator(response))
    
    print(f"\n✨ {agent.name} demo completed successfully!")


if __name__ == "__main__":
    main()
