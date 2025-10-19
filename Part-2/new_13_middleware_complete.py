import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import Callable, Awaitable

from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import (
    AgentRunContext,
    FunctionInvocationContext,
    ChatContext,
    agent_middleware,
    function_middleware,
    chat_middleware
)

load_dotenv('.env03')

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT = "gpt-4o"
API_VERSION = "2024-10-21"


# ============================================================================
# MIDDLEWARE 1: TIMING (Agent Middleware)
# ============================================================================

@agent_middleware
async def timing_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Tracks execution time for entire agent run."""
    start_time = datetime.now()
    
    print(f"\n⏱️  [TIMING] Started at {start_time.strftime('%H:%M:%S')}")
    
    # Execute agent
    await next(context)
    
    # Calculate duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    print(f"⏱️  [TIMING] Completed in {duration:.2f} seconds")


# ============================================================================
# MIDDLEWARE 2: SECURITY (Agent Middleware)
# ============================================================================

@agent_middleware
async def security_middleware(
    context: AgentRunContext,
    next: Callable[[AgentRunContext], Awaitable[None]],
) -> None:
    """Blocks requests containing sensitive keywords."""
    
    # Check the last message for blocked content
    if context.messages:
        last_message = context.messages[-1]
        if hasattr(last_message, 'contents'):
            for content in last_message.contents:
                if hasattr(content, 'text'):
                    text = str(content.text).lower()
                    
                    # List of blocked keywords
                    blocked_keywords = ["password", "secret", "hack", "exploit", "bypass"]
                    
                    for keyword in blocked_keywords:
                        if keyword in text:
                            print(f"\n🚫 [SECURITY] Request BLOCKED! Detected: '{keyword}'")
                            print(f"🚫 [SECURITY] This request contains sensitive content and cannot be processed.")
                            context.terminate = True
                            return
    
    # If safe, continue
    await next(context)


# ============================================================================
# MIDDLEWARE 3: FUNCTION LOGGER (Function Middleware)
# ============================================================================

@function_middleware
async def function_logger_middleware(
    context: FunctionInvocationContext,
    next: Callable[[FunctionInvocationContext], Awaitable[None]],
) -> None:
    """Logs every function/tool call with arguments and results."""
    
    print(f"\n🔧 [FUNCTION] Calling tool: {context.function.name}")
    print(f"🔧 [FUNCTION] Arguments: {context.arguments}")
    
    # Execute the function
    await next(context)
    
    # Log the result
    print(f"🔧 [FUNCTION] Result: {context.result}")


# ============================================================================
# MIDDLEWARE 4: TOKEN COUNTER (Chat Middleware)
# ============================================================================

@chat_middleware
async def token_counter_middleware(
    context: ChatContext,
    next: Callable[[ChatContext], Awaitable[None]],
) -> None:
    """Estimates and logs token usage for AI calls."""
    
    # Estimate input tokens (rough: 1 token ≈ 4 characters)
    total_chars = sum(len(str(msg)) for msg in context.messages)
    estimated_input_tokens = total_chars // 4
    
    print(f"\n🤖 [AI CALL] Sending request to GPT-4o")
    print(f"🤖 [AI CALL] Messages: {len(context.messages)}")
    print(f"🤖 [AI CALL] Estimated input tokens: ~{estimated_input_tokens}")
    
    # Call the AI
    await next(context)
    
    # Estimate output tokens
    if context.result and hasattr(context.result, 'choices'):
        if hasattr(context.result.choices[0].message, 'content'):
            response_text = str(context.result.choices[0].message.content)
            estimated_output_tokens = len(response_text) // 4
            total_tokens = estimated_input_tokens + estimated_output_tokens
            
            print(f"🤖 [AI CALL] Estimated output tokens: ~{estimated_output_tokens}")
            print(f"🤖 [AI CALL] Total estimated tokens: ~{total_tokens}")


# ============================================================================
# DEMO TOOLS/FUNCTIONS
# ============================================================================

def get_weather(city: str) -> str:
    """Get current weather for a city."""
    weather_data = {
        "seattle": "☁️ Cloudy, 15°C, Light drizzle",
        "london": "🌧️ Rainy, 12°C, Heavy rain",
        "tokyo": "☀️ Sunny, 22°C, Clear skies",
        "mumbai": "🌤️ Partly cloudy, 28°C, Humid",
        "paris": "⛅ Partly cloudy, 18°C, Mild",
        "new york": "🌨️ Snowy, -2°C, Light snow",
    }
    return weather_data.get(city.lower(), f"Weather data not available for {city}")


def calculate(expression: str) -> str:
    """Calculate a mathematical expression safely."""
    try:
        # Safe evaluation for basic math
        allowed_names = {}
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


def get_time() -> str:
    """Get the current time."""
    return f"Current time: {datetime.now().strftime('%I:%M:%S %p')}"


def search_database(query: str) -> str:
    """Simulate searching a database."""
    # Simulate some processing time
    results = {
        "users": "Found 150 users matching criteria",
        "products": "Found 45 products in inventory",
        "orders": "Found 230 orders in last 30 days",
    }
    return results.get(query.lower(), f"No results found for: {query}")


# ============================================================================
# MAIN INTERACTIVE DEMO
# ============================================================================

async def main():
    print("\n" + "="*75)
    print("🎯 COMPLETE MIDDLEWARE DEMO - All 4 Types Working Together")
    print("="*75)
    
    print("""
