"""
Interactive MAF Demo: Create Agents and Demonstrate A2A Communication
=====================================================================
This interactive script demonstrates Microsoft Agent Framework (MAF) by:
1. Creating agents step-by-step (Research, Executor, Coordinator)
2. Showing A2A message passing in real-time
3. Demonstrating complete multi-agent workflow

MAF Implementation via Azure AI Foundry SDK
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder

# MCP Tool creation - will be done inside functions to handle SDK version differences
# We'll create tool definitions as dictionaries which work across all SDK versions

# Handle different SDK versions for imports
# RequiredMcpToolCall - try multiple import paths
try:
    from azure.ai.agents.models._models import RequiredMcpToolCall
except ImportError:
    try:
        from azure.ai.agents.models import RequiredMcpToolCall
    except ImportError:
        try:
            from azure.ai.agents.models import RunStepMcpToolCall as RequiredMcpToolCall
        except ImportError:
            # If not available, we'll check by attributes
            RequiredMcpToolCall = None

# SubmitToolApprovalAction - check if available
try:
    from azure.ai.agents.models import SubmitToolApprovalAction
except ImportError:
    try:
        from azure.ai.agents.models._models import SubmitToolApprovalAction
    except ImportError:
        # Check RequiredAction which might be the base class
        try:
            from azure.ai.agents.models import RequiredAction
            SubmitToolApprovalAction = RequiredAction  # Use base class as fallback
        except ImportError:
            SubmitToolApprovalAction = None

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

load_dotenv()

# Configuration
PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
if not PROJECT_ENDPOINT:
    ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    PROJECT = os.getenv("AZURE_AI_FOUNDRY_PROJECT")
    if ENDPOINT and PROJECT:
        PROJECT_ENDPOINT = f"{ENDPOINT}/api/projects/{PROJECT}"

DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
MCP_LEARN_URL = "https://learn.microsoft.com/api/mcp"

agents_info = {}


def print_header(title):
    """Print a formatted header."""
    print("\n" + "="*70)
    print(title)
    print("="*70)


def print_step(step_num, total, description):
    """Print a step indicator."""
    print(f"\n[{step_num}/{total}] {description}")
    print("-" * 70)


def wait_for_input(prompt="Press Enter to continue...", auto_mode=False):
    """Wait for user input."""
    if auto_mode:
        print(f"\n{prompt}")
        time.sleep(2)  # Brief pause for readability
    else:
        try:
            input(f"\n{prompt}")
        except EOFError:
            # Non-interactive mode - auto proceed
            print(f"\n{prompt} [Auto-proceeding...]")
            time.sleep(2)


def submit_tool_approvals(credential, thread_id, run_id, tool_calls):
    """Submit tool approvals via REST API."""
    tool_approvals = []
    for tool_call in tool_calls:
        # Get tool ID - handle both dict and object formats
        tool_id = None
        if isinstance(tool_call, dict):
            tool_id = tool_call.get('id') or tool_call.get('tool_call_id')
        elif hasattr(tool_call, 'id'):
            tool_id = tool_call.id
        elif hasattr(tool_call, 'tool_call_id'):
            tool_id = tool_call.tool_call_id
        
        if tool_id:
            tool_approvals.append({
                "tool_call_id": tool_id,
                "approve": True,
                "headers": {}
            })
    
    if not tool_approvals:
        print(f"   ⚠️  No tool IDs found to approve")
        return False
    
    submit_url = f"{PROJECT_ENDPOINT}/threads/{thread_id}/runs/{run_id}/submit_tool_outputs?api-version=v1"
    try:
        token = credential.get_token("https://ai.azure.com/.default").token
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {"tool_approvals": tool_approvals}
        response = requests.post(
            submit_url,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"   ⚠️  API returned {response.status_code}: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"   ⚠️  Error submitting approvals: {e}")
        return False


def create_research_agent(agents_client):
    """Create Research Agent with MCP tools."""
    print_step(1, 3, "Creating Research Agent (with MCP tools)")
    
    print("\n📋 Research Agent Configuration:")
    print("   - Role: Information Researcher")
    print("   - Capability: Microsoft Learn Documentation Access")
    print("   - MCP Tools: microsoft_docs_search, microsoft_docs_fetch")
    
    # Auto mode check
    auto_mode = not sys.stdin.isatty()
    wait_for_input("Ready to create Research Agent?", auto_mode)
    
    # Create MCP tool definition as dictionary (works across all SDK versions)
    mcp_tool_def = [{
        "type": "mcp",
        "server_label": "microsoft_learn_server",
        "server_url": MCP_LEARN_URL
    }]
    
    research_agent = agents_client.create_agent(
        model=DEPLOYMENT,
        name="research-agent-interactive",
        instructions="""You are a Research Agent with access to Microsoft Learn documentation via MCP tools.

