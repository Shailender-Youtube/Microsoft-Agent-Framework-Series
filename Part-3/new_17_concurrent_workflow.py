import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from typing_extensions import Never
from dataclasses import dataclass

from agent_framework import WorkflowBuilder, WorkflowContext, WorkflowOutputEvent, Executor, handler

# Import our utilities
import sys
sys.path.append(str(Path(__file__).parent))
from invoice_utils import (
    InvoiceConfig, InvoiceData, read_invoices_csv, calculate_invoice_totals,
    render_invoice_text, save_invoice_file, log_action, ensure_directories,
    print_step
)

# Load environment
load_dotenv('.env03')

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
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


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class InvoiceWithConfig:
    """Invoice with configuration."""
    invoice: InvoiceData
    config: InvoiceConfig


@dataclass
class TotalsResult:
    """Result from totals calculation."""
    invoice_id: str
    totals: dict


@dataclass
class ClientResult:
    """Result from client preparation."""
    invoice_id: str
    client_info: dict


@dataclass
class CreditResult:
    """Result from credit check."""
    invoice_id: str
    credit_check: dict


@dataclass
class MergedResult:
    """Merged results from all three parallel tasks."""
    invoice: InvoiceData
    config: InvoiceConfig
    totals: dict
    client_info: dict
    credit_check: dict


# ============================================================================
# CONCURRENT WORKFLOW EXECUTORS
# ============================================================================

class Dispatcher(Executor):
    """Loads and dispatches invoice to parallel processors."""
    
    @handler
    async def dispatch(self, start_signal: str, ctx: WorkflowContext[InvoiceWithConfig]):
        """Load data and select invoice."""
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
        
        log_action(f"Selected invoice {selected_invoice_id} for parallel processing", str(LOGS_DIR))
        
        wait_for_user("start PARALLEL processing")
        
        data = InvoiceWithConfig(invoice=selected_invoice, config=config)
        await ctx.send_message(data)


class TotalsCalculator(Executor):
    """Calculates invoice totals (PARALLEL TASK 1)."""
    
    @handler
    async def calculate(self, data: InvoiceWithConfig, ctx: WorkflowContext[TotalsResult]):
        """Calculate totals."""
        print(f"\n[TOTALS] Calculating totals for {data.invoice.invoice_id}...")
        
        # Simulate some processing time
        await asyncio.sleep(0.1)
        
        totals = calculate_invoice_totals(data.invoice, data.config)
        
        print(f"   Calculation Complete!")
        print(f"      Subtotal: ${totals['subtotal']:.2f}")
        print(f"      Discounts: -${totals['total_discount']:.2f}")
        print(f"      Tax: ${totals['tax']:.2f}")
        print(f"      Total: ${totals['total']:.2f}")
        
        result = TotalsResult(invoice_id=data.invoice.invoice_id, totals=totals)
        await ctx.send_message(result)


class ClientInfoPreparer(Executor):
    """Prepares client information (PARALLEL TASK 2)."""
    
    @handler
    async def prepare(self, data: InvoiceWithConfig, ctx: WorkflowContext[ClientResult]):
        """Prepare client info."""
        print(f"\n[CLIENT] Preparing client info for {data.invoice.invoice_id}...")
        
        # Simulate some processing time
        await asyncio.sleep(0.5)
        
        client_info = {
            'name': data.invoice.client_name,
            'email': data.invoice.client_email,
            'is_preferred': data.invoice.is_preferred,
            'status': 'VIP' if data.invoice.is_preferred else 'Standard',
            'greeting': f"Dear {data.invoice.client_name},",
            'account_manager': f"AM-{data.invoice.client_name[:3].upper()}",
            'last_order_date': '2024-12-01' if data.invoice.is_preferred else '2024-11-15'
        }
        
        print(f"   Client Info Ready!")
        print(f"      Name: {client_info['name']}")
        print(f"      Status: {client_info['status']}")
        print(f"      Email: {client_info['email']}")
        print(f"      Account Manager: {client_info['account_manager']}")
        
        result = ClientResult(invoice_id=data.invoice.invoice_id, client_info=client_info)
        await ctx.send_message(result)


