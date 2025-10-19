import os
import asyncio
import json
from datetime import datetime
from dotenv import load_dotenv
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ContextProvider, Context, ChatMessage
from openai import AsyncAzureOpenAI

# Load environment
load_dotenv('.env03')

# File for persisting memory profile only
MEMORY_FILE = "ai_memory_profile.json"

class AIMemoryExtractor(ContextProvider):
    """
    AI-powered memory: Let the AI decide what's important to remember!
    No hardcoded patterns - the AI analyzes conversations intelligently.
    With persistent file storage!
    """
    
    def __init__(self, ai_client, memory_file=MEMORY_FILE):
        self.user_profile = {}  # Long-term memory storage
        self.ai_client = ai_client
        self.memory_file = memory_file
        
        # Load existing profile from file
        self._load_profile()
    
    def _load_profile(self):
        """Load user profile from JSON file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.user_profile = data.get('profile', {})
                print(f"\n📂 [LOADED MEMORY] from {self.memory_file}")
                if self.user_profile:
                    print(f"   🧠 Restored profile: {', '.join([f'{k}={v}' for k, v in self.user_profile.items()])}")
                else:
                    print(f"   📋 File exists but profile is empty")
            except Exception as e:
                print(f"\n⚠️  [LOAD ERROR] Could not load {self.memory_file}: {e}")
                self.user_profile = {}
        else:
            print(f"\n📋 [NEW MEMORY] No existing memory file found")
    
    def _save_profile(self):
        """Save user profile to JSON file."""
        try:
            data = {
                'timestamp': datetime.now().isoformat(),
                'profile': self.user_profile
            }
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"   💾 [SAVED TO FILE] {self.memory_file}")
        except Exception as e:
            print(f"   ⚠️  [SAVE ERROR] Could not save to {self.memory_file}: {e}")
    
    async def invoking(self, messages, **kwargs) -> Context:
        """Inject profile BEFORE agent processes request."""
        
        # If we have profile data, inject it as context
        if self.user_profile:
            profile_text = "\n".join([f"- {k}: {v}" for k, v in self.user_profile.items()])
            
            print(f"\n   💭 [INJECTING LONG-TERM MEMORY]")
            print(f"   📋 Profile: {', '.join([f'{k}={v}' for k, v in self.user_profile.items()])}\n")
            
            instructions = f"""[USER PROFILE - LONG-TERM MEMORY]:
{profile_text}

IMPORTANT: This is information about the user that persists across all conversations.
Reference this naturally when relevant, and be enthusiastic when recognizing the user!"""
            
            return Context(instructions=instructions)
        
        return Context()
    
    async def invoked(self, request_messages, response_messages, **kwargs) -> None:
        """Let AI extract important information AFTER conversation."""
        
        # Get the last user message
        user_message = ""
        if isinstance(request_messages, (list, tuple)):
            for msg in reversed(list(request_messages)):
                if hasattr(msg, 'contents') and isinstance(msg.contents, list):
                    if len(msg.contents) > 0 and hasattr(msg.contents[0], 'text'):
                        user_message = str(msg.contents[0].text)
                        break
        
        if not user_message or len(user_message) < 3:
            return
        
        print(f"   🤖 [AI ANALYZING]: '{user_message}'")
        
        # Ask AI to extract important information
        analysis_prompt = f"""Analyze this user message and extract any personal information worth remembering for future conversations.

User message: "{user_message}"

Current profile: {self.user_profile if self.user_profile else "Empty"}

Extract ONLY factual information about the user (name, age, profession, preferences, hobbies, etc.).
Return as JSON format: {{"key": "value", "key2": "value2"}}
If nothing important, return empty: {{}}

Examples:
- "My name is Alice" → {{"name": "Alice"}}
- "I'm a teacher" → {{"profession": "teacher"}}
- "I love pizza and my favorite color is blue" → {{"favorite_food": "pizza", "favorite_color": "blue"}}
- "How are you?" → {{}}

