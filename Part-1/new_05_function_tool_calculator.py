"""
NEW 05: Function Tools - Calculator (Interactive Demo)

This demo shows a calculator function tool.
The agent can perform mathematical calculations.
"""

import asyncio
import os
from typing import Annotated
from pydantic import Field
from dotenv import load_dotenv

from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables
load_dotenv('.env03')

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")


# Define calculator function
def calculate(
    expression: Annotated[str, Field(description="Mathematical expression to evaluate, e.g. '2 + 2' or '10 * 5'")]
) -> str:
    """Evaluate a mathematical expression."""
    try:
        # Safe evaluation with limited namespace
        result = eval(
            expression,
            {"__builtins__": {}},
            {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
            }
        )
        return f"Result: {result}"
    except Exception as e:
        return f"Error: Could not calculate '{expression}'"


async def main():
    """Interactive demo: Agent with calculator tool."""
    
    print("\n" + "="*70)
    print("🧮 DEMO: Function Tools - Calculator")
    print("="*70)
    
    # Create agent with calculator tool
    agent = AzureOpenAIChatClient(
        endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT,
        api_key=API_KEY,
        api_version=API_VERSION
    ).create_agent(
        instructions="You are a math assistant. Use the calculate tool for math problems.",
        name="CalculatorBot",
        tools=[calculate]
    )
    
    print("\n✅ Agent created with calculator tool")
    print("💡 TIP: Ask math questions or calculations")
    
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