Your capabilities:
- Search Microsoft documentation using microsoft_docs_search
- Fetch detailed documentation using microsoft_docs_fetch
- Provide accurate, up-to-date information

When other agents ask you questions via A2A:
- Use MCP tools to search Microsoft Learn documentation
- Provide comprehensive, accurate answers
- Include documentation sources when possible""",
        tools=mcp_tool_def
    )
    
    agents_info["research_agent"] = {
        "agent_id": research_agent.id,
        "agent_name": research_agent.name,
        "has_mcp": True
    }
    
    print(f"\n✅ Research Agent Created Successfully!")
    print(f"   Agent ID: {research_agent.id}")
    print(f"   Agent Name: {research_agent.name}")
    print(f"   MCP Tools: ✓ Connected")
    
    return research_agent


def create_executor_agent(agents_client):
    """Create Executor Agent."""
    print_step(2, 3, "Creating Executor Agent")
    
    print("\n📋 Executor Agent Configuration:")
    print("   - Role: Task Executor")
    print("   - Capability: Process and format information")
    print("   - MCP Tools: None (uses A2A to communicate)")
    
    auto_mode = not sys.stdin.isatty()
    wait_for_input("Ready to create Executor Agent?", auto_mode)
    
    executor_agent = agents_client.create_agent(
        model=DEPLOYMENT,
        name="executor-agent-interactive",
        instructions="""You are an Executor Agent that processes and formats information.

Your responsibilities:
- Receive data from other agents via A2A
- Format and structure information
- Create summaries and reports
- Present information in a clear, organized manner

You communicate with:
- Research Agent: Receives research data
- Coordinator Agent: Receives instructions and sends results""",
        tools=None
    )
    
    agents_info["executor_agent"] = {
        "agent_id": executor_agent.id,
        "agent_name": executor_agent.name,
        "has_mcp": False
    }
    
    print(f"\n✅ Executor Agent Created Successfully!")
    print(f"   Agent ID: {executor_agent.id}")
    print(f"   Agent Name: {executor_agent.name}")
    
    return executor_agent


def create_coordinator_agent(agents_client):
    """Create Coordinator Agent."""
    print_step(3, 3, "Creating Coordinator Agent (orchestrates A2A communication)")
    
    research_id = agents_info["research_agent"]["agent_id"]
    executor_id = agents_info["executor_agent"]["agent_id"]
    
    print("\n📋 Coordinator Agent Configuration:")
    print("   - Role: Workflow Orchestrator")
    print("   - Capability: Coordinates other agents via A2A")
    print(f"   - Available Agents:")
    print(f"     • Research Agent: {research_id}")
    print(f"     • Executor Agent: {executor_id}")
    
    auto_mode = not sys.stdin.isatty()
    wait_for_input("Ready to create Coordinator Agent?", auto_mode)
    
    coordinator_agent = agents_client.create_agent(
        model=DEPLOYMENT,
        name="coordinator-agent-interactive",
        instructions=f"""You are a Coordinator Agent that orchestrates multi-agent workflows using A2A communication.

