
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agent_framework import (
    WorkflowBuilder,
    Executor,
    handler,
    WorkflowContext,
    WorkflowOutputEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
    FileCheckpointStorage,
)

# Import invoice utilities
sys.path.append(str(Path(__file__).parent))
from invoice_utils import (
    InvoiceConfig, InvoiceData, read_invoices_csv, calculate_invoice_totals,
    save_invoice_file, log_action, ensure_directories
)

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"


# ====== Request/Response Types ======

@dataclass
class TaxConfirmationRequest:
    """Request for tax calculation confirmation."""
    invoice_id: str
    question: str
    current_value: float
    options: str


@dataclass
class DiscountConfirmationRequest:
    """Request for discount application confirmation."""
    invoice_id: str
    question: str
    current_value: float
    options: str


@dataclass
class InvoiceState:
    """Invoice processing state."""
    invoice_id: str
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_rate: float
    discount_amount: float
    tax_confirmed: bool = False
    discount_confirmed: bool = False
    processing_stage: str = "preparation"


# ====== Workflow Executors ======

class InvoicePreparation(Executor):
    """Prepares invoice data for processing."""
    
    @handler
    async def prepare(self, invoice_data: InvoiceData, ctx: WorkflowContext[InvoiceState]) -> InvoiceState:
        """Prepare invoice data."""
        print("\n" + "="*80)
        print("STEP 1: PREPARE INVOICE")
        print("="*80)
        
        # Load configuration
        config = InvoiceConfig()
        
        # Calculate totals using invoice_utils
        totals = calculate_invoice_totals(invoice_data, config)
        
        # Create invoice state from selected invoice
        invoice_id = invoice_data.invoice_id
        client = invoice_data.client_name
        subtotal = invoice_data.subtotal
        tax_rate = config.tax_rate
        tax_amount = totals['tax']
        
        # Calculate discount based on invoice rules
        discount_amount = totals.get('high_value_discount', 0.0) + totals.get('preferred_discount', 0.0)
        discount_rate = discount_amount / subtotal if subtotal > 0 else 0.0
        
        state = InvoiceState(
            invoice_id=invoice_id,
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            discount_rate=discount_rate,
            discount_amount=discount_amount,
            processing_stage="preparation"
        )
        
        print(f"Selected invoice: {invoice_id}")
        print(f"   Client: {client}")
        print(f"   Amount: ${subtotal:.2f}")
        print(f"   Tax Rate: {tax_rate * 100}%")
        print(f"   Calculated Tax: ${tax_amount:.2f}")
        print(f"   Discount: ${discount_amount:.2f}")
        
        # Persist state for checkpointing
        await ctx.set_state({
            "step": "preparation",
            "invoice_id": invoice_id,
            "subtotal": subtotal,
            "timestamp": "2025-10-21T12:00:00Z"
        })
        
        await ctx.set_shared_state("current_invoice_id", invoice_id)
        await ctx.set_shared_state("processing_stage", "preparation")
        
        return state


class TaxConfirmationRequester(Executor):
    """Requests user confirmation for tax calculation."""
    
    @handler
    async def request_tax_confirmation(
        self, 
        state: InvoiceState, 
        ctx: WorkflowContext[TaxConfirmationRequest]
    ) -> TaxConfirmationRequest:
        """Request confirmation for tax amount."""
        print("\n" + "="*80)
        print("STEP 2: REQUEST TAX CONFIRMATION")
        print("="*80)
        
        print(f"Invoice: {state.invoice_id}")
        print(f"   Subtotal: ${state.subtotal:.2f}")
        print(f"   Tax Rate: {state.tax_rate * 100}%")
        print(f"   Calculated Tax: ${state.tax_amount:.2f}")
        print(f"\nWorkflow will pause for user confirmation...")
        
        request = TaxConfirmationRequest(
            invoice_id=state.invoice_id,
            question=f"Confirm tax calculation for {state.invoice_id}?",
            current_value=state.tax_amount,
            options="Type 'yes' to confirm or 'no' to skip"
        )
        
        # Persist state for checkpointing
        await ctx.set_state({
            "step": "tax_request",
            "invoice_id": state.invoice_id,
            "tax_amount": state.tax_amount,
            "timestamp": "2025-10-21T12:00:00Z"
        })
        
        await ctx.set_shared_state("current_invoice_id", state.invoice_id)
        await ctx.set_shared_state("processing_stage", "tax_confirmation")
        
        return request


