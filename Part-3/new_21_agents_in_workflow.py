
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from typing_extensions import Never
from dataclasses import dataclass

from agent_framework import (
    WorkflowBuilder, WorkflowContext, WorkflowOutputEvent,
    Executor, handler, ChatAgent
)
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import AzureCliCredential
from azure.ai.projects.aio import AIProjectClient

# Import our utilities
import sys
sys.path.append(str(Path(__file__).parent))
from invoice_utils import (
    InvoiceConfig, InvoiceData, read_invoices_csv, calculate_invoice_totals,
    render_invoice_text, save_invoice_file, log_action, ensure_directories,
    print_step
)

# Load environment
load_dotenv('.env01')

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

# Azure AI configuration
PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
MODEL_DEPLOYMENT = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME")


# ============================================================================
# AGENT-BASED WORKFLOW EXECUTORS
# ============================================================================

class InvoiceAnalyzerAgent(Executor):
    """Agent that analyzes invoice data and provides business insights."""

    def __init__(self):
        super().__init__(id="invoice_analyzer")
        self.agent = None

    async def _ensure_agent(self):
        """Ensure the analysis agent is created or reused."""
        if self.agent is not None:
            return

        async with AzureCliCredential() as credential:
            async with AIProjectClient(
                endpoint=PROJECT_ENDPOINT,
                credential=credential
            ) as project_client:
                
                # Try to find existing agent first
                try:
                    agents = await project_client.agents.list_agents()
                    existing_agent = next((a for a in agents if a.name == "InvoiceAnalyzer"), None)
                    if existing_agent:
                        print(f"   🔄 Reusing existing agent: {existing_agent.id}")
                        self.agent = existing_agent
                        return
                except Exception:
                    pass  # Continue to create new agent
                
                # Create new agent if none exists
                self.agent = await project_client.agents.create_agent(
                    model=MODEL_DEPLOYMENT,
                    name="InvoiceAnalyzer",
                    instructions="""You are an expert financial analyst specializing in invoice analysis.
                    Analyze invoice data and provide:
                    1. Business insights about the client and transaction
                    2. Risk assessment (low/medium/high)
                    3. Recommendations for processing
                    4. Any unusual patterns or concerns

                    Be concise but thorough. Format your response as structured analysis."""
                )
                print(f"   ✅ Created new agent: {self.agent.id}")

    @handler
    async def analyze_invoice(self, invoice: InvoiceData, ctx: WorkflowContext[tuple[InvoiceData, dict]]) -> None:
        """Use agent to analyze invoice data."""
        print_step(2, "AGENT ANALYSIS")
        
        await self._ensure_agent()

        config = InvoiceConfig()
        totals = calculate_invoice_totals(invoice, config)

        analysis_prompt = f"""
        Please analyze this invoice:

        Invoice ID: {invoice.invoice_id}
        Client: {invoice.client_name} ({invoice.client_email})
        Item: {invoice.item_description}
        Quantity: {invoice.quantity}
        Unit Price: ${invoice.unit_price:.2f}
        Subtotal: ${invoice.subtotal:.2f}
        Preferred Client: {'Yes' if invoice.is_preferred else 'No'}
        Date: {invoice.date}

        Calculated Totals:
        - High Value Discount: ${totals['high_value_discount']:.2f}
        - Preferred Discount: ${totals['preferred_discount']:.2f}
        - Tax: ${totals['tax']:.2f}
        - Total Due: ${totals['total']:.2f}

        Business Rules:
        - High value threshold: ${config.high_value_threshold:.2f}
        - Tax rate: {config.tax_rate * 100}%
        - High value discount: {config.high_value_discount * 100}%
        - Preferred discount: {config.preferred_client_discount * 100}%

        Provide your analysis in a structured format.
        """

        print(f"🤖 Agent analyzing invoice {invoice.invoice_id}...")

        # Create agent client and run analysis
        async with AzureCliCredential() as credential:
            async with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
                async with ChatAgent(
                    chat_client=AzureAIAgentClient(
                        project_client=project_client,
                        agent_id=self.agent.id
                    )
                ) as agent:
                    result = await agent.run(analysis_prompt)
                    analysis = result.text
            print(f"\n📊 Agent Analysis Results:")
            print(f"{'─'*80}")
            print(analysis)
            print(f"{'─'*80}")

            # Parse analysis for workflow decisions
            analysis_data = {
                'agent_analysis': analysis,
                'risk_level': 'medium',  # Default
                'recommendations': [],
                'insights': []
            }

            # Simple parsing of agent response
            analysis_lower = analysis.lower()
            if 'high risk' in analysis_lower or 'concerning' in analysis_lower:
                analysis_data['risk_level'] = 'high'
            elif 'low risk' in analysis_lower or 'excellent' in analysis_lower:
                analysis_data['risk_level'] = 'low'

            log_action(f"Agent analyzed invoice {invoice.invoice_id}: risk={analysis_data['risk_level']}", str(LOGS_DIR))

            # Pass along invoice and analysis
            await ctx.send_message((invoice, analysis_data))