IMPORTANT: You do NOT have access to MCP tools or documentation directly.
You MUST delegate tasks to other agents via A2A.

Available Agents for A2A Communication:
- Research Agent (ID: {research_id}): Has Microsoft Learn MCP tools
- Executor Agent (ID: {executor_id}): Formats and processes information

Your workflow:
1. Receive user questions
2. Delegate research to Research Agent via A2A
3. Research Agent uses MCP to find information
4. Receive research results via A2A
5. Delegate formatting to Executor Agent via A2A
6. Receive formatted results via A2A
7. Present final answer to user

Always coordinate between agents using A2A protocol.""",
        tools=None
    )
    
    agents_info["coordinator_agent"] = {
        "agent_id": coordinator_agent.id,
        "agent_name": coordinator_agent.name,
        "has_mcp": False
    }
    
    print(f"\n✅ Coordinator Agent Created Successfully!")
    print(f"   Agent ID: {coordinator_agent.id}")
    print(f"   Agent Name: {coordinator_agent.name}")
    
    return coordinator_agent


def print_a2a_message(sender, recipient, message_type, content):
    """Print formatted A2A message."""
    print("\n" + "▔"*70)
    print("📨 A2A MESSAGE PASSING")
    print("▔"*70)
    print(f"From:      {sender}")
    print(f"To:        {recipient}")
    print(f"Type:      {message_type}")
    print(f"Content:   {content[:100]}{'...' if len(content) > 100 else ''}")
    print("▔"*70)


def demonstrate_a2a_workflow(credential):
    """Demonstrate A2A communication workflow."""
    auto_mode = not sys.stdin.isatty()
    
    print_header("A2A COMMUNICATION DEMONSTRATION")
    
    coordinator_id = agents_info["coordinator_agent"]["agent_id"]
    research_id = agents_info["research_agent"]["agent_id"]
    executor_id = agents_info["executor_agent"]["agent_id"]
    
    print("\n🌐 Agent Network:")
    print(f"   Coordinator: {coordinator_id}")
    print(f"   Research:    {research_id}")
    print(f"   Executor:    {executor_id}")
    
    # Get user question
    print("\n" + "="*70)
    print("ASK A QUESTION")
    print("="*70)
    
    if auto_mode:
        question = "What are the service tiers for MCP servers in API Management?"
        print(f"\n[Auto Mode] Using default question:")
        print(f"🤔 {question}")
    else:
        try:
            question = input("\n🤔 Enter your question about Microsoft/Azure services: ").strip()
            if not question:
                question = "What are the service tiers for MCP servers in API Management?"
                print(f"\n⚠️  Using default question: {question}")
            else:
                print(f"\n✅ Question received: {question}")
        except EOFError:
            question = "What are the service tiers for MCP servers in API Management?"
            print(f"\n[Auto Mode] Using default question: {question}")
    
    wait_for_input("Press Enter to start workflow...", auto_mode)
    
    # Step 1: User -> Coordinator
    print_header("STEP 1: User → Coordinator Agent")
    print_a2a_message("User", "Coordinator Agent", "user_request", question)
    
    with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
        agents_client = project_client.agents
        
        # Create thread for Coordinator
        thread_coord = agents_client.threads.create()
        msg_coord = agents_client.messages.create(
            thread_id=thread_coord.id,
            role="user",
            content=question
        )
        run_coord = agents_client.runs.create(
            thread_id=thread_coord.id,
            agent_id=coordinator_id
        )
        print(f"\n✅ Message delivered to Coordinator Agent")
        print(f"   Thread ID: {thread_coord.id}")
        print(f"   Run ID: {run_coord.id}")
        
        wait_for_input("Press Enter to continue to A2A delegation...", auto_mode)
        
        # Step 2: Coordinator -> Research Agent (A2A)
        print_header("STEP 2: Coordinator → Research Agent (A2A)")
        research_question = f"Please search Microsoft Learn documentation and answer: {question}"
        print_a2a_message("Coordinator Agent", "Research Agent", "research_request", research_question)
        
        thread_research = agents_client.threads.create()
        print(f"\n   🔗 Creating A2A connection (Thread: {thread_research.id})...")
        
        msg_research = agents_client.messages.create(
            thread_id=thread_research.id,
            role="user",
            content=research_question
        )
        print(f"   ✅ A2A message sent: {msg_research.id}")
        
        run_research = agents_client.runs.create(
            thread_id=thread_research.id,
            agent_id=research_id
        )
        print(f"   ✅ Research Agent processing: {run_research.id}")
        
        wait_for_input("Press Enter to see MCP tool usage...", auto_mode)
        
        # Step 3: Research Agent uses MCP tools
        print_header("STEP 3: Research Agent → MCP Tools")
        print("📡 Research Agent is calling MCP tools...")
        
        max_wait = 120
        waited = 0
        
        while run_research.status.value in ["queued", "in_progress", "requires_action"] and waited < max_wait:
            time.sleep(2)
            waited += 2
            run_research = agents_client.runs.get(thread_id=thread_research.id, run_id=run_research.id)
            
            if run_research.status.value == "requires_action":
                required_action = run_research.required_action
                tool_calls = []
                
                # Try to extract tool calls from required_action
                # Method 1: Access via _data attribute (seen in debug output)
                if hasattr(required_action, '_data'):
                    data = required_action._data
                    if isinstance(data, dict):
                        if 'submit_tool_approval' in data:
                            submit_data = data['submit_tool_approval']
                            if isinstance(submit_data, dict) and 'tool_calls' in submit_data:
                                tool_calls = submit_data['tool_calls']
                
                # Method 2: Direct attribute access
                if not tool_calls and hasattr(required_action, 'submit_tool_approval'):
                    submit_approval = getattr(required_action, 'submit_tool_approval', None)
                    if submit_approval:
                        if hasattr(submit_approval, 'tool_calls'):
                            tool_calls = getattr(submit_approval, 'tool_calls', [])
                        elif isinstance(submit_approval, dict) and 'tool_calls' in submit_approval:
                            tool_calls = submit_approval['tool_calls']
                
                # Method 3: submit_tool_outputs (fallback)
                if not tool_calls and hasattr(required_action, 'submit_tool_outputs'):
                    submit_outputs = getattr(required_action, 'submit_tool_outputs', None)
                    if submit_outputs and hasattr(submit_outputs, 'tool_calls'):
                        tool_calls = getattr(submit_outputs, 'tool_calls', [])
                
                if tool_calls:
                    print(f"\n   📋 Found {len(tool_calls)} tool call(s) requiring approval")
                    for tool_call in tool_calls:
                        # Handle both dict and object tool calls
                        if isinstance(tool_call, dict):
                            tool_id = tool_call.get('id')
                            tool_name = tool_call.get('name', 'unknown')
                            tool_type = tool_call.get('type', 'unknown')
                            print(f"\n   ✅ Tool Call: {tool_name} (type: {tool_type})")
                            if tool_id:
                                print(f"      Tool ID: {tool_id}")
                        elif RequiredMcpToolCall and isinstance(tool_call, RequiredMcpToolCall):
                            print(f"\n   ✅ MCP Tool Call: {tool_call.name}")
                            print(f"      Tool ID: {tool_call.id}")
                        elif hasattr(tool_call, 'name'):
                            tool_name = getattr(tool_call, 'name', 'unknown')
                            tool_id = getattr(tool_call, 'id', None)
                            print(f"\n   ✅ Tool Call: {tool_name}")
                            if tool_id:
                                print(f"      Tool ID: {tool_id}")
                    
                    # Submit approvals
                    if submit_tool_approvals(credential, thread_research.id, run_research.id, tool_calls):
                        print(f"\n   ✅ Tool approvals submitted successfully")
                        # Refresh run status after approval
                        time.sleep(2)
                        run_research = agents_client.runs.get(thread_id=thread_research.id, run_id=run_research.id)
                    else:
                        print(f"\n   ⚠️  Failed to submit tool approvals")
                elif waited == 10:  # Debug only once
                    print(f"\n   🔍 Debugging required_action (first time)...")
                    print(f"   Type: {type(required_action)}")
                    if hasattr(required_action, '_data'):
                        data = required_action._data
                        print(f"   _data type: {type(data)}")
                        if isinstance(data, dict):
                            print(f"   _data keys: {list(data.keys())}")
                            if 'submit_tool_approval' in data:
                                print(f"   Found submit_tool_approval in _data")
            
            if waited % 5 == 0 and run_research.status.value != "completed":
                print(f"   [INFO] Status: {run_research.status.value} (waited {waited}s)")
        
        wait_for_input("Press Enter to see Research Agent's response...", auto_mode)
        
        # Step 4: Research Agent -> Coordinator (A2A Response)
        print_header("STEP 4: Research Agent → Coordinator Agent (A2A Response)")
        
        if run_research.status.value == "completed":
            messages_research = agents_client.messages.list(
                thread_id=thread_research.id,
                order=ListSortOrder.ASCENDING
            )
            
            research_answer = None
            for msg in messages_research:
                if msg.role.value == "assistant" and msg.text_messages:
                    research_answer = msg.text_messages[-1].text.value
                    break
            
            if research_answer:
                print_a2a_message("Research Agent", "Coordinator Agent", "research_response", research_answer)
                print(f"\n✅ Research complete! Answer length: {len(research_answer)} characters")
                
                wait_for_input("Press Enter to continue to Executor Agent...", auto_mode)
                
                # Step 5: Coordinator -> Executor (A2A)
                print_header("STEP 5: Coordinator → Executor Agent (A2A)")
                executor_request = f"Please format and summarize this information: {research_answer[:500]}..."
                print_a2a_message("Coordinator Agent", "Executor Agent", "format_request", executor_request)
                
                thread_exec = agents_client.threads.create()
                msg_exec = agents_client.messages.create(
                    thread_id=thread_exec.id,
                    role="user",
                    content=f"Format and summarize: {research_answer}"
                )
                run_exec = agents_client.runs.create(
                    thread_id=thread_exec.id,
                    agent_id=executor_id
                )
                print(f"\n   ✅ A2A message sent to Executor Agent")
                print(f"   Thread ID: {thread_exec.id}")
                
                # Wait for executor
                max_wait_exec = 60
                waited_exec = 0
                while run_exec.status.value in ["queued", "in_progress"] and waited_exec < max_wait_exec:
                    time.sleep(2)
                    waited_exec += 2
                    run_exec = agents_client.runs.get(thread_id=thread_exec.id, run_id=run_exec.id)
                    if waited_exec % 5 == 0:
                        print(f"   [INFO] Status: {run_exec.status.value} (waited {waited_exec}s)")
                
                wait_for_input("Press Enter to see Executor Agent's response...", auto_mode)
                
                # Step 6: Executor -> Coordinator (A2A Response)
                print_header("STEP 6: Executor Agent → Coordinator Agent (A2A Response)")
                
                if run_exec.status.value == "completed":
                    messages_exec = agents_client.messages.list(
                        thread_id=thread_exec.id,
                        order=ListSortOrder.ASCENDING
                    )
                    
                    executor_answer = None
                    for msg in messages_exec:
                        if msg.role.value == "assistant" and msg.text_messages:
                            executor_answer = msg.text_messages[-1].text.value
                            break
                    
                    if executor_answer:
                        print_a2a_message("Executor Agent", "Coordinator Agent", "formatted_response", executor_answer)
                        print(f"\n✅ Formatting complete!")
                        
                        wait_for_input("Press Enter to see final answer...", auto_mode)
                        
                        # Step 7: Coordinator -> User (Final Answer)
                        print_header("STEP 7: Coordinator Agent → User (Final Answer)")
                        print_a2a_message("Coordinator Agent", "User", "final_answer", executor_answer)
                        
                        print("\n" + "="*70)
                        print("FINAL ANSWER:")
                        print("="*70)
                        print(executor_answer)
                        print("="*70)
                        
                        # Summary
                        print("\n" + "="*70)
                        print("A2A WORKFLOW SUMMARY")
                        print("="*70)
                        print("1. ✅ User → Coordinator Agent")
                        print("2. ✅ Coordinator → Research Agent (A2A)")
                        print("3. ✅ Research Agent → MCP Tools")
                        print("4. ✅ Research Agent → Coordinator (A2A)")
                        print("5. ✅ Coordinator → Executor Agent (A2A)")
                        print("6. ✅ Executor Agent → Coordinator (A2A)")
                        print("7. ✅ Coordinator → User")
                        print("\n🎉 Complete A2A workflow demonstrated!")
                        
                        return True
                    else:
                        print("⚠️  No answer from Executor Agent")
                        return False
                else:
                    print(f"⚠️  Executor Agent did not complete. Status: {run_exec.status.value}")
                    return False
            else:
                print("⚠️  No answer from Research Agent")
                return False
        else:
            print(f"⚠️  Research Agent did not complete. Status: {run_research.status.value}")
            return False


def main():
    """Main interactive demo."""
    import sys
    
    # Check if running in auto mode (no TTY)
    auto_mode = not sys.stdin.isatty()
    
    print("\n" + "="*70)
    print("Microsoft Agent Framework (MAF) - Interactive Demo")
    print("="*70)
    print("\nThis interactive demo will:")
    print("  1. Create three agents step-by-step")
    print("  2. Show A2A message passing between agents")
    print("  3. Demonstrate complete multi-agent workflow")
    
    if auto_mode:
        print("\n[INFO] Running in auto mode (non-interactive)")
    
    wait_for_input("\nReady to start? Press Enter...", auto_mode)
    
    credential = DefaultAzureCredential()
    
    # Create agents
    print_header("PHASE 1: CREATE AGENTS")
    
    with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
        agents_client = project_client.agents
        
        research_agent = create_research_agent(agents_client)
        wait_for_input("Press Enter to continue to Executor Agent...", auto_mode)
        
        executor_agent = create_executor_agent(agents_client)
        wait_for_input("Press Enter to continue to Coordinator Agent...", auto_mode)
        
        coordinator_agent = create_coordinator_agent(agents_client)
    
    # Save agent info
    with open("agents_info_interactive.json", "w") as f:
        json.dump(agents_info, f, indent=2)
    
    print_header("AGENT CREATION COMPLETE")
    print("\n✅ All Agents Created:")
    print(f"   • Research Agent:    {agents_info['research_agent']['agent_id']}")
    print(f"   • Executor Agent:    {agents_info['executor_agent']['agent_id']}")
    print(f"   • Coordinator Agent: {agents_info['coordinator_agent']['agent_id']}")
    print(f"\n✅ Agent info saved to: agents_info_interactive.json")
    
    auto_mode = not sys.stdin.isatty()
    wait_for_input("\nReady to demonstrate A2A communication? Press Enter...", auto_mode)
    
    # Demonstrate A2A workflow
    success = demonstrate_a2a_workflow(credential)
    
    if success:
        print("\n\n🎉 INTERACTIVE DEMO COMPLETED SUCCESSFULLY!")
    else:
        print("\n\n⚠️  Demo completed with some issues")
    
    print("\n" + "="*70)
    print("Thank you for using the MAF Interactive Demo!")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