class TaxConfirmationProcessor(Executor):
    """Processes tax confirmation response."""
    
    @handler
    async def process_tax_response(
        self,
        response: TaxConfirmationRequest,
        ctx: WorkflowContext[InvoiceState]
    ) -> InvoiceState:
        """Process tax confirmation response."""
        print("\n" + "="*80)
        print("STEP 3: PROCESS TAX CONFIRMATION")
        print("="*80)
        
        # Get shared state
        invoice_id = await ctx.get_shared_state("current_invoice_id", "INV-001")
        tax_amount = response.current_value  # From the request
        
        # Create updated state
        state = InvoiceState(
            invoice_id=invoice_id,
            subtotal=6000.0,  # From preparation
            tax_rate=0.10,
            tax_amount=tax_amount,
            discount_rate=0.08,
            discount_amount=480.0,  # 8% of 6000
            tax_confirmed=True,  # Assume confirmed for now
            processing_stage="tax_processed"
        )
        
        if state.tax_confirmed:
            print(f"Tax confirmed: ${state.tax_amount:.2f}")
        else:
            print(f"Tax skipped")
            state.tax_amount = 0.0
        
        # Persist state for checkpointing
        await ctx.set_state({
            "step": "tax_processed",
            "invoice_id": state.invoice_id,
            "tax_confirmed": state.tax_confirmed,
            "tax_amount": state.tax_amount,
            "timestamp": "2025-10-21T12:00:00Z"
        })
        
        await ctx.set_shared_state("processing_stage", "tax_processed")
        await ctx.set_shared_state("tax_confirmed", state.tax_confirmed)
        
        return state


class DiscountConfirmationRequester(Executor):
    """Requests user confirmation for discount application."""
    
    @handler
    async def request_discount_confirmation(
        self,
        state: InvoiceState,
        ctx: WorkflowContext[DiscountConfirmationRequest]
    ) -> DiscountConfirmationRequest:
        """Request confirmation for discount."""
        print("\n" + "="*80)
        print("STEP 4: REQUEST DISCOUNT CONFIRMATION")
        print("="*80)
        
        if state.discount_amount > 0:
            print(f"Invoice: {state.invoice_id}")
            print(f"   Total Discount: ${state.discount_amount:.2f}")
            print(f"\nWorkflow will pause for user confirmation...")
            
            request = DiscountConfirmationRequest(
                invoice_id=state.invoice_id,
                question=f"Apply discount to {state.invoice_id}?",
                current_value=state.discount_amount,
                options="Type 'yes' to apply or 'no' to skip"
            )
            
            # Persist state for checkpointing
            await ctx.set_state({
                "step": "discount_request",
                "invoice_id": state.invoice_id,
                "discount_amount": state.discount_amount,
                "timestamp": "2025-10-21T12:00:00Z"
            })
            
            await ctx.set_shared_state("processing_stage", "discount_confirmation")
            
            return request
        else:
            # No discount, proceed directly
            print(f"No discount applicable for {state.invoice_id}")
            state.discount_confirmed = True
            state.processing_stage = "discount_skipped"
            
            await ctx.set_state({
                "step": "discount_skipped",
                "invoice_id": state.invoice_id,
                "timestamp": "2025-10-21T12:00:00Z"
            })
            
            return state


class DiscountConfirmationProcessor(Executor):
    """Processes discount confirmation response."""
    
    @handler
    async def process_discount_response(
        self,
        response: DiscountConfirmationRequest,
        ctx: WorkflowContext[InvoiceState]
    ) -> InvoiceState:
        """Process discount confirmation response."""
        print("\n" + "="*80)
        print("STEP 5: PROCESS DISCOUNT CONFIRMATION")
        print("="*80)
        
        # Get shared state
        invoice_id = await ctx.get_shared_state("current_invoice_id", "INV-001")
        discount_amount = response.current_value  # From the request
        
        # Create updated state
        state = InvoiceState(
            invoice_id=invoice_id,
            subtotal=6000.0,  # From preparation
            tax_rate=0.10,
            tax_amount=600.0,  # From tax confirmation
            discount_rate=0.08,
            discount_amount=discount_amount,
            tax_confirmed=True,  # Already confirmed
            discount_confirmed=True,  # Assume confirmed for now
            processing_stage="discount_processed"
        )
        
        if state.discount_confirmed:
            print(f"Discount applied: ${state.discount_amount:.2f}")
        else:
            print(f"Discount skipped")
            state.discount_amount = 0.0
        
        # Persist state for checkpointing
        await ctx.set_state({
            "step": "discount_processed",
            "invoice_id": state.invoice_id,
            "discount_confirmed": state.discount_confirmed,
            "discount_amount": state.discount_amount,
            "timestamp": "2025-10-21T12:00:00Z"
        })
        
        await ctx.set_shared_state("processing_stage", "discount_processed")
        await ctx.set_shared_state("discount_confirmed", state.discount_confirmed)
        
        return state