class CommunicationAgent(Executor):
    """Agent that generates personalized client communications."""

    def __init__(self):
        super().__init__(id="communication_agent")
        self.agent = None

    async def _ensure_agent(self):
        """Ensure the communication agent is created or reused."""
        if self.agent is not None:
            return

        async with AzureCliCredential() as credential:
            async with AIProjectClient(
                endpoint=PROJECT_ENDPOINT,
                credential=credential
            ) as project_client:
                
                # Try to find existing agent first
                try:
                    agents = await project_client.agents.list_agents()
                    existing_agent = next((a for a in agents if a.name == "ClientCommunicator"), None)
                    if existing_agent:
                        print(f"   🔄 Reusing existing agent: {existing_agent.id}")
                        self.agent = existing_agent
                        return
                except Exception:
                    pass  # Continue to create new agent
                
                # Create new agent if none exists
                self.agent = await project_client.agents.create_agent(
                    model=MODEL_DEPLOYMENT,
                    name="ClientCommunicator",
                    instructions="""You are a professional client communication specialist.
                    Generate personalized, professional communications for clients including:
                    1. Invoice acknowledgments
                    2. Payment reminders
                    3. Thank you notes
                    4. Special offers for preferred clients

                    Be friendly, professional, and concise. Tailor the tone to the client relationship."""
                )
                print(f"   ✅ Created new agent: {self.agent.id}")

    @handler
    async def generate_communication(self, data: tuple[InvoiceData, dict, str],
                                    ctx: WorkflowContext[tuple[InvoiceData, dict, str, str]]) -> None:
        """Generate personalized client communication."""
        print_step(4, "AGENT COMMUNICATION")

        invoice, analysis, decision = data
        await self._ensure_agent()

        config = InvoiceConfig()
        totals = calculate_invoice_totals(invoice, config)

        comm_prompt = f"""
        Generate a personalized invoice acknowledgment email for this client:

        Client Details:
        - Name: {invoice.client_name}
        - Email: {invoice.client_email}
        - Preferred Client: {'Yes' if invoice.is_preferred else 'No'}

        Invoice Details:
        - Invoice ID: {invoice.invoice_id}
        - Item: {invoice.item_description}
        - Amount: ${totals['total']:.2f}
        - Due Date: {invoice.date}
        - Processing Decision: {decision}

        Agent Analysis Summary: {analysis['agent_analysis'][:200]}...

        Generate a professional email acknowledgment. Include:
        1. Personalized greeting
        2. Invoice summary
        3. Any special notes based on client status and processing decision
        4. Professional closing

        Keep it concise and friendly.
        """

        print(f"🤖 Agent generating communication for {invoice.client_name}...")

        async with AzureCliCredential() as credential:
            async with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
                async with ChatAgent(
                    chat_client=AzureAIAgentClient(
                        project_client=project_client,
                        agent_id=self.agent.id
                    )
                ) as agent:
                    result = await agent.run(comm_prompt)
                    communication = result.text
            print(f"\n📧 Generated Communication:")
            print(f"{'─'*80}")
            print(communication)
            print(f"{'─'*80}")

            log_action(f"Agent generated communication for {invoice.invoice_id}", str(LOGS_DIR))

            await ctx.send_message((invoice, analysis, decision, communication))


