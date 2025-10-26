import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from typing_extensions import Never
from dataclasses import dataclass

from agent_framework import (
    WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, 
    Executor, handler, Case, Default
)

# Import our utilities
import sys
sys.path.append(str(Path(__file__).parent))
from invoice_utils import (
    InvoiceConfig, InvoiceData, read_invoices_csv, calculate_invoice_totals,
    render_invoice_text, save_invoice_file, archive_old_invoice, log_action, 
    ensure_directories, print_step
)

# Load environment
load_dotenv('.env03')

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive"
LOGS_DIR = BASE_DIR / "logs"

# Global selection
selected_invoice_id = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def show_menu(invoices: list[InvoiceData]) -> str:
    """Display invoice selection menu."""
    print("\n" + "="*80)
    print("AVAILABLE INVOICES")
    print("="*80)
    
    for idx, inv in enumerate(invoices, 1):
        preferred_badge = "PREFERRED" if inv.is_preferred else "STANDARD"
        print(f"{idx}. {preferred_badge} {inv.invoice_id} - {inv.client_name}")
        print(f"   Amount: ${inv.subtotal:.2f} | Date: {inv.date}")
        print()
    
    while True:
        try:
            choice = input(f"Select invoice (1-{len(invoices)}): ").strip()
            idx = int(choice)
            if 1 <= idx <= len(invoices):
                return invoices[idx - 1].invoice_id
            else:
                print(f"Please enter a number between 1 and {len(invoices)}")
        except ValueError:
            print("Please enter a valid number")


def wait_for_user(message: str):
    """Pause and wait for user."""
    print(f"\n{'-'*80}")
    input(f"Press ENTER to {message} -> ")
    print(f"{'-'*80}\n")


def analyze_invoice_routing(invoice: InvoiceData, config: InvoiceConfig) -> tuple[str, str]:
    """Analyze invoice and determine routing decision."""
    totals = calculate_invoice_totals(invoice, config)
    
    # Check if file exists (needs archiving)
    output_file = OUTPUT_DIR / f"{invoice.invoice_id}.txt"
    if output_file.exists():
        return "archive_needed", "Existing file found - needs archiving"
    
    # Check high value
    elif totals['subtotal'] >= config.high_value_threshold:
        return "high_value", f"High value (${totals['subtotal']:.2f}) - applying discount"
    
    # Check preferred client
    elif invoice.is_preferred:
        return "preferred", "Preferred client - applying loyalty discount"
    
    # Default to standard
    else:
        return "standard", "Normal processing"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class InvoiceDecision:
    """Represents a routing decision for an invoice."""
    invoice: InvoiceData
    config: InvoiceConfig
    totals: dict
    decision_type: str  # 'high_value', 'preferred', 'standard', 'archive_needed'
    reason: str


# ============================================================================
# BRANCHING WORKFLOW EXECUTORS
# ============================================================================

class InvoiceLoader(Executor):
    """Loads and analyzes selected invoice to determine routing."""
    
    @handler
    async def load_and_analyze(self, start_signal: str, ctx: WorkflowContext[InvoiceDecision]):
        """Load data and select invoice for analysis."""
        print_step(1, "LOAD & SELECT INVOICE")
        
        config = InvoiceConfig()
        csv_path = DATA_DIR / "invoices.csv"
        all_invoices = read_invoices_csv(str(csv_path))
        
        print(f"Loaded {len(all_invoices)} invoices")
        
        # Let user select
        global selected_invoice_id
        selected_invoice_id = show_menu(all_invoices)
        selected_invoice = next(inv for inv in all_invoices if inv.invoice_id == selected_invoice_id)
        
        print(f"\nSelected: {selected_invoice.invoice_id} - {selected_invoice.client_name}")
        print(f"   Amount: ${selected_invoice.subtotal:.2f}")
        print(f"   Preferred: {'YES' if selected_invoice.is_preferred else 'NO'}")
        
        # Analyze routing
        decision_type, reason = analyze_invoice_routing(selected_invoice, config)
        totals = calculate_invoice_totals(selected_invoice, config)
        
        print(f"\nANALYSIS RESULTS:")
        print(f"   Decision Type: {decision_type.upper()}")
        print(f"   Reason: {reason}")
        
        if decision_type == "high_value":
            print(f"   High Value Threshold: ${config.high_value_threshold:.2f}")
            print(f"   High Value Discount: ${totals['high_value_discount']:.2f}")
        elif decision_type == "preferred":
            print(f"   Loyalty Discount: ${totals['preferred_discount']:.2f}")
        
        decision = InvoiceDecision(
            invoice=selected_invoice,
            config=config,
            totals=totals,
            decision_type=decision_type,
            reason=reason
        )
        
        log_action(f"Selected and analyzed {selected_invoice_id}: {decision_type}", str(LOGS_DIR))
        
        wait_for_user("start BRANCHING workflow")
        
        await ctx.send_message(decision)