This demo shows 4 middleware working simultaneously:

1️⃣  TIMING MIDDLEWARE (Agent)      → Tracks how long each request takes
2️⃣  SECURITY MIDDLEWARE (Agent)    → Blocks sensitive content
3️⃣  FUNCTION LOGGER (Function)     → Logs all tool calls
4️⃣  TOKEN COUNTER (Chat)           → Counts tokens sent to AI

Watch how they all work together in a real conversation!
""")
    
    print("="*75)
    print("\n🔧 Creating agent with all 4 middleware...\n")
    
    # Create agent with all middleware
    agent = AzureOpenAIChatClient(
        endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT,
        api_key=API_KEY,
        api_version=API_VERSION
    ).create_agent(
        model="gpt-4o",
        instructions="""You are a helpful assistant with access to various tools.
        Be friendly, concise, and helpful in your responses.""",
        tools=[get_weather, calculate, get_time, search_database],
        middleware=[
            timing_middleware,          # Agent middleware #1
            security_middleware,        # Agent middleware #2
            function_logger_middleware, # Function middleware
            token_counter_middleware,   # Chat middleware
        ]
    )
    
    print("✅ Agent created with 4 middleware layers!")
    
    print("\n" + "="*75)
    print("📝 SUGGESTED TEST PROMPTS:")
    print("="*75)
    print("""
To see all middleware in action, try these prompts:

✅ PROMPT 1: "tell me a joke"
   → Triggers: Timing + Token Counter
   → Simple request, no functions

✅ PROMPT 2: "what's the weather in Tokyo?"
   → Triggers: Timing + Function Logger + Token Counter
   → Calls the get_weather function

✅ PROMPT 3: "what time is it and calculate 15 * 8"
   → Triggers: Timing + Function Logger (2 calls) + Token Counter
   → Multiple function calls

✅ PROMPT 4: "what is my password?"
   → Triggers: Security (BLOCKS) + Timing
   → Security middleware blocks this request!

✅ PROMPT 5: "search for users and get weather in Paris"
   → Triggers: ALL 4 middleware
   → Multiple functions, shows complete flow

Type 'quit' to exit
""")
    print("="*75 + "\n")
    
    # Get new thread for conversation
    thread = agent.get_new_thread()
    
    # Interactive loop
    while True:
        try:
            user_input = input("💬 You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Demo ended! Thanks for testing all the middleware!")
                break
            
            print("\n" + "-"*75)
            print("🔄 PROCESSING YOUR REQUEST...")
            print("-"*75)
            
            # Stream the response
            print("\n🤖 Agent: ", end="", flush=True)
            async for chunk in agent.run_stream(user_input, thread=thread):
                print(chunk, end="", flush=True)
            print("\n")
            
            print("-"*75)
            print("✅ Request completed!\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Demo ended!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    asyncio.run(main())