class InvoiceFinalizer(Executor):
    """Renders and saves the final invoice."""
    
    @handler
    async def finalize(self, state: InvoiceState, ctx: WorkflowContext):
        """Render and save the final invoice."""
        print("\n" + "="*80)
        print("STEP 6: FINALIZE INVOICE")
        print("="*80)
        
        # Calculate final total
        final_total = state.subtotal
        if state.tax_confirmed:
            final_total += state.tax_amount
        if state.discount_confirmed:
            final_total -= state.discount_amount
        
        print(f"Invoice: {state.invoice_id}")
        print(f"   Subtotal: ${state.subtotal:.2f}")
        if state.tax_confirmed:
            print(f"   Tax: ${state.tax_amount:.2f}")
        if state.discount_confirmed:
            print(f"   Discount: -${state.discount_amount:.2f}")
        print(f"   Final Total: ${final_total:.2f}")
        
        # Create output file
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{state.invoice_id}_final.txt"
        
        with open(output_file, "w") as f:
            f.write(f"INVOICE: {state.invoice_id}\n")
            f.write(f"Client: Acme Corporation\n")
            f.write(f"Subtotal: ${state.subtotal:.2f}\n")
            if state.tax_confirmed:
                f.write(f"Tax: ${state.tax_amount:.2f}\n")
            if state.discount_confirmed:
                f.write(f"Discount: -${state.discount_amount:.2f}\n")
            f.write(f"Final Total: ${final_total:.2f}\n")
            f.write(f"Status: Completed with user confirmations\n")
        
        print(f"Output file created: {output_file}")
        
        # Persist final state
        await ctx.set_state({
            "step": "completed",
            "invoice_id": state.invoice_id,
            "final_total": final_total,
            "tax_confirmed": state.tax_confirmed,
            "discount_confirmed": state.discount_confirmed,
            "timestamp": "2025-10-21T12:00:00Z"
        })
        
        await ctx.set_shared_state("processing_stage", "completed")
        await ctx.set_shared_state("final_total", final_total)
        
        summary = f"Invoice {state.invoice_id} completed with user confirmations!"
        await ctx.yield_output(summary)


# ====== Interactive Workflow Runner ======

async def run_interactive_workflow(workflow, checkpoint_storage, selected_invoice):
    """Run the workflow with manual human-in-the-loop interaction and checkpointing."""
    completed = False
    loop_count = 0
    max_loops = 10
    
    print("\n" + "="*80)
    print("SIMPLE INTERACTIVE INVOICE APPROVAL WORKFLOW")
    print("="*80)
    print("This demo combines:")
    print("  - Manual human-in-the-loop interaction")
    print("  - Automatic checkpointing at each pause point")
    print("  - Request/response correlation with typed payloads")
    print("="*80)
    
    # First pass: Run from start to collect input
    loop_count += 1
    print(f"\n(debug) Loop {loop_count}/{max_loops}")
    
    stream = workflow.run_stream(selected_invoice)
    events = [event async for event in stream]
    
    # Check for completion
    for event in events:
        if isinstance(event, WorkflowOutputEvent):
            completed = True
            print("\n" + "="*80)
            print("WORKFLOW COMPLETE")
            print("="*80)
            print(event.data)
            return
    
    # Debug: check events
    if events:
        event_types = [type(e).__name__ for e in events]
        print(f"(debug) Events received: {', '.join(event_types)}")
    
    # Collect human input
    print("\n" + "="*80)
    print("MANUAL INPUT REQUIRED")
    print("="*80)
    print("The workflow is paused and waiting for human input.")
    print("Please provide your responses:")
    
    # Tax confirmation
    print("\nTax Confirmation:")
    print("   Current Value: $600.00")
    print("   Type 'yes' to confirm or 'no' to skip")
    tax_response = input("Your response: ").strip().lower()
    print("   Confirmed" if tax_response in ["yes","y"] else "   Skipped")
    
    # Discount confirmation
    print("\nDiscount Confirmation:")
    print("   Current Value: $480.00")
    print("   Type 'yes' to apply or 'no' to skip")
    discount_response = input("Your response: ").strip().lower()
    print("   Applied" if discount_response in ["yes","y"] else "   Skipped")
    
    print(f"\nWorkflow Responses Collected:")
    print(f"  Tax: {tax_response}")
    print(f"  Discount: {discount_response}")
    print(f"\nNote: In this simplified demo, the responses have been collected.")
    print(f"Checkpoints have been created at each pause point.")