Extract only NEW or UPDATED information. Be concise with values.
JSON only, no explanation:"""

        try:
            # Use AI to analyze the message
            response = await self.ai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": analysis_prompt}],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=200
            )
            
            # Parse AI response
            ai_response = response.choices[0].message.content.strip()
            
            # Try to extract JSON
            if "{" in ai_response and "}" in ai_response:
                start = ai_response.index("{")
                end = ai_response.rindex("}") + 1
                json_str = ai_response[start:end]
                
                import json
                extracted = json.loads(json_str)
                
                # Update profile with extracted information
                if extracted:
                    for key, value in extracted.items():
                        self.user_profile[key] = value
                        print(f"   💾 [AI LEARNED] {key} = {value}")
                    
                    # Save to file immediately after learning
                    self._save_profile()
        
        except Exception as e:
            print(f"   ⚠️  [AI EXTRACTION ERROR]: {e}")


async def main():
    print("\n" + "="*70)
    print("🤖 AI-POWERED LONG-TERM MEMORY with FILE PERSISTENCE")
    print("="*70)
    print("\nConcept: AI intelligently extracts & saves important information!")
    print(f"Memory File: {MEMORY_FILE}")
    print("="*70)
    
    # Create OpenAI client for AI analysis
    chat_client = AsyncAzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-10-21",
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
    )
    
    print("\n🔧 Creating agent with AI-powered memory...")
    
    # Create AI-powered memory provider
    ai_memory = AIMemoryExtractor(chat_client)
    print("   ✅ AI memory analyzer initialized")
    
    # Create Azure OpenAI agent
    agent_client = AzureOpenAIChatClient(
        endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-10-21",
        deployment_name="gpt-4o"
    )
    
    agent = agent_client.create_agent(
        model="gpt-4o",
        instructions="""You are a helpful, friendly assistant with long-term memory.
        
When you recognize information about the user from their profile:
- Reference it naturally in conversation
- Be enthusiastic when you recognize them
- Provide personalized responses based on what you know

Be conversational and warm!""",
        context_providers=[ai_memory]  # Add AI memory provider to agent
    )
    print("✅ Agent created with AI-powered memory\n")
    
    print("="*70)
    print("💡 COMMANDS:")
    print("="*70)
    print("  • Chat naturally - AI extracts & saves info to file")
    print("  • 'new' - Create new thread (test cross-thread memory)")
    print("  • 'profile' - Show what AI learned about you")
    print("  • 'quit' - Exit")
    print("="*70)
    
    # Start conversation loop
    thread_num = 0
    thread = None
    
    try:
        while True:
            # Create new thread if needed
            if thread is None:
                thread_num += 1
                thread = agent.get_new_thread()
                print(f"\n🆕 THREAD #{thread_num} created\n")
            
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.lower() == 'quit':
                print("\n👋 Demo ended!")
                if ai_memory.user_profile:
                    print("\n📊 Final AI-Learned Profile:")
                    for key, value in ai_memory.user_profile.items():
                        print(f"   • {key}: {value}")
                else:
                    print("   (No profile data learned)")
                break
            
            if user_input.lower() == 'new':
                thread = None  # Will create new thread on next iteration
                continue
            
            if user_input.lower() == 'profile':
                print("\n📋 AI-LEARNED PROFILE:")
                if ai_memory.user_profile:
                    for key, value in ai_memory.user_profile.items():
                        print(f"   • {key}: {value}")
                else:
                    print("   (AI hasn't learned anything about you yet)")
                print()
                continue
            
            # Send message (AI memory automatically injected by agent)
            print(f"Agent (Thread #{thread_num}): ", end="", flush=True)
            async for chunk in agent.run_stream(user_input, thread=thread):
                print(chunk, end="", flush=True)
            print("\n")
    
    finally:
        # Cleanup
        print("\nCleaning up...")


if __name__ == "__main__":
    asyncio.run(main())
