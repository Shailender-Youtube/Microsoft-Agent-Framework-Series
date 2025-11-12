"""
Research Agent - Agent 1 for Scenario 1
========================================
This agent is responsible for researching and gathering information using the Weather MCP server.

Capabilities:
- Connects to Weather MCP server for weather data
- Receives requests from Coordinator Agent
- Returns research results via A2A communication

Role: Information Gatherer
"""

import os
import asyncio
from typing import Any, Dict
from openai import AzureOpenAI
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()


class ResearchAgent:
    """Agent focused on research and information gathering using MCP Weather tools."""
    
    def __init__(self):
        """Initialize the Research Agent."""
        self.agent_id = "research-agent"
        self.name = "Research Agent"
        self.role = "Information Gatherer - Weather Research"
        
        # Initialize Azure OpenAI client
        self.client = AzureOpenAI(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
        )
        
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        
        # Agent instructions
        self.system_instructions = """
        You are a Research Agent specializing in weather information gathering.
        
        Your responsibilities:
        1. Research weather information when requested by the Coordinator Agent
        2. Use the Weather MCP tools to gather accurate, current data
        3. Provide comprehensive yet concise research summaries
        4. Always cite your data sources (weather API)
        
        Available MCP Tools:
        - get_weather(city, state): Get current weather for a city
        - get_forecast(latitude, longitude): Get detailed forecast
        - get_alerts(state): Get weather alerts for a US state
        
        Communication Protocol:
        - You receive requests via A2A messages from the Coordinator
        - You respond with structured research data
        - Include confidence levels and data timestamps when available
        
        Be thorough but efficient in your research.
        """
        
        print(f"✅ {self.name} initialized (ID: {self.agent_id})")
        print(f"   Role: {self.role}")
    
    async def process_research_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a research request from the Coordinator Agent.
        
        Args:
            request: Dictionary containing research request details
                - task: Type of research (e.g., "weather_lookup")
                - parameters: Task parameters (e.g., city, state)
                - context: Additional context
        
        Returns:
            Dictionary containing research results
        """
        task = request.get("task", "unknown")
        parameters = request.get("parameters", {})
        
        print(f"\n📊 {self.name} received research request:")
        print(f"   Task: {task}")
        print(f"   Parameters: {parameters}")
        
        try:
            # Call the REAL MCP Weather Server for live data
            result = await self._call_weather_mcp(parameters)
            
            return {
                "agent_id": self.agent_id,
                "status": "success",
                "task": task,
                "results": result,
                "metadata": {
                    "source": "Weather MCP Server (Real API)",
                    "confidence": "high"
                }
            }
        
        except Exception as e:
            print(f"❌ Error processing research request: {e}")
            return {
                "agent_id": self.agent_id,
                "status": "error",
                "task": task,
                "error": str(e)
            }
    
    async def _call_weather_mcp(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call the real Weather MCP server to get live weather data.
        
        Args:
            parameters: Parameters for the weather lookup (city, country)
        
        Returns:
            Real weather data from Open-Meteo API via MCP server
        """
        city = parameters.get("city", "Melbourne")
        country = parameters.get("country", "Australia")
        
        print(f"   🌐 Fetching LIVE weather data for {city}, {country}...")
        
        try:
            # Import the MCP server tool function directly
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from mcp_servers.weather_server import get_weather
            
            # Call the MCP tool function directly to get real weather
            weather_text = await get_weather(city, country)
            
            # Return structured data with the live weather info
            result = {
                "city": city,
                "country": country,
                "weather_data": weather_text,
                "source": "Open-Meteo API (Live)",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            print(f"   ✅ Retrieved REAL weather data for {city}, {country}")
            return result
            
        except Exception as e:
            print(f"   ⚠️ Error calling MCP server: {e}")
            return {
                "city": city,
                "country": country,
                "error": str(e),
                "note": "Unable to fetch live weather data - check MCP server"
            }
    
    async def send_to_coordinator(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send results back to the Coordinator Agent via A2A.
        
        Args:
            message: Message to send to coordinator
        
        Returns:
            Acknowledgment from coordinator
        """
        print(f"\n📤 Sending results to Coordinator Agent...")
        print(f"   Data: {json.dumps(message, indent=2)}")
        
        # Simulate A2A message transmission
        # In production, this would use actual agent messaging protocol
        return {
            "status": "delivered",
            "recipient": "coordinator-agent",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    
    async def handle_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
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
        
        if message_type == "research_request":
            # Process research request with real MCP
            result = await self.process_research_request(message.get("data", {}))
            return result
        
        elif message_type == "ping":
            # Health check
            print(f"   ✅ {self.name}: active")
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
    """Main function to run the Research Agent."""
    print("\n" + "="*60)
    print("🤖 Research Agent (Agent 1) - Starting...")
    print("="*60)
    
    # Initialize agent
    agent = ResearchAgent()
    
    # Example: Simulate receiving a research request
    print("\n--- Example Research Request ---")
    sample_request = {
        "type": "research_request",
        "sender": "coordinator-agent",
        "data": {
            "task": "weather_lookup",
            "parameters": {
                "city": "San Francisco",
                "state": "CA"
            }
        }
    }
    
    # Process the request
    response = agent.handle_message(sample_request)
    
    print(f"\n✅ Research completed!")
    print(f"   Response: {json.dumps(response, indent=2)}")
    
    # Send to coordinator
    asyncio.run(agent.send_to_coordinator(response))
    
    print(f"\n✨ {agent.name} demo completed successfully!")


if __name__ == "__main__":
    main()