class DecisionAgent(Executor):
    """Agent that makes business decisions about invoice processing."""

    def __init__(self):
        super().__init__(id="decision_agent")
        self.agent = None

    async def _ensure_agent(self):
        """Ensure the decision agent is created or reused."""
        if self.agent is not None:
            return

        async with AzureCliCredential() as credential:
            async with AIProjectClient(
                endpoint=PROJECT_ENDPOINT,
                credential=credential
            ) as project_client:
                
                # Try to find existing agent first
                try:
                    agents = await project_client.agents.list_agents()
                    existing_agent = next((a for a in agents if a.name == "BusinessDecisionMaker"), None)
                    if existing_agent:
                        print(f"   🔄 Reusing existing agent: {existing_agent.id}")
                        self.agent = existing_agent
                        return
                except Exception:
                    pass  # Continue to create new agent
                
                # Create new agent if none exists
                self.agent = await project_client.agents.create_agent(
                    model=MODEL_DEPLOYMENT,
                    name="BusinessDecisionMaker",
                    instructions="""You are a senior business decision maker for invoice processing.
                    Based on invoice data and analysis, decide on processing actions:

                    Available Actions:
                    1. APPROVE: Standard processing
                    2. PRIORITY: Fast-track processing
                    3. REVIEW: Requires manual review
                    4. HOLD: Temporarily hold processing

                    Consider: client status, amount, risk level, business rules.
                    Provide clear reasoning for your decision."""
                )
                print(f"   ✅ Created new agent: {self.agent.id}")

    @handler
    async def make_decision(self, data: tuple[InvoiceData, dict],
                           ctx: WorkflowContext[tuple[InvoiceData, dict, str]]) -> None:
        """Make business decision about processing."""
        print_step(3, "AGENT DECISION MAKING")

        invoice, analysis = data
        await self._ensure_agent()

        config = InvoiceConfig()
        totals = calculate_invoice_totals(invoice, config)

        decision_prompt = f"""
        Make a business decision about processing this invoice:

        Invoice: {invoice.invoice_id}
        Client: {invoice.client_name} (Preferred: {'Yes' if invoice.is_preferred else 'No'})
        Amount: ${totals['total']:.2f}
        Risk Level: {analysis['risk_level']}

        Agent Analysis: {analysis['agent_analysis'][:300]}...

        Business Rules:
        - High value threshold: $5,000
        - Preferred clients get priority
        - High risk requires review

        Decide on: APPROVE, PRIORITY, REVIEW, or HOLD
        Provide clear reasoning.
        """

        print(f"🤖 Agent making decision for invoice {invoice.invoice_id}...")

        async with AzureCliCredential() as credential:
            async with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
                async with ChatAgent(
                    chat_client=AzureAIAgentClient(
                        project_client=project_client,
                        agent_id=self.agent.id
                    )
                ) as agent:
                    result = await agent.run(decision_prompt)
                    decision = result.text
            print(f"\n⚖️  Agent Decision:")
            print(f"{'─'*80}")
            print(decision)
            print(f"{'─'*80}")

            # Determine processing path based on decision
            decision_text = decision.upper()
            if 'PRIORITY' in decision_text:
                processing_path = 'priority'
            elif 'REVIEW' in decision_text:
                processing_path = 'review'
            elif 'HOLD' in decision_text:
                processing_path = 'hold'
            else:
                processing_path = 'standard'

            log_action(f"Agent decided {processing_path} processing for {invoice.invoice_id}", str(LOGS_DIR))

            await ctx.send_message((invoice, analysis, processing_path))


