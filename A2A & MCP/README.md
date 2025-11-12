# MAF A2A: Microsoft Agent Framework with Agent-to-Agent Communication

This repository demonstrates **Microsoft Agent Framework (MAF)** concepts through two complementary scenarios, showcasing how AI agents can communicate with each other using Agent-to-Agent (A2A) protocol and leverage Model Context Protocol (MCP) tools.

## 📚 Overview

This project contains two distinct scenarios that demonstrate different approaches to building multi-agent systems:

1. **Scenario 1: Local Agents** - Custom Python agents running locally with Azure OpenAI
2. **Scenario 2: Azure AI Foundry Agents** - Cloud-hosted agents using Azure AI Foundry Agent Service

Both scenarios implement:
- ✅ **Agent-to-Agent (A2A) Communication** - Agents collaborating and delegating tasks
- ✅ **Model Context Protocol (MCP)** - Agents accessing external tools and services
- ✅ **Multi-Agent Orchestration** - Coordinator agents managing workflows
- ✅ **Microsoft Agent Framework Concepts** - Following MAF design patterns

---

## 🎯 Scenario Comparison

| Feature | Scenario 1: Local Agents | Scenario 2: Azure AI Foundry |
|---------|-------------------------|------------------------------|
| **Hosting** | Local Python processes | Azure Cloud Service |
| **MCP Servers** | Local MCP servers (Weather, File Ops) | Remote MCP server (Microsoft Learn) |
| **Agent Creation** | Custom Python classes | Azure AI Foundry SDK |
| **Infrastructure** | Self-managed | Azure-managed |
| **Best For** | Learning, prototyping, offline use | Production, scalability, enterprise |
| **Setup Complexity** | Medium | High (requires Azure resources) |
| **Cost** | Azure OpenAI API only | Azure AI Foundry + Azure OpenAI |

---

## 📁 Project Structure

```
MAF A2A/
├── scenario1_local_agents/          # Local agent implementation
│   ├── agents/                      # Three agent implementations
│   │   ├── agent1_research.py       # Research agent (Weather MCP)
│   │   ├── agent2_coordinator.py    # Coordinator agent
│   │   └── agent3_executor.py      # Executor agent (File MCP)
│   ├── mcp_servers/                 # Local MCP servers
│   │   ├── weather_server.py        # Weather information MCP server
│   │   └── file_operations_server.py # File operations MCP server
│   ├── run_scenario1.py             # Main orchestration script
│   ├── requirements.txt             # Python dependencies
│   └── README.md                    # Detailed Scenario 1 documentation
│
├── scenario2_azure_foundry/         # Azure-hosted agents
│   ├── interactive_maf_demo.py      # Interactive agent creation & A2A demo
│   ├── requirements.txt             # Python dependencies
│   ├── .env                         # Azure credentials (not in repo)
│   └── README.md                    # Detailed Scenario 2 documentation
│
└── README.md                        # This file
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- Azure OpenAI account (for both scenarios)
- Azure AI Foundry project (for Scenario 2 only)

### Choose Your Scenario

**Start with Scenario 1 if you:**
- Want to learn how A2A and MCP work at a low level
- Prefer running everything locally
- Want full control over agent implementation
- Are prototyping or experimenting

**Start with Scenario 2 if you:**
- Need production-ready, scalable agents
- Want to leverage Azure AI Foundry services
- Need access to Microsoft Learn documentation
- Prefer cloud-managed infrastructure

---

## 📖 Scenario 1: Local Agents

**Location:** `scenario1_local_agents/`

### Architecture

```
User Request
    ↓
Coordinator Agent (Orchestrates)
    ├─→ Research Agent (Weather MCP) → Local Weather Server
    └─→ Executor Agent (File MCP) → Local File Server
    ↓
Final Response
```

### Key Features

- **3 Custom Agents**: Research, Coordinator, Executor
- **2 Local MCP Servers**: Weather (port 8001), File Operations (port 8002)
- **A2A Protocol**: Custom implementation for agent communication
- **Full Control**: Complete access to agent logic and behavior

### Quick Start

```powershell
# 1. Install dependencies
cd scenario1_local_agents
pip install -r requirements.txt

