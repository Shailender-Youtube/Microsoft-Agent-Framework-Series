"""
NEW 06: Multiple Function Tools (Interactive Demo)

This demo shows an agent with MULTIPLE tools:
- Weather tool
- Calculator tool
- Time zone tool

The agent automatically chooses the right tool based on your question.
"""

import asyncio
import os
from typing import Annotated
from pydantic import Field
from dotenv import load_dotenv
from datetime import datetime
import requests

from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables
load_dotenv('.env03')

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")


# Tool 1: Weather
def get_weather(
    location: Annotated[str, Field(description="City name")]
) -> str:
    """Get current weather for a location."""
    weather_data = {
        "london": "🌧️ 15°C, Rainy",
        "paris": "☀️ 22°C, Sunny",
        "tokyo": "⛅ 18°C, Partly Cloudy",
        "new york": "🌤️ 20°C, Clear"
    }
    return weather_data.get(location.lower(), f"Weather data not available for {location}")


# Tool 2: Calculator
def calculate(
    expression: Annotated[str, Field(description="Math expression")]
) -> str:
    """Calculate a mathematical expression."""
    try:
        result = eval(expression, {"__builtins__": {}}, {
            "abs": abs, "round": round, "min": min, "max": max, "pow": pow
        })
        return f"Result: {result}"
    except:
        return f"Cannot calculate '{expression}'"


# Tool 3: Time Zone
def get_time(
    timezone: Annotated[str, Field(description="Timezone like 'America/New_York' or 'Europe/London'")]
) -> str:
    """Get current time in a timezone."""
    try:
        response = requests.get(f"http://worldtimeapi.org/api/timezone/{timezone}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            time = data.get('datetime', '').split('T')[1].split('.')[0]
            return f"⏰ Current time in {timezone}: {time}"
        else:
            return f"Could not get time for {timezone}"
    except:
        return f"Error getting time for {timezone}"


async def main():
    """Interactive demo: Agent with multiple tools."""
    
    print("\n" + "="*70)
    print("🛠️ DEMO: Multiple Function Tools")
    print("="*70)
    
    # Create agent with multiple tools
    agent = AzureOpenAIChatClient(
        endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT,
        api_key=API_KEY,
        api_version=API_VERSION
    ).create_agent(
        instructions="You are a helpful assistant with weather, calculator, and time tools. Choose the right tool automatically.",
        name="MultiToolBot",
        tools=[get_weather, calculate, get_time]
    )
    
    print("\n✅ Agent created with 3 tools:")
    print("   🌤️  Weather tool")
    print("   🧮 Calculator tool")
    print("   ⏰ Time zone tool")
    
    print("\n" + "="*70)
    print("💬 Interactive Chat (Type 'quit' to exit)")
    print("="*70 + "\n")
    
    while True:
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not user_input.strip():
            continue
        
        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream(user_input):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