class SummaryAgent(Executor):
    """Agent that creates executive summaries."""

    def __init__(self):
        super().__init__(id="summary_agent")
        self.agent = None

    async def _ensure_agent(self):
        """Ensure the summary agent is created or reused."""
        if self.agent is not None:
            return

        async with AzureCliCredential() as credential:
            async with AIProjectClient(
                endpoint=PROJECT_ENDPOINT,
                credential=credential
            ) as project_client:
                
                # Try to find existing agent first
                try:
                    agents = await project_client.agents.list_agents()
                    existing_agent = next((a for a in agents if a.name == "ExecutiveSummarizer"), None)
                    if existing_agent:
                        print(f"   🔄 Reusing existing agent: {existing_agent.id}")
                        self.agent = existing_agent
                        return
                except Exception:
                    pass  # Continue to create new agent
                
                # Create new agent if none exists
                self.agent = await project_client.agents.create_agent(
                    model=MODEL_DEPLOYMENT,
                    name="ExecutiveSummarizer",
                    instructions="""You are an executive assistant creating summaries for business processing.
                    Create concise executive summaries that include:
                    1. Key transaction details
                    2. Business decisions made
                    3. Client insights
                    4. Next steps or recommendations

                    Keep summaries professional and actionable."""
                )
                print(f"   ✅ Created new agent: {self.agent.id}")

    @handler
    async def create_summary(self, data: tuple[InvoiceData, dict, str, str],
                            ctx: WorkflowContext[Never, str]) -> None:
        """Create executive summary of the entire process."""
        print_step(5, "AGENT SUMMARY")

        invoice, analysis, decision, communication = data
        await self._ensure_agent()

        config = InvoiceConfig()
        totals = calculate_invoice_totals(invoice, config)

        summary_prompt = f"""
        Create an executive summary for this invoice processing:

        Invoice: {invoice.invoice_id}
        Client: {invoice.client_name}
        Total Amount: ${totals['total']:.2f}
        Processing Decision: {decision}

        Agent Analysis: {analysis['agent_analysis'][:200]}...
        Agent Decision: {decision}

        Communication Generated: Yes

        Create a concise executive summary highlighting key points and outcomes.
        """

        print(f"🤖 Agent creating executive summary...")

        async with AzureCliCredential() as credential:
            async with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
                async with ChatAgent(
                    chat_client=AzureAIAgentClient(
                        project_client=project_client,
                        agent_id=self.agent.id
                    )
                ) as agent:
                    result = await agent.run(summary_prompt)
                    summary = result.text
            print(f"\n📋 Executive Summary:")
            print(f"{'─'*80}")
            print(summary)
            print(f"{'─'*80}")

            # Save all agent outputs
            ensure_directories(str(OUTPUT_DIR), str(LOGS_DIR))

            full_report = f"""
EXECUTIVE SUMMARY - INVOICE {invoice.invoice_id}
{'='*80}

CLIENT INFORMATION:
- Name: {invoice.client_name}
- Email: {invoice.client_email}
- Preferred: {'Yes' if invoice.is_preferred else 'No'}

FINANCIAL DETAILS:
- Subtotal: ${totals['subtotal']:.2f}
- Total Due: ${totals['total']:.2f}
- Processing Path: {decision}

AGENT ANALYSIS:
{analysis['agent_analysis']}

AGENT DECISION:
{decision}

CLIENT COMMUNICATION:
{communication}

EXECUTIVE SUMMARY:
{summary}

{'='*80}
            """

            filepath = save_invoice_file(f"{invoice.invoice_id}_agent_report", full_report, str(OUTPUT_DIR))

            log_action(f"Agent workflow completed for {invoice.invoice_id}", str(LOGS_DIR))

            final_summary = f"✅ Agent workflow completed! Invoice {invoice.invoice_id} processed with AI assistance."
            await ctx.yield_output(final_summary)


# ============================================================================
# TRADITIONAL EXECUTORS (for workflow structure)
# ============================================================================