# 2. Configure environment
cp .env.template .env
# Edit .env with your Azure OpenAI credentials

# 3. Start MCP servers (in separate terminals)
python mcp_servers/weather_server.py
python mcp_servers/file_operations_server.py

# 4. Run the scenario
python run_scenario1.py
```

### Example Workflow

**User:** "What's the weather in Seattle and save it to a file?"

1. Coordinator receives request
2. Coordinator → Research Agent (via A2A): "Get Seattle weather"
3. Research Agent → Weather MCP Server: `get_weather("Seattle")`
4. Research Agent → Coordinator (via A2A): Weather data
5. Coordinator → Executor Agent (via A2A): "Save weather data"
6. Executor Agent → File MCP Server: `write_file("seattle_weather.txt", data)`
7. Coordinator responds: "Weather saved to seattle_weather.txt"



---

## 📖 Scenario 2: Azure AI Foundry Agents

**Location:** `scenario2_azure_foundry/`

### Architecture

```
User Request
    ↓
Coordinator Agent (Azure AI Foundry)
    ↓ (A2A via Azure Threads)
Research Agent (Azure AI Foundry + Microsoft Learn MCP)
    ↓ (MCP Protocol)
Microsoft Learn MCP Server (Public API)
    ↓
Final Response
```

### Key Features

- **Cloud-Hosted Agents**: Managed by Azure AI Foundry
- **Microsoft Learn MCP**: Access to up-to-date Microsoft documentation
- **Azure SDK Integration**: Using `azure.ai.projects` and `azure.ai.agents`
- **Interactive Demo**: Step-by-step agent creation and A2A demonstration

### Quick Start

```powershell
# 1. Install dependencies
cd scenario2_azure_foundry
pip install -r requirements.txt

# 2. Configure environment
# Edit .env with your Azure AI Foundry credentials:
# - AZURE_AI_FOUNDRY_ENDPOINT
# - AZURE_AI_FOUNDRY_API_KEY
# - AZURE_AI_FOUNDRY_PROJECT
# - AZURE_AI_PROJECT_ENDPOINT
# - AZURE_OPENAI_ENDPOINT (optional, for local comparison)

