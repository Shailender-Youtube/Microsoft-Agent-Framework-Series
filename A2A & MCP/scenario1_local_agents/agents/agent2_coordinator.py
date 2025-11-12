"""
Coordinator Agent - Agent 2 for Scenario 1
===========================================
This agent orchestrates the workflow between Research Agent and Executor Agent.

Capabilities:
- Receives user requests
- Delegates research tasks to Research Agent
- Delegates execution tasks to Executor Agent
- Coordinates multi-agent workflows
- Has access to both Weather and File MCP servers

Role: Workflow Orchestrator
"""

import os
import asyncio
from typing import Any, Dict, List
from openai import AzureOpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()


class CoordinatorAgent:
    """Agent responsible for orchestrating workflows between other agents."""
    
    def __init__(self, research_agent=None, executor_agent=None):
        """Initialize the Coordinator Agent with optional agent references."""
        self.agent_id = "coordinator-agent"
        self.name = "Coordinator Agent"
        self.role = "Workflow Orchestrator"
        
        # Store references to other agents for real A2A communication
        self.research_agent = research_agent
        self.executor_agent = executor_agent
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
        # Agent instructions
        self.system_instructions = """
        You are a Coordinator Agent responsible for orchestrating multi-agent workflows.
        
        Your responsibilities:
        1. Receive and analyze user requests
        2. Break down complex tasks into subtasks
        3. Delegate subtasks to appropriate agents:
           - Research Agent: For information gathering and weather research
           - Executor Agent: For file operations and task execution
        4. Coordinate communication between agents via A2A protocol
        5. Aggregate results and respond to user
        
        Available Agents:
        - Research Agent (research-agent): Weather research and information gathering
        - Executor Agent (executor-agent): File operations and task execution
        
        Available MCP Tools (Direct Access):
        - Weather Server: get_weather, get_forecast, get_alerts
        - File Server: read_file, write_file, list_files, delete_file, file_info
        
        Communication Protocol:
        - Send A2A messages to delegate tasks
        - Wait for responses from agents
        - Aggregate and synthesize results
        - Provide clear, actionable responses to users
        
        Decision Making:
        - Analyze task complexity
        - Determine optimal agent allocation
        - Handle failures gracefully
        - Ensure all subtasks complete before responding
        """
        
        print(f"✅ {self.name} initialized (ID: {self.agent_id})")
        print(f"   Role: {self.role}")
    
    async def process_user_request(self, user_request: str) -> Dict[str, Any]:
        """
        Process a user request and orchestrate agent workflow.
        
        Args:
            user_request: Natural language request from user
        
        Returns:
            Dictionary containing the final response
        """
        print(f"\n👤 User Request: {user_request}")
        print(f"🤔 Analyzing request and planning workflow...")
        
        # Analyze the request and determine workflow
        workflow_plan = self._plan_workflow(user_request)
        
        print(f"\n📋 Workflow Plan:")
        for i, step in enumerate(workflow_plan["steps"], 1):
            print(f"   {i}. {step['action']} (Agent: {step['agent']})")
        
        # Execute workflow
        results = await self._execute_workflow(workflow_plan)
        
        # Aggregate results
        final_response = self._aggregate_results(results)
        
        return final_response
    
    def _plan_workflow(self, user_request: str) -> Dict[str, Any]:
        """
        Analyze user request and create a workflow plan.
        
        Args:
            user_request: User's request
        
        Returns:
            Workflow plan with steps
        """
        # Simple workflow planning logic
        # In production, this would use LLM for intelligent planning
        
        request_lower = user_request.lower()
        steps = []
        
        # Check if weather research is needed
        if any(word in request_lower for word in ["weather", "temperature", "forecast", "climate"]):
            steps.append({
                "agent": "research-agent",
                "action": "Research weather information",
                "type": "research_request",
                "parameters": self._extract_weather_params(user_request)
            })
        
        # Check if file operation is needed
        if any(word in request_lower for word in ["save", "write", "file", "report", "document"]):
            steps.append({
                "agent": "executor-agent",
                "action": "Save data to file",
                "type": "execution_request",
                "parameters": {
                    "operation": "write_file",
                    "filename": "weather_report.txt"
                }
            })
        
        return {
            "request": user_request,
            "steps": steps,
            "total_steps": len(steps)
        }
    
    def _extract_weather_params(self, request: str) -> Dict[str, Any]:
        """
        Extract weather-related parameters from request.
        
        Args:
            request: User request
        
        Returns:
            Dictionary of parameters (city, country)
        """
        # Simple extraction logic for Australian cities
        # In production, use NER or LLM for extraction
        
        australian_cities = {
            "melbourne": {"city": "Melbourne", "country": "Australia"},
            "sydney": {"city": "Sydney", "country": "Australia"},
            "brisbane": {"city": "Brisbane", "country": "Australia"},
            "perth": {"city": "Perth", "country": "Australia"},
            "adelaide": {"city": "Adelaide", "country": "Australia"},
            "canberra": {"city": "Canberra", "country": "Australia"},
        }
        
        request_lower = request.lower()
        
        # Check for Australian cities
        for city_key, params in australian_cities.items():
            if city_key in request_lower:
                return params
        
        # Check if "australia" is mentioned - default to Melbourne
        if "australia" in request_lower:
            return {"city": "Melbourne", "country": "Australia"}
        
        # Default fallback
        return {"city": "Melbourne", "country": "Australia"}
    
    async def _execute_workflow(self, workflow_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute the workflow plan by coordinating with agents.
        
        Args:
            workflow_plan: Planned workflow steps
        
        Returns:
            List of results from each step
        """
        results = []
        weather_data = None
        
        for i, step in enumerate(workflow_plan["steps"], 1):
            print(f"\n🚀 Executing Step {i}/{workflow_plan['total_steps']}")
            print(f"   Agent: {step['agent']}")
            print(f"   Action: {step['action']}")
            
            # Prepare data for this step
            step_data = step.get("parameters", {})
            
            # If this is a file operation and we have weather data, include it
            if step["agent"] == "executor-agent" and weather_data:
                step_data["content"] = weather_data
            
            # Send A2A message to agent
            result = await self._send_to_agent(
                agent_id=step["agent"],
                message_type=step["type"],
                data=step_data
            )
            
            # Store weather data if this was a research step
            if step["agent"] == "research-agent" and result.get("status") == "success":
                weather_info = result.get("results", {})
                if "weather_data" in weather_info:
                    weather_data = weather_info["weather_data"]
            
            results.append(result)
            
            # Simulate processing time
            await asyncio.sleep(0.5)
        
        return results
    
    async def _send_to_agent(self, agent_id: str, message_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send A2A message to another agent.
        
        Args:
            agent_id: Target agent ID
            message_type: Type of message
            data: Message data
        
        Returns:
            Response from agent
        """
        message = {
            "sender": self.agent_id,
            "recipient": agent_id,
            "type": message_type,
            "data": data,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        print(f"   📤 Sending A2A message to {agent_id}...")
        print(f"\n   📨 A2A MESSAGE STRUCTURE:")
        print(f"   ┌{'─'*60}┐")
        print(f"   │ Sender:    {message['sender']:<45}│")
        print(f"   │ Recipient: {message['recipient']:<45}│")
        print(f"   │ Type:      {message['type']:<45}│")
        print(f"   │ Data:      {str(message['data'])[:43]:<45}│")
        print(f"   └{'─'*60}┘")
        
        # Call REAL agents if available
        if agent_id == "research-agent" and self.research_agent:
            # Call the actual research agent with real MCP
            result = await self.research_agent.process_research_request({
                "task": "weather_lookup",
                "parameters": data
            })
            
            # Show A2A response
            print(f"\n   📨 A2A RESPONSE RECEIVED:")
            print(f"   ┌{'─'*60}┐")
            print(f"   │ From:      {result.get('agent_id', 'unknown'):<45}│")
            print(f"   │ Status:    {result.get('status', 'unknown'):<45}│")
            print(f"   │ Task:      {result.get('task', 'unknown'):<45}│")
            print(f"   └{'─'*60}┘")
            
            return result
            
        elif agent_id == "executor-agent" and self.executor_agent:
            # Call the actual executor agent with file MCP
            result = self.executor_agent.process_execution_request({
                "operation": data.get("operation", "write_file"),
                "parameters": data,
                "content": data.get("content", "")
            })
            
            # Show A2A response
            print(f"\n   📨 A2A RESPONSE RECEIVED:")
            print(f"   ┌{'─'*60}┐")
            print(f"   │ From:      {result.get('agent_id', 'unknown'):<45}│")
            print(f"   │ Status:    {result.get('status', 'unknown'):<45}│")
            print(f"   │ Operation: {result.get('operation', 'unknown'):<45}│")
            print(f"   └{'─'*60}┘")
            
            return result
        
        # Fallback if agents not connected
        else:
            print(f"   ⚠️ Agent {agent_id} not connected, using simulated response")
            if agent_id == "research-agent":
                return {
                    "agent_id": agent_id,
                    "status": "success",
                    "results": {
                        "city": data.get("city", "Melbourne"),
                        "note": "Simulated - agent not connected"
                    }
                }
            elif agent_id == "executor-agent":
                return {
                    "agent_id": agent_id,
                    "status": "success",
                    "operation": "write_file",
                    "filename": data.get("filename", "output.txt"),
                    "message": "File saved successfully (simulated)"
                }
            
            return {"status": "error", "error": "Unknown agent"}
    
    def _aggregate_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate results from all workflow steps.
        
        Args:
            results: List of results from agents
        
        Returns:
            Aggregated final response
        """
        print(f"\n📊 Aggregating results from {len(results)} steps...")
        
        successful = sum(1 for r in results if r.get("status") == "success")
        
        return {
            "coordinator_id": self.agent_id,
            "status": "completed" if successful == len(results) else "partial_success",
            "total_steps": len(results),
            "successful_steps": successful,
            "results": results,
            "summary": self._create_summary(results)
        }
    
    def _create_summary(self, results: List[Dict[str, Any]]) -> str:
        """
        Create a natural language summary of the workflow results.
        
        Args:
            results: Results from workflow execution
        
        Returns:
            Summary string
        """
        summaries = []
        
        for result in results:
            if result.get("status") == "success":
                if "results" in result:
                    # Weather result from research agent
                    weather_info = result["results"]
                    if "weather_data" in weather_info:
                        # Real weather data
                        city = weather_info.get("city", "Unknown")
                        country = weather_info.get("country", "")
                        summaries.append(f"✅ Retrieved LIVE weather data for {city}, {country}")
                    elif "city" in weather_info:
                        # Fallback format
                        summaries.append(f"✅ Weather data retrieved for {weather_info['city']}")
                    else:
                        summaries.append("✅ Weather data retrieved")
                
                # Check for file operation results
                if "operation" in result and result.get("operation") == "write_file":
                    file_result = result.get("results", {})
                    filename = file_result.get("filename", "file")
                    summaries.append(f"✅ Saved to {filename} via File Operations MCP")
                elif "filename" in result:
                    # Fallback file operation result
                    summaries.append(f"✅ File operation: {result['filename']}")
                
                if not any(x in str(result) for x in ["weather", "filename", "operation"]):
                    summaries.append("✅ Step completed")
        
        return " | ".join(summaries) if summaries else "Workflow completed successfully."
    
    def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle incoming A2A messages from other agents.
        
        Args:
            message: A2A message from another agent
        
        Returns:
            Response message
        """
        print(f"\n📨 Received message from {message.get('sender', 'unknown')}")
        print(f"   Type: {message.get('type', 'unknown')}")
        
        message_type = message.get("type")
        
        if message_type == "ping":
            # Health check response
            print(f"   ✅ {self.name}: active")
            return {
                "sender": self.agent_id,
                "recipient": message.get("sender"),
                "type": "pong",
                "status": "active",
                "message": f"{self.name} is operational"
            }
        
        elif message_type == "workflow_request":
            # Handle workflow delegation request
            print(f"   📋 Received workflow request from {message.get('sender')}")
            data = message.get("data", {})
            return {
                "sender": self.agent_id,
                "recipient": message.get("sender"),
                "type": "workflow_response",
                "status": "accepted",
                "message": "Workflow request accepted"
            }
        
        else:
            # Unknown message type
            return {
                "sender": self.agent_id,
                "recipient": message.get("sender"),
                "type": "error",
                "error": f"Unknown message type: {message_type}"
            }


def main():
    """Main function to run the Coordinator Agent."""
    print("\n" + "="*60)
    print("🤖 Coordinator Agent (Agent 2) - Starting...")
    print("="*60)
    
    # Initialize agent
    agent = CoordinatorAgent()
    
    # Example: Process a user request
    print("\n--- Example User Request ---")
    user_request = "What's the weather in San Francisco and save it to a report?"
    
    # Process request
    response = asyncio.run(agent.process_user_request(user_request))
    
    print(f"\n✅ Workflow completed!")
    print(f"\n📄 Final Response:")
    print(f"   Status: {response['status']}")
    print(f"   Summary: {response['summary']}")
    print(f"   Steps Completed: {response['successful_steps']}/{response['total_steps']}")
    
    print(f"\n✨ {agent.name} demo completed successfully!")


if __name__ == "__main__":
    main()
