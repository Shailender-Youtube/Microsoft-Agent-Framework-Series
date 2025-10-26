
import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from typing_extensions import Never

from agent_framework import (
    WorkflowBuilder, WorkflowContext, Executor, handler,
    WorkflowViz, Case, Default
)

# Import our utilities
import sys
sys.path.append(str(Path(__file__).parent))
from invoice_utils import (
    InvoiceConfig, InvoiceData, read_invoices_csv, calculate_invoice_totals,
    render_invoice_text, save_invoice_file, archive_old_invoice, log_action,
    ensure_directories, print_step, print_invoice_summary
)

# Load environment
load_dotenv('.env03')

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive"
LOGS_DIR = BASE_DIR / "logs"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def show_workflow_menu() -> list[str]:
    """Display workflow pattern selection menu."""
    print("\n" + "="*80)
    print("WORKFLOW VISUALIZATION OPTIONS")
    print("="*80)
    print("Select which workflow patterns to visualize:")
    print()
    print("1. Sequential Workflow")
    print("   • Linear processing (A -> B -> C -> D)")
    print("   • Best for step-by-step operations")
    print("   • No parallelism or branching")
    print()
    print("2. Parallel Workflow")
    print("   • Concurrent processing with fan-out/fan-in")
    print("   • Best for independent concurrent tasks")
    print("   • Multiple tasks run simultaneously")
    print()
    print("3. Branching Workflow")
    print("   • Conditional routing with switch-case")
    print("   • Best for conditional routing based on data")
    print("   • Different paths based on conditions")
    print()
    print("4. All Workflows (Complete Demo)")
    print("   • Visualize all three patterns")
    print("   • Compare different approaches")
    print("   • Full demonstration")
    print()
    
    while True:
        try:
            choice = input("Enter your selection (1-4, or comma-separated like '1,3'): ").strip()
            
            if choice == "4":
                return ["sequential", "parallel", "branching"]
            
            # Parse comma-separated choices
            choices = [c.strip() for c in choice.split(",")]
            patterns = []
            
            for c in choices:
                if c == "1":
                    patterns.append("sequential")
                elif c == "2":
                    patterns.append("parallel")
                elif c == "3":
                    patterns.append("branching")
                else:
                    print(f"Invalid choice: {c}. Please enter 1, 2, 3, or 4.")
                    break
            else:
                if patterns:
                    return patterns
                else:
                    print("Please select at least one pattern.")
        except ValueError:
            print("Please enter valid numbers (1-4) or comma-separated choices.")


def wait_for_user(message: str):
    """Pause and wait for user."""
    print(f"\n{'-'*80}")
    input(f"Press ENTER to {message} -> ")
    print(f"{'-'*80}\n")


# ============================================================================
# SIMPLIFIED WORKFLOW EXECUTORS FOR VISUALIZATION
# ============================================================================

class LoadInvoices(Executor):
    """Loads invoices from CSV."""
    
    @handler
    async def load(self, start_signal: str, ctx: WorkflowContext[list[InvoiceData]]):
        config = InvoiceConfig()
        csv_path = DATA_DIR / "invoices.csv"
        invoices = read_invoices_csv(str(csv_path))
        await ctx.send_message(invoices)


class CalculateTotals(Executor):
    """Calculates totals for all invoices."""
    
    @handler
    async def calculate(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[tuple]]):
        config = InvoiceConfig()
        results = []
        for invoice in invoices:
            totals = calculate_invoice_totals(invoice, config)
            results.append((invoice, totals))
        await ctx.send_message(results)


class RenderInvoices(Executor):
    """Renders invoices to text."""
    
    @handler
    async def render(self, data: list[tuple], ctx: WorkflowContext[list[tuple]]):
        config = InvoiceConfig()
        results = []
        for invoice, totals in data:
            text = render_invoice_text(invoice, totals, config)
            results.append((invoice, totals, text))
        await ctx.send_message(results)


class SaveInvoices(Executor):
    """Saves invoices to files."""
    
    @handler
    async def save(self, data: list[tuple], ctx: WorkflowContext[Never, str]):
        ensure_directories(str(OUTPUT_DIR), str(LOGS_DIR))
        for invoice, totals, text in data:
            save_invoice_file(invoice.invoice_id, text, str(OUTPUT_DIR))
        await ctx.yield_output("All invoices saved!")