class InvoiceSelector(Executor):
    """Traditional executor to select invoice (no agent needed)."""

    @handler
    async def select_invoice(self, start_signal: str, ctx: WorkflowContext[InvoiceData]) -> None:
        """Load and let user select invoice."""
        print_step(1, "SELECT INVOICE")

        config = InvoiceConfig()
        csv_path = DATA_DIR / "invoices.csv"
        invoices = read_invoices_csv(str(csv_path))

        print(f"Loaded {len(invoices)} invoices")

        # Simple selection for demo (first invoice)
        invoice = invoices[0]

        print(f"Selected: {invoice.invoice_id} - {invoice.client_name}")
        print(f"Amount: ${invoice.subtotal:.2f}")

        log_action(f"Selected invoice {invoice.invoice_id} for agent processing", str(LOGS_DIR))

        await ctx.send_message(invoice)


# ============================================================================
# CLEANUP FUNCTION
# ============================================================================

async def cleanup_agents(analyzer, decider, communicator, summarizer):
    """Clean up temporary agents created during the workflow."""
    print("\n🧹 Cleaning up temporary agents...")
    try:
        async with AzureCliCredential() as credential:
            async with AIProjectClient(endpoint=PROJECT_ENDPOINT, credential=credential) as project_client:
                executors = [analyzer, decider, communicator, summarizer]
                for executor in executors:
                    if getattr(executor, "agent", None) and getattr(executor.agent, "id", None):
                        try:
                            await project_client.agents.delete_agent(executor.agent.id)
                            print(f"   ✅ Deleted agent: {executor.agent.id}")
                        except Exception:
                            pass  # Keep it simple for the lab
    except Exception:
        pass
    print("   🧹 Cleanup complete")


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

async def run_agent_workflow():
    """Run the agent-integrated workflow."""

    # Create executors (mix of traditional and agent-based)
    selector = InvoiceSelector(id="selector")
    analyzer = InvoiceAnalyzerAgent()
    decider = DecisionAgent()
    communicator = CommunicationAgent()
    summarizer = SummaryAgent()

    # Build workflow with agents integrated at key steps
    workflow = (
        WorkflowBuilder()
        .set_start_executor(selector)
        .add_edge(selector, analyzer)
        .add_edge(analyzer, decider)
        .add_edge(decider, communicator)
        .add_edge(communicator, summarizer)
        .build()
    )

    # Run the workflow
    async for event in workflow.run_stream("start"):
        if isinstance(event, WorkflowOutputEvent):
            print("\n" + "="*80)
            print("🎉 AGENT WORKFLOW COMPLETE")
            print("="*80)
            print(event.data)
            print("\n📁 Check the following directories:")
            print(f"   • Output: {OUTPUT_DIR}")
            print(f"   • Logs: {LOGS_DIR}")
            print("\n🤖 This workflow used AI agents for:")
            print("   • Invoice analysis and risk assessment")
            print("   • Business decision making")
            print("   • Personalized client communication")
            print("   • Executive summary generation")
            print("="*80)
    
    # Cleanup agents after workflow completes
    await cleanup_agents(analyzer, decider, communicator, summarizer)


async def main():
    """Main entry point."""

    print("\n" + "="*80)
    print("🤖 AGENTS INSIDE WORKFLOWS - INVOICE BUILDER")
    print("="*80)
    print("\n✨ This demo shows AI AGENTS integrated into workflow steps:")
    print("   • Agent analyzes invoice data and provides insights")
    print("   • Agent makes business decisions about processing")
    print("   • Agent generates personalized client communications")
    print("   • Agent creates executive summaries")
    print("\n🔄 Workflow Pattern:")
    print("   Select → Analyze → Decide → Communicate → Summarize")
    print("   🤖      🤖       🤖         🤖           🤖")
    print("   (All middle steps use AI agents for intelligent processing)")
    print("="*80)

    # Check Azure AI configuration
    if not PROJECT_ENDPOINT or not MODEL_DEPLOYMENT:
        print("❌ Azure AI configuration missing. Please check your .env01 file.")
        print("   Required: AZURE_AI_PROJECT_ENDPOINT, AZURE_AI_MODEL_DEPLOYMENT_NAME")
        return

    await run_agent_workflow()

    print("\n" + "="*80)
    print("Demo completed! Agents successfully integrated into workflow processing.")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())