class CreditChecker(Executor):
    """Performs credit checks (PARALLEL TASK 3)."""
    
    @handler
    async def check_credit(self, data: InvoiceWithConfig, ctx: WorkflowContext[CreditResult]):
        """Perform credit check."""
        print(f"\n[CREDIT] Processing credit check for {data.invoice.invoice_id}...")
        
        # Simulate credit check processing time
        await asyncio.sleep(0.8)
        
        # Simulate credit check logic based on invoice amount and client status
        invoice_amount = data.invoice.subtotal
        is_preferred = data.invoice.is_preferred
        
        # Credit scoring logic
        if is_preferred:
            credit_score = 850
            credit_limit = 50000
            risk_level = "LOW"
        elif invoice_amount > 5000:
            credit_score = 720
            credit_limit = 25000
            risk_level = "MEDIUM"
        else:
            credit_score = 650
            credit_limit = 10000
            risk_level = "MEDIUM"
        
        # Check if invoice amount is within credit limit
        approved = invoice_amount <= credit_limit
        
        credit_check = {
            'credit_score': credit_score,
            'credit_limit': credit_limit,
            'risk_level': risk_level,
            'approved': approved,
            'invoice_amount': invoice_amount,
            'available_credit': credit_limit - invoice_amount if approved else 0,
            'check_timestamp': '2024-12-09T10:30:00Z'
        }
        
        status = "APPROVED" if approved else "DECLINED"
        print(f"   Credit Check Complete!")
        print(f"      Status: {status}")
        print(f"      Score: {credit_score}")
        print(f"      Limit: ${credit_limit:,.0f}")
        print(f"      Risk: {risk_level}")
        
        result = CreditResult(invoice_id=data.invoice.invoice_id, credit_check=credit_check)
        await ctx.send_message(result)


class ResultsMerger(Executor):
    """Merges results from all three parallel tasks."""
    
    def __init__(self):
        super().__init__(id="merger")
        self.totals_result = None
        self.client_result = None
        self.credit_result = None
        self.original_data = None
    
    @handler
    async def merge_totals(self, result: TotalsResult, ctx: WorkflowContext[MergedResult]):
        """Receive totals result."""
        self.totals_result = result
        print(f"\n[MERGER] Received TOTALS for {result.invoice_id}")
        await self._check_and_merge(ctx)
    
    @handler
    async def merge_client(self, result: ClientResult, ctx: WorkflowContext[MergedResult]):
        """Receive client result."""
        self.client_result = result
        print(f"[MERGER] Received CLIENT INFO for {result.invoice_id}")
        await self._check_and_merge(ctx)
    
    @handler
    async def merge_credit(self, result: CreditResult, ctx: WorkflowContext[MergedResult]):
        """Receive credit result."""
        self.credit_result = result
        print(f"[MERGER] Received CREDIT CHECK for {result.invoice_id}")
        await self._check_and_merge(ctx)
    
    @handler
    async def store_original(self, data: InvoiceWithConfig, ctx: WorkflowContext[MergedResult]):
        """Store original invoice data."""
        self.original_data = data
        await self._check_and_merge(ctx)
    
    async def _check_and_merge(self, ctx: WorkflowContext[MergedResult]):
        """Check if all three results are ready and merge."""
        if self.totals_result and self.client_result and self.credit_result and self.original_data:
            print(f"\n[MERGER] All three parallel tasks complete - merging results...")
            
            merged = MergedResult(
                invoice=self.original_data.invoice,
                config=self.original_data.config,
                totals=self.totals_result.totals,
                client_info=self.client_result.client_info,
                credit_check=self.credit_result.credit_check
            )
            
            wait_for_user("proceed to RENDERING")
            
            await ctx.send_message(merged)
            
            # Reset for next run
            self.totals_result = None
            self.client_result = None
            self.credit_result = None
            self.original_data = None