# Parallel processing executors
class Dispatcher(Executor):
    """Distributes invoices for parallel processing."""
    
    @handler
    async def dispatch(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        await ctx.send_message(invoices)


class TotalsCalculator(Executor):
    """Calculates invoice totals (parallel)."""
    
    @handler
    async def calculate(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        config = InvoiceConfig()
        totals_map = {inv.invoice_id: calculate_invoice_totals(inv, config) for inv in invoices}
        # Return the original invoices with totals attached
        for invoice in invoices:
            invoice.totals = totals_map[invoice.invoice_id]
        await ctx.send_message(invoices)


class ClientPreparer(Executor):
    """Prepares client information (parallel)."""
    
    @handler
    async def prepare(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        # Add client info to invoices
        for invoice in invoices:
            invoice.client_info = {"name": invoice.client_name, "email": invoice.client_email}
        await ctx.send_message(invoices)


class Merger(Executor):
    """Merges parallel results."""
    
    @handler
    async def merge(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        await ctx.send_message(invoices)


class Renderer(Executor):
    """Final rendering."""
    
    @handler
    async def render(self, invoices: list[InvoiceData], ctx: WorkflowContext[Never, str]):
        await ctx.yield_output("Rendering complete!")


# Branching workflow executors
class Analyzer(Executor):
    """Analyzes invoices for routing."""
    
    @handler
    async def analyze(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        await ctx.send_message(invoices)


class HighValueHandler(Executor):
    """Handles high-value invoices."""
    
    @handler
    async def handle(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        await ctx.send_message(invoices)


class PreferredHandler(Executor):
    """Handles preferred clients."""
    
    @handler
    async def handle(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        await ctx.send_message(invoices)


class StandardHandler(Executor):
    """Handles standard invoices."""
    
    @handler
    async def handle(self, invoices: list[InvoiceData], ctx: WorkflowContext[list[InvoiceData]]):
        await ctx.send_message(invoices)


class Finalizer(Executor):
    """Finalizes all invoices."""
    
    @handler
    async def finalize(self, invoices: list[InvoiceData], ctx: WorkflowContext[Never, str]):
        await ctx.yield_output("Processing complete!")


# ============================================================================
# WORKFLOW BUILDERS
# ============================================================================

def build_sequential_workflow():
    """Build a sequential workflow."""
    loader = LoadInvoices(id="loader")
    calculator = CalculateTotals(id="calculator")
    renderer = RenderInvoices(id="renderer")
    saver = SaveInvoices(id="saver")
    
    return (
        WorkflowBuilder()
        .set_start_executor(loader)
        .add_edge(loader, calculator)
        .add_edge(calculator, renderer)
        .add_edge(renderer, saver)
        .build()
    )


def build_parallel_workflow():
    """Build a parallel workflow with fan-out/fan-in."""
    dispatcher = Dispatcher(id="dispatcher")
    totals_calc = TotalsCalculator(id="totals_calculator")
    client_prep = ClientPreparer(id="client_preparer")
    merger = Merger(id="merger")
    renderer = Renderer(id="renderer")
    
    return (
        WorkflowBuilder()
        .set_start_executor(dispatcher)
        .add_edge(dispatcher, totals_calc)
        .add_edge(dispatcher, client_prep)
        .add_edge(totals_calc, merger)
        .add_edge(client_prep, merger)
        .add_edge(merger, renderer)
        .build()
    )


def build_branching_workflow():
    """Build a branching workflow with conditional routing."""
    analyzer = Analyzer(id="analyzer")
    high_value = HighValueHandler(id="high_value_handler")
    preferred = PreferredHandler(id="preferred_handler")
    standard = StandardHandler(id="standard_handler")
    finalizer = Finalizer(id="finalizer")
    
    # Condition functions
    def is_high_value(invoices: list[InvoiceData], ctx: WorkflowContext) -> bool:
        # For demo purposes, check if any invoice is high value
        config = InvoiceConfig()
        for invoice in invoices:
            totals = calculate_invoice_totals(invoice, config)
            if totals['subtotal'] >= config.high_value_threshold:
                return True
        return False
    
    def is_preferred(invoices: list[InvoiceData], ctx: WorkflowContext) -> bool:
        # For demo purposes, check if any invoice is for preferred client
        for invoice in invoices:
            if invoice.is_preferred:
                return True
        return False
    
    return (
        WorkflowBuilder()
        .set_start_executor(analyzer)
        .add_switch_case_edge_group(
            analyzer,
            [
                Case(is_high_value, high_value),
                Case(is_preferred, preferred),
                Default(standard)
            ]
        )
        .add_edge(high_value, finalizer)
        .add_edge(preferred, finalizer)
        .add_edge(standard, finalizer)
        .build()
    )


# ============================================================================
# VISUALIZATION FUNCTIONS
# ============================================================================

def visualize_workflow(workflow, title: str, pattern_type: str):
    """Visualize a workflow in multiple formats."""
    
    print(f"\n{'='*80}")
    print(f"VISUALIZATION: {title}")
    print(f"{'='*80}\n")
    
    # Generate Mermaid diagram
    print("Mermaid Diagram:")
    print("-" * 80)
    mermaid = WorkflowViz(workflow).to_mermaid()
    print(mermaid)
    print("-" * 80)
    
    # Save to files
    viz_dir = BASE_DIR / "visualizations"
    viz_dir.mkdir(exist_ok=True)
    
    filename_base = pattern_type.lower()
    
    mermaid_file = viz_dir / f"{filename_base}_workflow.mmd"
    with open(mermaid_file, 'w') as f:
        f.write(mermaid)
    print(f"\nSaved Mermaid: {mermaid_file}")
    
    # Note: DOT format may not be available in this version
    print("Note: DOT format not available in current version")
    
    print("\n" + "="*80)


def print_workflow_analysis(workflow, title: str, pattern_type: str):
    """Print analysis of workflow structure."""
    
    print(f"\nAnalysis: {title}")
    print("-" * 80)
    
    # Analyze structure based on pattern type
    if pattern_type == "sequential":
        print("Executors in workflow:")
        print("  1. loader (entry point)")
        print("  2. calculator")
        print("  3. renderer")
        print("  4. saver (exit point)")
        print("\nPattern: Linear chain (A -> B -> C -> D)")
        print("Parallelism: None")
        print("Branches: None")
        print("Use Case: Step-by-step processing where each step depends on the previous")
    
    elif pattern_type == "parallel":
        print("Executors in workflow:")
        print("  1. dispatcher (entry point)")
        print("  2. totals_calculator (parallel)")
        print("  3. client_preparer (parallel)")
        print("  4. merger (synchronization)")
        print("  5. renderer (exit point)")
        print("\nPattern: Fan-out/Fan-in")
        print("Parallelism: 2 concurrent branches")
        print("Branches: None")
        print("Use Case: Independent concurrent tasks that can run simultaneously")
    
    elif pattern_type == "branching":
        print("Executors in workflow:")
        print("  1. analyzer (entry point)")
        print("  2. high_value_handler (conditional)")
        print("  3. preferred_handler (conditional)")
        print("  4. standard_handler (default)")
        print("  5. finalizer (convergence point)")
        print("\nPattern: Switch-case with convergence")
        print("Parallelism: None")
        print("Branches: 3 conditional paths")
        print("Use Case: Conditional routing based on data or business rules")
    
    print("-" * 80)


# ============================================================================
# INTERACTIVE VISUALIZATION DEMO
# ============================================================================

async def visualize_pattern(pattern_type: str):
    """Visualize a specific workflow pattern."""
    
    if pattern_type == "sequential":
        workflow = build_sequential_workflow()
        title = "Sequential Workflow"
    elif pattern_type == "parallel":
        workflow = build_parallel_workflow()
        title = "Parallel Workflow"
    elif pattern_type == "branching":
        workflow = build_branching_workflow()
        title = "Branching Workflow"
    else:
        return
    
    visualize_workflow(workflow, title, pattern_type)
    print_workflow_analysis(workflow, title, pattern_type)
    
    wait_for_user("continue to next visualization")


async def main():
    """Run interactive visualization demo."""
    
    print("\n" + "="*80)
    print("WORKFLOW VISUALIZATION - INVOICE BUILDER")
    print("="*80)
    print("\nThis demo visualizes different workflow patterns:")
    print("  • Sequential Workflow - Linear processing")
    print("  • Parallel Workflow - Concurrent processing with fan-out/fan-in")
    print("  • Branching Workflow - Conditional routing with switch-case")
    print("\nOutput formats:")
    print("  • Mermaid (for Markdown and web rendering)")
    print("  • Note: DOT/Graphviz format not available in current version")
    print("="*80)
    
    ensure_directories(str(BASE_DIR / "visualizations"))
    
    # Get user selection
    selected_patterns = show_workflow_menu()
    
    print(f"\nSelected patterns: {', '.join(selected_patterns).title()}")
    wait_for_user("start visualization")
    
    # Visualize selected patterns
    for i, pattern in enumerate(selected_patterns, 1):
        print(f"\n\n{'█'*80}")
        print(f"█{' '*78}█")
        print(f"█{' '*25}{pattern.upper()} WORKFLOW{' '*35}█")
        print(f"█{' '*78}█")
        print(f"█{' '*20}({i} of {len(selected_patterns)}){' '*35}█")
        print(f"█{' '*78}█")
        print(f"{'█'*80}")
        
        await visualize_pattern(pattern)
    
    # Summary
    print("\n\n" + "="*80)
    print("VISUALIZATION COMPLETE")
    print("="*80)
    print("\nOutput Directory: part-3/visualizations/")
    print("\nGenerated Files:")
    
    for pattern in selected_patterns:
        print(f"  • {pattern}_workflow.mmd (Mermaid)")
    
    print("\nUsage Tips:")
    print("  • Copy .mmd files to Mermaid Live Editor (https://mermaid.live)")
    print("  • Visual diagrams help understand complex workflows")
    print("  • Great for documentation and presentations")
    
    print("\nWorkflow Pattern Summary:")
    if "sequential" in selected_patterns:
        print("  Sequential: Best for step-by-step processing")
    if "parallel" in selected_patterns:
        print("  Parallel: Best for independent concurrent tasks")
    if "branching" in selected_patterns:
        print("  Branching: Best for conditional routing based on data")
    
    print("\n" + "="*80)
    print("All selected workflow patterns visualized successfully!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())