# ============================================================================
# CONDITION FUNCTIONS FOR ROUTING
# ============================================================================

def is_archive_needed(decision: InvoiceDecision) -> bool:
    """Check if invoice needs archiving."""
    return decision.decision_type == "archive_needed"


def is_high_value(decision: InvoiceDecision) -> bool:
    """Check if invoice is high value."""
    return decision.decision_type == "high_value"


def is_preferred(decision: InvoiceDecision) -> bool:
    """Check if invoice is for preferred client."""
    return decision.decision_type == "preferred"


# ============================================================================
# BRANCH HANDLERS
# ============================================================================

class ArchiveHandler(Executor):
    """Handles archiving of existing invoices."""
    
    @handler
    async def archive_old(self, decision: InvoiceDecision, ctx: WorkflowContext[InvoiceDecision]):
        """Archive the old invoice file."""
        print(f"\n[ARCHIVE BRANCH] {decision.invoice.invoice_id}")
        print(f"   Reason: {decision.reason}")
        
        ensure_directories(str(ARCHIVE_DIR))
        
        archived = archive_old_invoice(
            decision.invoice.invoice_id,
            str(OUTPUT_DIR),
            str(ARCHIVE_DIR)
        )
        
        if archived:
            print(f"   Old invoice archived to {ARCHIVE_DIR}")
            log_action(f"Archived old invoice {decision.invoice.invoice_id}", str(LOGS_DIR))
        
        # Continue to next decision point
        print(f"   Continuing to next routing decision...")
        
        # Re-analyze for next decision (now that archive is done)
        decision_type, reason = analyze_invoice_routing(decision.invoice, decision.config)
        decision.decision_type = decision_type
        decision.reason = reason
        
        print(f"   Next Decision: {decision_type.upper()}")
        print(f"   Reason: {reason}")
        
        wait_for_user("continue to NEXT BRANCH")
        
        await ctx.send_message(decision)


class HighValueHandler(Executor):
    """Handles high-value invoices with special discount."""
    
    @handler
    async def process_high_value(self, decision: InvoiceDecision, ctx: WorkflowContext[InvoiceDecision]):
        """Process high-value invoice."""
        print(f"\n[HIGH VALUE BRANCH] {decision.invoice.invoice_id}")
        print(f"   Reason: {decision.reason}")
        print(f"   Original Total: ${decision.totals['total']:.2f}")
        print(f"   High Value Discount: ${decision.totals['high_value_discount']:.2f}")
        print(f"   Special processing applied")
        
        log_action(f"Applied high-value discount to {decision.invoice.invoice_id}", str(LOGS_DIR))
        
        wait_for_user("proceed to FINALIZATION")
        
        await ctx.send_message(decision)


class PreferredClientHandler(Executor):
    """Handles preferred client invoices with loyalty discount."""
    
    @handler
    async def process_preferred(self, decision: InvoiceDecision, ctx: WorkflowContext[InvoiceDecision]):
        """Process preferred client invoice."""
        print(f"\n[PREFERRED CLIENT BRANCH] {decision.invoice.invoice_id}")
        print(f"   Reason: {decision.reason}")
        print(f"   Client: {decision.invoice.client_name}")
        print(f"   Original Total: ${decision.totals['total']:.2f}")
        print(f"   Loyalty Discount: ${decision.totals['preferred_discount']:.2f}")
        print(f"   Loyalty rewards applied")
        
        log_action(f"Applied preferred client discount to {decision.invoice.invoice_id}", str(LOGS_DIR))
        
        wait_for_user("proceed to FINALIZATION")
        
        await ctx.send_message(decision)


class StandardHandler(Executor):
    """Handles standard invoices."""
    
    @handler
    async def process_standard(self, decision: InvoiceDecision, ctx: WorkflowContext[InvoiceDecision]):
        """Process standard invoice."""
        print(f"\n[STANDARD BRANCH] {decision.invoice.invoice_id}")
        print(f"   Reason: {decision.reason}")
        print(f"   Client: {decision.invoice.client_name}")
        print(f"   Total: ${decision.totals['total']:.2f}")
        print(f"   Standard processing")
        
        log_action(f"Standard processing for {decision.invoice.invoice_id}", str(LOGS_DIR))
        
        wait_for_user("proceed to FINALIZATION")
        
        await ctx.send_message(decision)