# 3. Run interactive demo
python interactive_maf_demo.py
```

### Example Workflow

**User:** "Which regions support Azure AI Foundry Agent Service to use MCP?"

1. User asks Coordinator Agent
2. Coordinator → Research Agent (via A2A): "Search Microsoft Learn for MCP regions"
3. Research Agent → Microsoft Learn MCP: `microsoft_docs_search("MCP regions Azure AI Foundry")`
4. Research Agent → Microsoft Learn MCP: `microsoft_docs_fetch(article_url)`
5. Research Agent → Coordinator (via A2A): Found documentation with regions
6. Coordinator responds: Lists supported regions with citations



---

## 🔑 Key Concepts

### Agent-to-Agent (A2A) Communication

A2A allows agents to communicate directly with each other, enabling:
- **Task Delegation**: One agent can ask another to perform specific tasks
- **Collaborative Problem Solving**: Multiple agents working together
- **Specialization**: Agents can focus on their strengths

**Implementation:**
- **Scenario 1**: Custom message passing between Python objects
- **Scenario 2**: Azure AI Foundry threads enable A2A between cloud agents

### Model Context Protocol (MCP)

MCP provides a standardized way for agents to access external tools and data:
- **Tools**: Functions that agents can call (e.g., `get_weather`, `read_file`)
- **Servers**: Services that provide MCP tools (e.g., Weather Server, Microsoft Learn)
- **Protocol**: JSON-RPC based communication

**Implementation:**
- **Scenario 1**: Local MCP servers with custom tools
- **Scenario 2**: Remote Microsoft Learn MCP server for documentation access

### Microsoft Agent Framework (MAF)

MAF is a conceptual framework for building AI agents:
- **Not a separate package**: Implemented through Azure AI Foundry SDK
- **Design Patterns**: Coordinator, Research, Executor agent patterns
- **Best Practices**: Agent specialization, delegation, orchestration

---

## 🎓 Learning Path

### Beginner Path

1. **Start with Scenario 1**
   - Understand basic agent concepts
   - Learn how MCP servers work
   - See A2A communication in action
   - Modify agents to experiment

2. **Progress to Scenario 2**
   - Understand cloud-hosted agents
   - Learn Azure AI Foundry SDK
   - See production-ready patterns

### Advanced Path

1. **Extend Scenario 1**
   - Create new MCP servers with custom tools
   - Add more specialized agents
   - Implement complex multi-agent workflows

2. **Productionize Scenario 2**
   - Deploy agents to Azure
   - Integrate with enterprise systems
   - Add monitoring and logging
   - Scale to multiple regions

---

## 🛠️ Common Tasks

### Testing A2A Communication

**Scenario 1:**
```powershell
# Test individual agents
python scenario1_local_agents/agents/agent1_research.py
python scenario1_local_agents/agents/agent2_coordinator.py
```

**Scenario 2:**
```powershell
# Interactive demo shows A2A in real-time
python scenario2_azure_foundry/interactive_maf_demo.py
```

### Creating New MCP Tools

**Scenario 1:** Add tools to existing MCP servers or create new ones
**Scenario 2:** Connect to additional remote MCP servers via configuration

### Debugging

- **Scenario 1**: Check console logs, MCP server outputs
- **Scenario 2**: Check Azure portal, agent run history, thread messages

---

## 📋 Requirements by Scenario

### Scenario 1 Requirements

- Azure OpenAI account
- Python 3.8+
- Local network access (for MCP servers)

### Scenario 2 Requirements

- Azure AI Foundry project
- Azure OpenAI account
- Python 3.8+
- Azure CLI (`az login`) or API keys
- Internet access (for Microsoft Learn MCP)

---

## 🔧 Configuration

### Environment Variables

**Scenario 1** (`.env` in `scenario1_local_agents/`):
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
```

**Scenario 2** (`.env` in `scenario2_azure_foundry/`):
```bash
AZURE_AI_FOUNDRY_ENDPOINT=https://your-resource.services.ai.azure.com/
AZURE_AI_FOUNDRY_API_KEY=your-key
AZURE_AI_FOUNDRY_PROJECT=your-project-name
AZURE_AI_PROJECT_ENDPOINT=https://your-resource.services.ai.azure.com/api/projects/your-project
```

---

## 🐛 Troubleshooting

### Scenario 1 Issues

**MCP Servers Not Starting:**
- Check ports 8001 and 8002 are available
- Verify firewall settings
- Check Python dependencies installed

**Agents Not Communicating:**
- Ensure all MCP servers are running
- Check agent IDs match
- Review console logs

### Scenario 2 Issues

**Agent Creation Fails:**
- Verify Azure credentials in `.env`
- Check Azure AI Foundry project exists
- Ensure correct API version

**MCP Tools Not Working:**
- Verify Microsoft Learn MCP server URL
- Check tool approval status in Azure portal
- Review agent run logs

---

## 📚 Additional Resources

### Documentation

- [Azure AI Foundry Agents](https://learn.microsoft.com/en-us/azure/ai-foundry/agents/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [Azure AI Projects SDK](https://learn.microsoft.com/en-us/python/api/azure-ai-projects/)

### Examples

- [Microsoft Learn MCP Server](https://github.com/microsoftdocs/mcp)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

---

## 🤝 Contributing

This is a demonstration repository. Suggestions and improvements welcome!

---

## 📝 License

This project is for educational and demonstration purposes.

---

## 🎯 Next Steps

1. **Run Scenario 1** to understand the fundamentals
2. **Run Scenario 2** to see cloud implementation
3. **Experiment** with both to find what works for your use case
4. **Extend** by adding new agents, MCP servers, or tools

**Ready to build multi-agent systems! 🚀**

