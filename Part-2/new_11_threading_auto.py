import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

from agent_framework.azure import AzureOpenAIChatClient

# Load environment variables
load_dotenv('.env03')

# File to save thread history
THREAD_FILE = "thread_history.json"

# Custom JSON encoder for Pydantic models
class PydanticEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'model_dump'):
            return obj.model_dump(mode='json')
        return super().default(obj)

ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")


async def main():
    """Interactive demo with automatic serialization after every message."""
    
    print("\n" + "="*70)
    print("🧵 AUTO-SERIALIZATION DEMO: Thread Save/Restore After Every Message")
    print("="*70)
    
    # Create agent
    agent = AzureOpenAIChatClient(
        endpoint=ENDPOINT,
        deployment_name=DEPLOYMENT,
        api_key=API_KEY,
        api_version=API_VERSION
    ).create_agent(
        instructions="You are a helpful assistant. Remember everything the user tells you and refer back to it.",
        name="MemoryBot"
    )
    
    print("\n✅ Agent created")
    
    # Try to load existing thread from file, or create new one
    print("📋 Checking for existing thread...")
    thread = None
    message_count = 0
    
    if os.path.exists(THREAD_FILE):
        try:
            print(f"   📂 Found {THREAD_FILE}! Loading previous conversation...")
            with open(THREAD_FILE, 'r', encoding='utf-8') as f:
                loaded_data = json.load(f)
            
            # Convert dicts back to ChatMessage objects
            from agent_framework._types import ChatMessage
            thread_data = loaded_data['thread_data']
            if 'chat_message_store_state' in thread_data and thread_data['chat_message_store_state']:
                store_state = thread_data['chat_message_store_state']
                if 'messages' in store_state:
                    store_state['messages'] = [
                        ChatMessage.from_dict(msg) if isinstance(msg, dict) else msg
                        for msg in store_state['messages']
                    ]
            
            # Restore thread
            thread = await agent.deserialize_thread(thread_data)
            message_count = loaded_data.get('message_number', 0)
            
            print(f"   ✅ Restored previous session with {message_count} messages!")
            print(f"   💡 Continuing from where you left off...\n")
        except Exception as e:
            print(f"   ⚠️  Could not load previous thread: {e}")
            print(f"   📋 Creating new thread instead...\n")
            thread = None
    
    if thread is None:
        print("   📋 Creating new thread...")
        thread = agent.get_new_thread()
        print("   ✅ New thread created\n")
    
    print("="*70)
    print("💬 Interactive Chat with Auto-Serialization")
    print("="*70)
    print("💡 After each message:")
    print("   1. Agent responds")
    print("   2. Thread automatically serializes (saves)")
    print("   3. Thread automatically deserializes (restores)")
    print("   4. Next message uses restored thread")
    print("\n💡 Type 'quit' to exit")
    print("="*70 + "\n")
    
    # message_count already set above when loading thread
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Demo completed!")
            print(f"\n📊 Total messages: {message_count}")
            print(f"📊 Total serialization cycles: {message_count}")
            break
        
        if not user_input:
            continue
        
        message_count += 1
        print(f"\n[Message #{message_count}]")
        
        # Step 1: Agent responds using current thread
        print("Agent: ", end="", flush=True)
        async for chunk in agent.run_stream(user_input, thread=thread):
            print(chunk, end="", flush=True)
        print()
        
        # Step 2: Serialize the thread (save state)
        print("\n💾 [Auto-Serializing thread state...]")
        serialized = await thread.serialize()
        print(f"   ✅ Serialized: {len(str(serialized))} bytes")
        print(f"   📊 Contains: {list(serialized.keys())}")
        
        # NEW: Save to JSON file (following Microsoft documentation)
        print(f"\n💾 [Saving to {THREAD_FILE}...]")
        
        # Manually convert the chat_message_store_state which contains ChatMessage objects
        json_serialized = dict(serialized)
        if 'chat_message_store_state' in json_serialized and json_serialized['chat_message_store_state']:
            store_state = json_serialized['chat_message_store_state']
            if 'messages' in store_state:
                # Convert ChatMessage objects to dicts using to_dict() method
                store_state['messages'] = [
                    msg.to_dict() if hasattr(msg, 'to_dict') else msg
                    for msg in store_state['messages']
                ]
        
        save_data = {
            'timestamp': datetime.now().isoformat(),
            'message_number': message_count,
            'thread_data': json_serialized
        }
        
        with open(THREAD_FILE, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)
        print(f"   ✅ Saved to disk: {THREAD_FILE}")
        
        # Step 3: Load from JSON file and deserialize (following Microsoft documentation)
        print(f"\n📥 [Loading from {THREAD_FILE}...]")
        with open(THREAD_FILE, 'r', encoding='utf-8') as f:
            loaded_data = json.load(f)
        print(f"   ✅ Loaded from disk (message #{loaded_data['message_number']})")
        
        print("\n📥 [Deserializing thread state...]")
        # Convert dicts back to ChatMessage objects
        from agent_framework._types import ChatMessage
        thread_data = loaded_data['thread_data']
        if 'chat_message_store_state' in thread_data and thread_data['chat_message_store_state']:
            store_state = thread_data['chat_message_store_state']
            if 'messages' in store_state:
                # Convert dicts back to ChatMessage objects using from_dict()
                store_state['messages'] = [
                    ChatMessage.from_dict(msg) if isinstance(msg, dict) else msg
                    for msg in store_state['messages']
                ]
        
        # Deserialize from the restored data
        thread = await agent.deserialize_thread(thread_data)
        print("   ✅ Thread restored from file")
        print("   💡 Next message will use this restored thread\n")
        
        print("-" * 70 + "\n")
    
    print("\n" + "="*70)
    print("✅ DEMO COMPLETE")
    print("="*70)
    print("💡 What you saw:")
    print("   • Thread automatically saved to JSON file after each message")
    print("   • Thread automatically restored from JSON file")
    print("   • Agent maintained full conversation history")
    print("   • Each cycle proved file persistence works!")
    print(f"\n📁 Check the file: {THREAD_FILE}")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