class InvoiceFinalizer(Executor):
    """Renders and saves invoices after branch processing."""
    
    @handler
    async def finalize(self, decision: InvoiceDecision, ctx: WorkflowContext[Never, str]):
        """Render and save the invoice."""
        print_step(3, "RENDER & SAVE")
        
        # Render invoice
        invoice_text = render_invoice_text(
            decision.invoice,
            decision.totals,
            decision.config
        )
        
        # Add branch information
        branch_info = f"""
BRANCHING DECISION:
==================
Decision Type: {decision.decision_type.upper()}
Reason: {decision.reason}
Processing Path: {decision.decision_type.replace('_', ' ').title()}

"""
        
        # Combine invoice with branch info
        full_invoice_text = invoice_text + branch_info
        
        # Save to file
        ensure_directories(str(OUTPUT_DIR), str(LOGS_DIR))
        filepath = save_invoice_file(
            decision.invoice.invoice_id,
            full_invoice_text,
            str(OUTPUT_DIR)
        )
        
        print(f"Rendering invoice {decision.invoice.invoice_id}...")
        
        # Show preview
        print(f"\n{'-'*80}")
        print("INVOICE PREVIEW:")
        print(f"{'-'*80}")
        print(full_invoice_text)
        print(f"{'-'*80}")
        
        print(f"\nInvoice saved successfully!")
        print(f"   Location: {filepath}")
        print(f"   Branch: {decision.decision_type.upper()}")
        print(f"   Total: ${decision.totals['total']:.2f}")
        
        log_action(f"Finalized {decision.invoice.invoice_id} via {decision.decision_type} branch", str(LOGS_DIR))
        
        summary = f"Branching workflow completed! Invoice {decision.invoice.invoice_id} processed via {decision.decision_type} branch."
        await ctx.yield_output(summary)


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

async def run_workflow():
    """Run the branching workflow for ONE invoice."""
    
    # Create executors
    loader = InvoiceLoader(id="loader")
    archive_handler = ArchiveHandler(id="archive_handler")
    high_value_handler = HighValueHandler(id="high_value_handler")
    preferred_handler = PreferredClientHandler(id="preferred_handler")
    standard_handler = StandardHandler(id="standard_handler")
    finalizer = InvoiceFinalizer(id="finalizer")
    
    # Build the branching workflow with switch-case pattern
    workflow = (
        WorkflowBuilder()
        .set_start_executor(loader)
        # Route based on decision type
        .add_switch_case_edge_group(
            loader,
            [
                Case(condition=is_archive_needed, target=archive_handler),
                Case(condition=is_high_value, target=high_value_handler),
                Case(condition=is_preferred, target=preferred_handler),
                Default(target=standard_handler)
            ]
        )
        # Archive handler continues to next decision
        .add_switch_case_edge_group(
            archive_handler,
            [
                Case(condition=is_high_value, target=high_value_handler),
                Case(condition=is_preferred, target=preferred_handler),
                Default(target=standard_handler)
            ]
        )
        # All branches converge to finalizer
        .add_edge(high_value_handler, finalizer)
        .add_edge(preferred_handler, finalizer)
        .add_edge(standard_handler, finalizer)
        .build()
    )
    
    # Run the workflow
    async for event in workflow.run_stream("start"):
        if isinstance(event, WorkflowOutputEvent):
            print("\n" + "="*80)
            print("BRANCHING WORKFLOW COMPLETE")
            print("="*80)
            print(event.data)
            print("\nCheck the following directories:")
            print(f"   • Output: {OUTPUT_DIR}")
            print(f"   • Archive: {ARCHIVE_DIR}")
            print(f"   • Logs: {LOGS_DIR}")
            print("\nNote: Invoice followed its appropriate branch based on business rules!")
            print("="*80)


async def main():
    """Main entry point with loop."""
    
    print("\n" + "="*80)
    print("BRANCHING LOGIC WORKFLOW - INVOICE BUILDER")
    print("="*80)
    print("\nThis demo shows CONDITIONAL BRANCHING with interactive steps:")
    print("   • You select ONE invoice to process")
    print("   • System analyzes and determines routing path")
    print("   • Invoice follows appropriate branch:")
    print("     1. Existing file? -> Archive old version first")
    print("     2. High value invoice? -> Apply volume discount")
    print("     3. Preferred client? -> Apply loyalty discount")
    print("     4. Otherwise -> Standard processing")
    print("   • Final invoice rendered and saved")
    print("\nWorkflow Pattern:")
    print("   Loader -> [Archive Check] -> [Value/Preferred/Standard Branches] -> Finalizer")
    print("            +-------- CONDITIONAL ROUTING --------+")
    print("="*80)
    
    while True:
        await run_workflow()
        
        print("\n" + "="*80)
        choice = input("\nProcess another invoice? (y/n): ").strip().lower()
        
        if choice != 'y':
            print("\nThank you for using Invoice Builder!")
            print("="*80)
            break
        
        print("\n" + "="*80)
        print("RESTARTING WORKFLOW...")
        print("="*80)


if __name__ == "__main__":
    asyncio.run(main())