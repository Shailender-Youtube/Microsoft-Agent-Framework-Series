
import asyncio
import os
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import MCPStdioTool

load_dotenv('.env03')

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT = "gpt-4o"
API_VERSION = "2024-10-21"


async def main():
    print("\n" + "="*75)
    print("MCP INTERACTIVE DEMO - Calculator Server")
    print("="*75)
    print("""
This demo connects to a LOCAL MCP calculator server!

HOW IT WORKS:
1. Starts MCP calculator server (uvx mcp-server-calculator)
2. Agent gets access to calculator tools
3. You ask math questions
4. Agent uses MCP tools to calculate answers

REQUIREMENTS:
- Install 'uv': pip install uv
- MCP server will be installed automatically via 'uvx'

Let's start!
    """)
    
    input("Press Enter to start MCP server...")
    
    try:
        print("\nStarting MCP calculator server...")
        print("Command: uvx mcp-server-calculator")
        
        async with MCPStdioTool(
            name="calculator",
            command="venv\\Scripts\\uvx.exe",
            args=["mcp-server-calculator"]
        ) as mcp_server:
            
            print("✅ MCP server started successfully!\n")
            
            # Create agent
            print("Creating agent with MCP calculator tools...")
            chat_client = AzureOpenAIChatClient(
                endpoint=ENDPOINT,
                deployment_name=DEPLOYMENT,
                api_key=API_KEY,
                api_version=API_VERSION
            )
            
            agent = chat_client.create_agent(
                model="gpt-4o",
                instructions=(
                    "You are a helpful math assistant. "
                    "Use the calculator tools for all mathematical calculations. "
                    "Show your work and explain the steps."
                ),
                tools=mcp_server
            )
            
            print("✅ Agent ready with MCP calculator!\n")
            
            print("="*75)
            print("INTERACTIVE MODE")
            print("="*75)
            print("""
Try these examples:
1. "What is 15 * 23 + 45?"
2. "Calculate the square root of 256"
3. "What is 2 to the power of 16?"
4. "Calculate (100 + 50) * 3 / 2"
5. "Find the sine of 45 degrees"

Type 'quit' to exit
            """)
            
            while True:
                try:
                    user_input = input("\n💭 You: ").strip()
                    
                    if not user_input:
                        continue
                    
                    if user_input.lower() in ['quit', 'exit']:
                        print("\n✅ Thanks for trying MCP! Goodbye!")
                        break
                    
                    print("\n🤖 Agent: ", end="", flush=True)
                    result = await agent.run(user_input)
                    print(result)
                    
                except KeyboardInterrupt:
                    print("\n\n✅ Exiting...")
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
    
    except FileNotFoundError:
        print("\n❌ ERROR: 'uvx' command not found!")
        print("\nSOLUTION:")
        print("1. Install 'uv': pip install uv")
        print("2. Or install with pipx: pipx install uv")
        print("3. Documentation: https://docs.astral.sh/uv/")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTROUBLESHOOTING:")
        print("1. Check 'uv' is installed: uv --version")
        print("2. Try manually: uvx mcp-server-calculator")
        print("3. Check Python version (3.10+ required)")


if __name__ == "__main__":
    asyncio.run(main())
