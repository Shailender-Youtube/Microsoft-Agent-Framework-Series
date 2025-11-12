"""
Scenario 1 Main Orchestration Script
====================================
This script demonstrates the complete workflow of three local agents
communicating via A2A protocol and using local MCP servers.

Workflow:
1. User provides a request
2. Coordinator Agent analyzes and plans workflow
3. Coordinator delegates to Research Agent (Weather MCP)
4. Coordinator delegates to Executor Agent (File MCP)
5. Coordinator aggregates results and responds to user

Run:
    python run_scenario1.py
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv
import json

# Add agents directory to path
sys.path.append(str(Path(__file__).parent / "agents"))

# Import agents
from agent1_research import ResearchAgent
from agent2_coordinator import CoordinatorAgent
from agent3_executor import ExecutorAgent

# Load environment variables
load_dotenv()


class Scenario1Orchestrator:
    """Orchestrator for Scenario 1 - Local Agents with MCP."""
    
    def __init__(self):
        """Initialize the orchestrator and all agents."""
        print("\n" + "="*70)
        print("🚀 SCENARIO 1: Local Agents with Azure OpenAI and Local MCP Servers")
        print("="*70)
        
        print("\n📋 Initializing agents...")
        
        # Initialize agents in the right order
        self.research_agent = ResearchAgent()
        self.executor_agent = ExecutorAgent()
        
        # Initialize coordinator with references to other agents for real A2A
        self.coordinator_agent = CoordinatorAgent(
            research_agent=self.research_agent,
            executor_agent=self.executor_agent
        )
        
        print("\n✅ All agents initialized successfully!")
        
        # Verify Azure OpenAI configuration
        self._verify_configuration()
    
    def _verify_configuration(self):
        """Verify that necessary environment variables are set."""
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_API_KEY",
            "AZURE_OPENAI_DEPLOYMENT_NAME"
        ]
        
        missing = [var for var in required_vars if not os.getenv(var)]
        
        if missing:
            print(f"\n⚠️  Warning: Missing environment variables: {', '.join(missing)}")
            print("   Please configure your .env file")
        else:
            print(f"\n✅ Azure OpenAI configuration verified")
            print(f"   Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
            print(f"   Model: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
    
    async def run_complete_workflow(self, user_request: str):
        """
        Run the complete multi-agent workflow.
        
        Args:
            user_request: Natural language request from user
        """
        print("\n" + "="*70)
        print("🎯 Starting Complete Workflow")
        print("="*70)
        
        print(f"\n👤 User Request:")
        print(f"   \"{user_request}\"")
        
        # Step 1: Coordinator receives and plans
        print(f"\n{'='*70}")
        print(f"📍 STEP 1: Coordinator Agent - Planning Workflow")
        print(f"{'='*70}")
        
        response = await self.coordinator_agent.process_user_request(user_request)
        
        print(f"\n{'='*70}")
        print(f"✅ WORKFLOW COMPLETED")
        print(f"{'='*70}")
        
        print(f"\n📊 Final Results:")
        print(f"   Status: {response['status']}")
        print(f"   Steps Completed: {response['successful_steps']}/{response['total_steps']}")
        
        # Display actual weather data if available
        if response.get('results'):
            for i, result in enumerate(response['results'], 1):
                if result.get('status') == 'success' and 'results' in result:
                    weather_info = result['results']
                    if 'weather_data' in weather_info:
                        print(f"\n🌤️  WEATHER DATA (Step {i}):")
                        print(weather_info['weather_data'])
                    elif 'raw_data' in weather_info:
                        print(f"\n🌤️  WEATHER DATA (Step {i}):")
                        print(weather_info['raw_data'])
        
        print(f"\n💬 Summary:")
        print(f"   {response['summary']}")
        
        return response
    
    async def demonstrate_agent_communication(self):
        """Demonstrate direct agent-to-agent communication."""
        print("\n" + "="*70)
        print("🔄 Demonstrating Agent-to-Agent (A2A) Communication")
        print("="*70)
        
        # Demo 1: Coordinator -> Research Agent
        print(f"\n{'='*70}")
        print("📡 Demo 1: Coordinator → Research Agent")
        print(f"{'='*70}")
        
        research_request = {
            "type": "research_request",
            "sender": "coordinator-agent",
            "data": {
                "task": "weather_lookup",
                "parameters": {
                    "city": "Melbourne",
                    "country": "Australia"
                }
            }
        }
        
        research_response = await self.research_agent.handle_message(research_request)
        print(f"\n✅ Research Agent Response:")
        
        # Display the actual weather data nicely
        if 'results' in research_response:
            results = research_response['results']
            if 'weather_data' in results:
                print(results['weather_data'])
            else:
                print(f"   {json.dumps(results, indent=2)}")
        
        # Demo 2: Coordinator -> Executor Agent
        print(f"\n{'='*70}")
        print("📡 Demo 2: Coordinator → Executor Agent")
        print(f"{'='*70}")
        
        execution_request = {
            "type": "execution_request",
            "sender": "coordinator-agent",
            "data": {
                "operation": "write_file",
                "parameters": {
                    "filename": "agent_demo.txt"
                },
                "content": json.dumps(research_response['results'], indent=2)
            }
        }
        
        execution_response = self.executor_agent.handle_message(execution_request)
        print(f"\n✅ Executor Agent Response:")
        print(f"   {execution_response['results']['message']}")
        
        # Demo 3: Ping all agents
        print(f"\n{'='*70}")
        print("📡 Demo 3: Health Check - Ping All Agents")
        print(f"{'='*70}")
        
        ping_message = {"type": "ping", "sender": "orchestrator"}
        
        agents = [
            ("Research Agent", self.research_agent),
            ("Coordinator Agent", self.coordinator_agent),
            ("Executor Agent", self.executor_agent)
        ]
        
        for name, agent in agents:
            response = agent.handle_message(ping_message)
            status = "✅" if response.get("status") == "active" else "❌"
            print(f"   {status} {name}: {response.get('status', 'unknown')}")
    
    def print_architecture_diagram(self):
        """Print the architecture diagram."""
        print("\n" + "="*70)
        print("🏗️  SCENARIO 1 ARCHITECTURE")
        print("="*70)
        print("""
    ┌─────────────────────────────────────────────────────┐
    │              Local Environment                       │
    │                                                      │
    │  ┌──────────────┐         ┌──────────────┐         │
    │  │ MCP Server 1 │         │ MCP Server 2 │         │
    │  │  (Weather)   │         │(File  Ops)   │         │
    │  │  Port: 8001  │         │  Port: 8002  │         │
    │  └──────┬───────┘         └──────┬───────┘         │
    │         │                        │                  │
    │         └──────────┬─────────────┘                  │
    │                    │ MCP Protocol                   │
    │         ┌──────────┴─────────────┐                  │
    │         │                        │                  │
    │  ┌──────▼──────┐      ┌─────────▼──────┐          │
    │  │   Agent 1   │      │    Agent 2     │          │
    │  │  Research   │◄────►│  Coordinator   │          │
    │  └─────────────┘      └────────┬───────┘          │
    │                                 │                   │
    │                        ┌────────▼────────┐         │
    │                        │    Agent 3      │         │
    │                        │    Executor     │         │
    │                        └─────────────────┘         │
    │                              │                      │
    │                              │ A2A Communication    │
    └──────────────────────────────┼──────────────────────┘
                                  │
                                  ▼
                         ┌────────────────┐
                         │  Azure OpenAI  │
                         └────────────────┘
        """)


def show_popular_cities():
    """Display list of popular cities for quick reference."""
    print("\n" + "="*70)
    print("🌆 POPULAR CITIES BY REGION")
    print("="*70)
    
    cities = {
        "Australia": ["Melbourne", "Sydney", "Brisbane", "Perth", "Adelaide"],
        "Asia": ["Tokyo", "Singapore", "Bangkok", "Seoul", "Mumbai"],
        "Europe": ["London", "Paris", "Berlin", "Rome", "Madrid"],
        "North America": ["New York", "Los Angeles", "Toronto", "Chicago", "Miami"],
        "South America": ["São Paulo", "Buenos Aires", "Rio de Janeiro", "Lima"],
        "Africa": ["Cairo", "Lagos", "Cape Town", "Nairobi"]
    }
    
    for region, city_list in cities.items():
        print(f"\n🌍 {region}:")
        print(f"   {', '.join(city_list)}")
    
    print("\n💡 Example: 'What's the weather in Tokyo, Japan?'")


def show_a2a_protocol():
    """Display detailed A2A protocol information."""
    print("\n" + "="*70)
    print("📡 AGENT-TO-AGENT (A2A) PROTOCOL EXPLAINED")
    print("="*70)
    
    print("\n🔄 What is A2A Communication?")
    print("   Agent-to-Agent messaging allows agents to delegate tasks,")
    print("   share information, and collaborate on complex workflows.")
    
    print("\n📨 A2A Message Structure:")
    print("""
   {
     "sender": "coordinator-agent",      // Who is sending the message
     "recipient": "research-agent",      // Who receives the message
     "type": "research_request",         // Type of request
     "data": {                           // Payload/parameters
       "task": "weather_lookup",
       "parameters": {
         "city": "Melbourne",
         "country": "Australia"
       }
     },
     "timestamp": 1234567890.123        // When message was sent
   }
    """)
    
    print("\n📬 A2A Response Structure:")
    print("""
   {
     "agent_id": "research-agent",       // Who is responding
     "status": "success",                // Success or error
     "task": "weather_lookup",           // Which task was performed
     "results": {                        // The actual results
       "city": "Melbourne",
       "weather_data": "..."
     },
     "metadata": {                       // Additional info
       "source": "Weather MCP Server",
       "confidence": "high"
     }
   }
    """)
    
    print("\n🎯 Message Types:")
    print("   • research_request  - Ask for information gathering")
    print("   • execution_request - Ask to perform an action")
    print("   • ping              - Health check")
    print("   • workflow_request  - Delegate a complex workflow")
    
    print("\n💡 Try asking a weather question to see A2A in action!")


def show_help():
    """Display help information."""
    print("\n" + "="*70)
    print("❓ HELP - HOW TO USE THE WEATHER ASSISTANT")
    print("="*70)
    
    print("\n📖 What you can ask:")
    print("   • Current weather: 'What's the weather in [city]?'")
    print("   • Forecasts: 'Get forecast for [city]'")
    print("   • Save data: '...and save it to a file'")
    print("   • Alerts: 'Check weather alerts for [city]'")
    
    print("\n🎯 Query format:")
    print("   • Include city name (required)")
    print("   • Add country for better accuracy (recommended)")
    print("   • Mention 'save' or 'file' to save results")
    
    print("\n✅ Good examples:")
    print("   ✓ 'Weather in Melbourne, Australia'")
    print("   ✓ 'Tokyo forecast and save to file'")
    print("   ✓ 'What's the temperature in London?'")
    
    print("\n❌ What won't work:")
    print("   ✗ 'Weather' (no city specified)")
    print("   ✗ 'Tell me a joke' (not weather-related)")
    
    print("\n🔧 Special commands:")
    print("   • 'cities' - View popular cities list")
    print("   • 'demo' - Run automated examples")
    print("   • 'quit' or 'exit' - End session")


async def interactive_mode():
    """Interactive mode - ask user for custom weather requests."""
    
    print("\n" + "="*70)
    print("🎮 INTERACTIVE MODE - Custom Weather Queries")
    print("="*70)
    
    # Initialize orchestrator
    orchestrator = Scenario1Orchestrator()
    
    # Show architecture
    orchestrator.print_architecture_diagram()
    
    print("\n\n" + "="*70)
    print("💡 INTERACTIVE WEATHER ASSISTANT")
    print("="*70)
    print("\n🌍 Ask me about weather in any city worldwide!")
    print("\n📝 Example questions:")
    print("   • What's the weather in Melbourne, Australia?")
    print("   • Get weather forecast for Tokyo, Japan")
    print("   • Check weather conditions in London, UK and save to file")
    print("   • Compare weather in Sydney and Brisbane")
    print("\n🎯 Quick commands:")
    print("   • Type 'cities' to see popular cities list")
    print("   • Type 'demo' to see automated examples")
    print("   • Type 'a2a' to see detailed A2A communication example")
    print("   • Type 'help' for more information")
    print("   • Type 'quit' or 'exit' to end the session\n")
    
    while True:
        print("\n" + "-"*70)
        user_input = input("🤔 Your weather question: ").strip()
        
        if not user_input:
            print("⚠️  Please enter a question!")
            continue
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Thank you for using the Interactive Weather Assistant!")
            print("🎉 Session ended.\n")
            break
        
        if user_input.lower() == 'demo':
            await run_demo_examples(orchestrator)
            continue
        
        if user_input.lower() == 'cities':
            show_popular_cities()
            continue
        
        if user_input.lower() == 'help':
            show_help()
            continue
        
        if user_input.lower() == 'a2a':
            show_a2a_protocol()
            continue
        
        # Process the user's weather request
        print(f"\n{'='*70}")
        print(f"🔄 Processing your request...")
        print(f"{'='*70}")
        
        try:
            await orchestrator.run_complete_workflow(user_input)
            print(f"\n✨ Request completed! Ask another question or type 'quit' to exit.")
        except Exception as e:
            print(f"\n❌ Error processing request: {e}")
            print("💡 Tip: Make sure to mention a city name in your question!")
            import traceback
            traceback.print_exc()


async def run_demo_examples(orchestrator):
    """Run pre-defined demo examples."""
    print("\n\n" + "="*70)
    print("🎬 RUNNING DEMO EXAMPLES")
    print("="*70)
    
    user_requests = [
        "What's the weather in Melbourne, Australia and save it to a file?",
        "Get weather forecast for Sydney, Australia and create a report",
        "Check weather conditions for Brisbane, Australia and save them"
    ]
    
    for i, request in enumerate(user_requests, 1):
        print(f"\n{'#'*70}")
        print(f"# DEMO EXAMPLE {i}/{len(user_requests)}")
        print(f"{'#'*70}")
        
        await orchestrator.run_complete_workflow(request)
        
        if i < len(user_requests):
            print("\n⏸️  Press Enter to continue to next demo...")
            input()
    
    print("\n✅ Demo examples completed!")


async def main():
    """Main entry point for Scenario 1."""
    
    print("\n" + "="*70)
    print("🚀 WELCOME TO SCENARIO 1")
    print("Multi-Agent Weather Assistant with A2A Communication")
    print("="*70)
    print("\n🎮 Starting Interactive Mode...")
    print("💡 You can see A2A message structures in real-time!\n")
    
    # Directly start interactive mode
    await interactive_mode()
    
    print("""
    ✅ Successfully Demonstrated:
       • Three local agents (Research, Coordinator, Executor)
       • Agent-to-Agent (A2A) communication
       • Integration with MCP servers (Weather & File Operations)
       • Multi-agent workflow orchestration
       • Azure OpenAI model usage
    
    📚 Next Steps:
       • Explore Scenario 2 for Azure AI Foundry hosted agents
       • Modify agent instructions for custom behaviors
       • Add more MCP servers with different capabilities
       • Experiment with complex multi-step workflows
    
    💡 Tips:
       • Check agent logs for detailed execution flow
       • Modify .env for different Azure OpenAI models
       • Extend agents with additional capabilities
    """)


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   Microsoft Agent Framework - Scenario 1                  ║
    ║   Local Agents with A2A Communication and MCP Servers     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