class InvoiceRenderer(Executor):
    """Renders and saves the final invoice."""
    
    @handler
    async def render(self, data: MergedResult, ctx: WorkflowContext[Never, str]):
        """Render and save invoice."""
        print_step(3, "RENDER & SAVE")
        
        ensure_directories(str(OUTPUT_DIR), str(LOGS_DIR))
        
        print(f"Rendering invoice {data.invoice.invoice_id}...")
        
        # Render invoice text
        invoice_text = render_invoice_text(data.invoice, data.totals, data.config)
        
        # Add credit check information
        credit_info = f"""
CREDIT CHECK RESULTS:
====================
Status: {'APPROVED' if data.credit_check['approved'] else 'DECLINED'}
Credit Score: {data.credit_check['credit_score']}
Credit Limit: ${data.credit_check['credit_limit']:,.2f}
Risk Level: {data.credit_check['risk_level']}
Invoice Amount: ${data.credit_check['invoice_amount']:,.2f}
Available Credit: ${data.credit_check['available_credit']:,.2f}
Check Date: {data.credit_check['check_timestamp']}

"""
        
        # Add client information
        client_info = f"""
CLIENT INFORMATION:
==================
Name: {data.client_info['name']}
Email: {data.client_info['email']}
Status: {data.client_info['status']}
Account Manager: {data.client_info['account_manager']}
Last Order: {data.client_info['last_order_date']}

"""
        
        # Combine all information
        full_invoice_text = invoice_text + credit_info + client_info
        
        # Show preview
        print(f"\n{'-'*80}")
        print("INVOICE PREVIEW:")
        print(f"{'-'*80}")
        print(full_invoice_text)
        print(f"{'-'*80}")
        
        # Save to file
        filepath = save_invoice_file(data.invoice.invoice_id, full_invoice_text, str(OUTPUT_DIR))
        
        print(f"\nInvoice saved successfully!")
        print(f"   Location: {filepath}")
        print(f"   Client: {data.client_info['name']} ({data.client_info['status']})")
        print(f"   Amount: ${data.totals['total']:.2f}")
        print(f"   Credit: {'APPROVED' if data.credit_check['approved'] else 'DECLINED'} (Score: {data.credit_check['credit_score']})")
        
        log_action(f"Rendered and saved {data.invoice.invoice_id} using concurrent workflow with credit check", str(LOGS_DIR))
        
        summary = f"Concurrent workflow completed! Invoice {data.invoice.invoice_id} processed with 3 parallel tasks."
        await ctx.yield_output(summary)


# ============================================================================
# MAIN WORKFLOW
# ============================================================================

async def run_workflow():
    """Run the concurrent workflow for ONE invoice."""
    
    # Create executors
    dispatcher = Dispatcher(id="dispatcher")
    totals_calc = TotalsCalculator(id="totals_calculator")
    client_prep = ClientInfoPreparer(id="client_preparer")
    credit_checker = CreditChecker(id="credit_checker")
    merger = ResultsMerger()
    renderer = InvoiceRenderer(id="renderer")
    
    # Build the concurrent workflow
    workflow = (
        WorkflowBuilder()
        .set_start_executor(dispatcher)
        # Fan-out: dispatcher sends to ALL THREE parallel executors AND merger
        .add_fan_out_edges(dispatcher, [totals_calc, client_prep, credit_checker, merger])
        # All three parallel tasks send to merger
        .add_edge(totals_calc, merger)
        .add_edge(client_prep, merger)
        .add_edge(credit_checker, merger)
        # Merger sends to renderer
        .add_edge(merger, renderer)
        .build()
    )
    
    # Run the workflow
    async for event in workflow.run_stream("start"):
        if isinstance(event, WorkflowOutputEvent):
            print("\n" + "="*80)
            print("CONCURRENT WORKFLOW COMPLETE")
            print("="*80)
            print(event.data)
            print("\nCheck the following directories:")
            print(f"   • Output: {OUTPUT_DIR}")
            print(f"   • Logs: {LOGS_DIR}")
            print("\nNote: Three parallel executors ran concurrently for better performance!")
            print("   Each invoice now includes totals, client info, AND credit check results!")
            print("="*80)


async def main():
    """Main entry point with loop."""
    
    print("\n" + "="*80)
    print("CONCURRENT WORKFLOW - INVOICE BUILDER")
    print("="*80)
    print("\nThis demo shows PARALLEL PROCESSING with interactive steps:")
    print("   • You select ONE invoice to process")
    print("   • THREE tasks run SIMULTANEOUSLY:")
    print("     1. Calculate totals (amounts, discounts, tax)")
    print("     2. Prepare client information (name, status, email)")
    print("     3. Perform credit check (score, limit, approval)")
    print("   • Results MERGE when all three tasks complete")
    print("   • Final invoice rendered and saved")
    print("\nWorkflow Pattern:")
    print("   Dispatcher -> [Totals Calculator + Client Preparer + Credit Checker] -> Merger -> Renderer")
    print("                 +----------- PARALLEL EXECUTION -----------+")
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