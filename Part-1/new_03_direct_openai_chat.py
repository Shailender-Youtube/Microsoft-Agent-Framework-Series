"""
NEW 03: Direct Azure OpenAI Chat (Interactive Demo)

This demo uses Azure OpenAI DIRECTLY (not Azure AI Foundry Agent Service).
The agent is not persistent - it exists only for this session.
"""

import asyncio
import os
from dotenv import load_dotenv

from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables
load_dotenv('.env03')

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-07-01-preview")


async def main():
    """Interactive demo: Azure OpenAI direct chat."""
    
    print("\n" + "="*70)
    print("🤖 DEMO: Direct Azure OpenAI Chat (Not Agent Service)")
    print("="*70)
    
    # Create agent using direct Azure OpenAI
    agent = AzureOpenAIChatClient(
        endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT,
        api_key=API_KEY,
        api_version=API_VERSION
    ).create_agent(
        instructions="You are a helpful assistant. Be concise and clear.",
        name="DirectChatBot"
    )
    
    print("\n✅ Agent created (temporary, not saved to cloud)")
    
    print("\n" + "="*70)
    print("💬 Interactive Chat (Type 'quit' to exit)")
    print("="*70 + "\n")
    
    while True:
        # Get user input
        user_input = input("You: ")
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not user_input.strip():
            continue
        
        # Get streaming response
        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream(user_input):
            if chunk.text:
                print(chunk.text, end="", flush=True)
        print("\n")


if __name__ == "__main__":
    asyncio.run(main())