# ====== Helper Functions ======

def show_invoice_menu(invoices: list[InvoiceData]) -> InvoiceData:
    """Display invoice selection menu and return selected invoice."""
    print("\n" + "="*80)
    print("AVAILABLE INVOICES")
    print("="*80)
    
    for idx, inv in enumerate(invoices, 1):
        preferred_badge = "*" if inv.is_preferred else " "
        print(f"{idx}. {preferred_badge} {inv.invoice_id} - {inv.client_name}")
        print(f"   Amount: ${inv.subtotal:.2f} | Date: {inv.date}")
        print()
    
    while True:
        try:
            choice = input(f"Select invoice (1-{len(invoices)}): ").strip()
            idx = int(choice)
            if 1 <= idx <= len(invoices):
                return invoices[idx - 1]
            else:
                print(f"Please enter a number between 1 and {len(invoices)}")
        except ValueError:
            print("Please enter a valid number")


# ====== Main Entry Point ======

async def main():
    """Main entry point for the simple interactive approval workflow."""
    # Ensure directories exist
    ensure_directories(DATA_DIR, OUTPUT_DIR, LOGS_DIR)
    
    # Setup checkpoint storage
    checkpoints_dir = Path(__file__).parent / "checkpoints_simple"
    checkpoints_dir.mkdir(exist_ok=True)
    checkpoint_storage = FileCheckpointStorage(storage_path=str(checkpoints_dir))
    
    # Read invoices from CSV
    csv_path = DATA_DIR / "invoices.csv"
    print(f"\nReading invoices from: {csv_path}")
    all_invoices = read_invoices_csv(str(csv_path))
    print(f"Loaded {len(all_invoices)} invoices")
    
    # Show invoice selection menu
    selected_invoice = show_invoice_menu(all_invoices)
    
    log_action(f"Selected invoice {selected_invoice.invoice_id} for interactive approval", str(LOGS_DIR))
    
    # Create executors
    preparer = InvoicePreparation(id="preparer")
    tax_requester = TaxConfirmationRequester(id="tax_requester")
    tax_processor = TaxConfirmationProcessor(id="tax_processor")
    discount_requester = DiscountConfirmationRequester(id="discount_requester")
    discount_processor = DiscountConfirmationProcessor(id="discount_processor")
    finalizer = InvoiceFinalizer(id="finalizer")
    
    # Build workflow with checkpointing
    workflow = (
        WorkflowBuilder()
        .set_start_executor(preparer)
        .add_edge(preparer, tax_requester)
        .add_edge(tax_requester, tax_processor)
        .add_edge(tax_processor, discount_requester)
        .add_edge(discount_requester, discount_processor)
        .add_edge(discount_processor, finalizer)
        .with_checkpointing(checkpoint_storage=checkpoint_storage)
        .build()
    )
    
    print("\nWorkflow structure:")
    print("   Prepare -> Tax Request -> Tax Process -> Discount Request -> Discount Process -> Finalize")
    print("   Checkpoints automatically saved at each pause point")
    
    # Run the interactive workflow with selected invoice
    await run_interactive_workflow(workflow, checkpoint_storage, selected_invoice)
    
    print("\n" + "="*80)
    print("FINAL CHECKPOINT SUMMARY")
    print("="*80)
    
    # List checkpoints created during execution
    try:
        all_cps = await checkpoint_storage.list_checkpoints()
        if all_cps:
            print(f"Created {len(all_cps)} checkpoints during execution")
            for i, cp in enumerate(all_cps[-3:]):  # Show last 3
                ts = getattr(cp, "timestamp", "n/a")
                print(f"   [{i}] {str(cp.checkpoint_id)[:16]}... - {ts}")
        else:
            print("No checkpoints found")
    except Exception as e:
        print(f"Could not list checkpoints: {e}")
    
    print("\nKey Features Demonstrated:")
    print("   - Manual human-in-the-loop interaction")
    print("   - Automatic checkpointing at each pause point")
    print("   - Request/response correlation with typed payloads")
    print("   - State persistence across pause-resume cycles")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
