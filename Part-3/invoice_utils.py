"""
Shared utilities for Invoice Builder Workflows
Provides reusable functions for all workflow demos.
"""

import csv
import os
import shutil
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import List


@dataclass
class InvoiceData:
    """Represents a single invoice record."""
    invoice_id: str
    client_name: str
    client_email: str
    is_preferred: bool
    item_description: str
    quantity: int
    unit_price: float
    date: str
    
    @property
    def subtotal(self) -> float:
        """Calculate subtotal (quantity * unit_price)."""
        return self.quantity * self.unit_price


class InvoiceConfig:
    """Configuration loaded from environment variables."""
    
    def __init__(self):
        self.tax_rate = float(os.getenv("INVOICE_TAX_RATE", "0.10"))
        self.high_value_threshold = float(os.getenv("INVOICE_HIGH_VALUE_THRESHOLD", "5000.00"))
        self.high_value_discount = float(os.getenv("INVOICE_HIGH_VALUE_DISCOUNT", "0.05"))
        self.preferred_client_discount = float(os.getenv("INVOICE_PREFERRED_DISCOUNT", "0.03"))
        self.company_name = os.getenv("INVOICE_COMPANY_NAME", "TechServices Inc.")
        self.company_address = os.getenv("INVOICE_COMPANY_ADDRESS", "123 Business St, Tech City, TC 12345")
        
    def __repr__(self):
        return (f"InvoiceConfig(tax={self.tax_rate*100}%, "
                f"high_value_threshold=${self.high_value_threshold}, "
                f"high_value_discount={self.high_value_discount*100}%, "
                f"preferred_discount={self.preferred_client_discount*100}%)")


def read_invoices_csv(csv_path: str) -> List[InvoiceData]:
    """Read invoices from CSV file."""
    invoices = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            invoice = InvoiceData(
                invoice_id=row['invoice_id'],
                client_name=row['client_name'],
                client_email=row['client_email'],
                is_preferred=row['is_preferred'].lower() == 'true',
                item_description=row['item_description'],
                quantity=int(row['quantity']),
                unit_price=float(row['unit_price']),
                date=row['date']
            )
            invoices.append(invoice)
    
    return invoices


def calculate_invoice_totals(invoice: InvoiceData, config: InvoiceConfig) -> dict:
    """Calculate all invoice amounts including discounts and taxes."""
    subtotal = invoice.subtotal
    
    # Calculate discounts
    high_value_discount = 0.0
    if subtotal >= config.high_value_threshold:
        high_value_discount = subtotal * config.high_value_discount
    
    preferred_discount = 0.0
    if invoice.is_preferred:
        preferred_discount = subtotal * config.preferred_client_discount
    
    total_discount = high_value_discount + preferred_discount
    amount_after_discount = subtotal - total_discount
    
    # Calculate tax
    tax = amount_after_discount * config.tax_rate
    total = amount_after_discount + tax
    
    return {
        'subtotal': subtotal,
        'high_value_discount': high_value_discount,
        'preferred_discount': preferred_discount,
        'total_discount': total_discount,
        'amount_after_discount': amount_after_discount,
        'tax': tax,
        'total': total
    }


def render_invoice_text(invoice: InvoiceData, totals: dict, config: InvoiceConfig) -> str:
    """Render invoice as formatted text."""
    
    lines = []
    lines.append("=" * 80)
    lines.append(f"{config.company_name}".center(80))
    lines.append(f"{config.company_address}".center(80))
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"INVOICE: {invoice.invoice_id}")
    lines.append(f"Date: {invoice.date}")
    lines.append("")
    lines.append(f"Bill To:")
    lines.append(f"  {invoice.client_name}")
    lines.append(f"  {invoice.client_email}")
    if invoice.is_preferred:
        lines.append(f"  ⭐ PREFERRED CLIENT")
    lines.append("")
    lines.append("-" * 80)
    lines.append(f"{'DESCRIPTION':<40} {'QTY':<10} {'PRICE':<15} {'AMOUNT':>15}")
    lines.append("-" * 80)
    lines.append(f"{invoice.item_description:<40} {invoice.quantity:<10} "
                f"${invoice.unit_price:<14.2f} ${totals['subtotal']:>14.2f}")
    lines.append("")
    lines.append(f"{'Subtotal:':<65} ${totals['subtotal']:>14.2f}")
    
    if totals['high_value_discount'] > 0:
        lines.append(f"{'High Value Discount (5%):':<65} -${totals['high_value_discount']:>13.2f}")
    
    if totals['preferred_discount'] > 0:
        lines.append(f"{'Preferred Client Discount (3%):':<65} -${totals['preferred_discount']:>13.2f}")
    
    if totals['total_discount'] > 0:
        lines.append(f"{'Amount After Discount:':<65} ${totals['amount_after_discount']:>14.2f}")
    
    lines.append(f"{'Tax (10%):':<65} ${totals['tax']:>14.2f}")
    lines.append("-" * 80)
    lines.append(f"{'TOTAL DUE:':<65} ${totals['total']:>14.2f}")
    lines.append("=" * 80)
    lines.append("")
    lines.append("Thank you for your business!")
    lines.append("")
    
    return "\n".join(lines)


def save_invoice_file(invoice_id: str, content: str, output_dir: str) -> str:
    """Save invoice to output directory."""
    filename = f"{invoice_id}.txt"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return filepath


def archive_old_invoice(invoice_id: str, output_dir: str, archive_dir: str) -> bool:
    """Archive existing invoice file if it exists."""
    filename = f"{invoice_id}.txt"
    output_path = os.path.join(output_dir, filename)
    
    if os.path.exists(output_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_filename = f"{invoice_id}_{timestamp}.txt"
        archive_path = os.path.join(archive_dir, archive_filename)
        
        shutil.move(output_path, archive_path)
        return True
    
    return False


def log_action(message: str, log_dir: str, log_file: str = "invoice_workflow.log"):
    """Log action to log file."""
    log_path = os.path.join(log_dir, log_file)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(log_path, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")


def ensure_directories(*dirs):
    """Ensure all required directories exist."""
    for directory in dirs:
        Path(directory).mkdir(parents=True, exist_ok=True)


def print_step(step_number: int, step_name: str, details: str = ""):
    """Print formatted step information."""
    print(f"\n{'='*80}")
    print(f"STEP {step_number}: {step_name}")
    print(f"{'='*80}")
    if details:
        print(details)


def print_invoice_summary(invoice: InvoiceData, totals: dict):
    """Print a summary of the invoice."""
    print(f"\n📄 Invoice: {invoice.invoice_id}")
    print(f"   Client: {invoice.client_name} {'⭐' if invoice.is_preferred else ''}")
    print(f"   Item: {invoice.item_description}")
    print(f"   Quantity: {invoice.quantity} x ${invoice.unit_price:.2f}")
    print(f"   Subtotal: ${totals['subtotal']:.2f}")
    if totals['total_discount'] > 0:
        print(f"   Discount: -${totals['total_discount']:.2f}")
    print(f"   Tax: ${totals['tax']:.2f}")
    print(f"   💰 TOTAL: ${totals['total']:.2f}")
