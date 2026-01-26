#!/usr/bin/env python3
"""
EQ Bank Statement PDF Generator

Generates bank statements from JSON transaction data using WeasyPrint.
Uses fixed positioning for reliable PDF output.
"""

import json
import math
import os
import sys
from pathlib import Path

# Install dependencies if needed
try:
    from weasyprint import HTML, CSS
    from jinja2 import Environment, FileSystemLoader
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "weasyprint", "jinja2"])
    from weasyprint import HTML, CSS
    from jinja2 import Environment, FileSystemLoader


# Configuration - Transactions per page (tuned for A4 with fixed layout)
TRANSACTIONS_FIRST_PAGE = 7   # First page has less space due to summary section
TRANSACTIONS_OTHER_PAGES = 12  # Subsequent pages have more space


def load_json_data(json_path: str) -> dict:
    """Load transaction data from JSON file."""
    with open(json_path, 'r') as f:
        return json.load(f)


def format_currency(value):
    """Format a number as currency with commas."""
    if value is None:
        return ""
    return "{:,.2f}".format(float(value))


def paginate_transactions(transactions: list) -> list:
    """
    Split transactions into pages, returning a list of page objects.
    Each page object contains: page_num, is_first_page, transactions
    """
    pages = []
    
    if not transactions:
        # Return empty first page if no transactions
        return [{
            'page_num': 1,
            'is_first_page': True,
            'transactions': []
        }]
    
    # First page
    first_page_txns = transactions[:TRANSACTIONS_FIRST_PAGE]
    pages.append({
        'page_num': 1,
        'is_first_page': True,
        'transactions': first_page_txns
    })
    
    # Remaining transactions
    remaining = transactions[TRANSACTIONS_FIRST_PAGE:]
    page_num = 2
    
    while remaining:
        page_txns = remaining[:TRANSACTIONS_OTHER_PAGES]
        pages.append({
            'page_num': page_num,
            'is_first_page': False,
            'transactions': page_txns
        })
        remaining = remaining[TRANSACTIONS_OTHER_PAGES:]
        page_num += 1
    
    return pages


def format_transaction_amounts(transactions: list) -> list:
    """Format all transaction amounts as currency strings."""
    formatted = []
    for txn in transactions:
        formatted_txn = txn.copy()
        if 'withdrawal' in formatted_txn and formatted_txn['withdrawal']:
            formatted_txn['withdrawal'] = format_currency(formatted_txn['withdrawal'])
        if 'deposit' in formatted_txn and formatted_txn['deposit']:
            formatted_txn['deposit'] = format_currency(formatted_txn['deposit'])
        if 'balance' in formatted_txn:
            formatted_txn['balance'] = format_currency(formatted_txn['balance'])
        formatted.append(formatted_txn)
    return formatted


def format_summary(summary: dict) -> dict:
    """Format summary amounts as currency strings."""
    return {
        'opening_balance': format_currency(summary.get('opening_balance', 0)),
        'total_deposits': format_currency(summary.get('total_deposits', 0)),
        'total_withdrawals': format_currency(summary.get('total_withdrawals', 0)),
        'closing_balance': format_currency(summary.get('closing_balance', 0)),
        'interest_earned': format_currency(summary.get('interest_earned', 0))
    }


def render_html(data: dict, template_dir: str) -> str:
    """Render the HTML template with transaction data."""
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template('statement_template.html')
    
    # Format transactions
    transactions = data.get('transactions', [])
    formatted_txns = format_transaction_amounts(transactions)
    
    # Paginate transactions
    pages = paginate_transactions(formatted_txns)
    total_pages = len(pages)
    
    # Format summary
    formatted_summary = format_summary(data.get('summary', {}))
    
    # Extract year from date_range_end for footer (e.g., "July 31, 2025" -> "2025")
    date_range_end = data.get('date_range_end', '')
    footer_year = date_range_end.split()[-1] if date_range_end else '2026'
    
    return template.render(
        statement_month=data.get('statement_month', ''),
        account_type=data.get('account_type', ''),
        account_number=data.get('account_number', ''),
        date_range_start=data.get('date_range_start', ''),
        date_range_end=date_range_end,
        customer=data.get('customer', {}),
        summary=formatted_summary,
        contact=data.get('contact', {}),
        pages=pages,
        total_pages=total_pages,
        footer_year=footer_year
    )


def generate_pdf(html_content: str, output_path: str, base_url: str):
    """Generate PDF from HTML content using WeasyPrint."""
    html = HTML(string=html_content, base_url=base_url)
    html.write_pdf(output_path)
    print(f"✅ PDF generated successfully: {output_path}")


def main():
    # Determine paths
    script_dir = Path(__file__).parent.resolve()
    
    # Default paths
    data_file = script_dir / "sample_data.json"
    output_dir = script_dir / "output"
    output_file = output_dir / "statement.pdf"
    
    # Allow command-line override
    if len(sys.argv) > 1:
        data_file = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_file = Path(sys.argv[2])
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    print(f"📄 Loading data from: {data_file}")
    print(f"📁 Output will be saved to: {output_file}")
    
    # Load data
    data = load_json_data(str(data_file))
    print(f"📊 Found {len(data.get('transactions', []))} transactions")
    
    # Render HTML
    html_content = render_html(data, str(script_dir))
    
    # Save HTML preview for debugging
    preview_file = output_dir / "statement_preview.html"
    with open(preview_file, 'w') as f:
        f.write(html_content)
    print(f"🔍 HTML preview saved to: {preview_file}")
    
    # Generate PDF
    generate_pdf(html_content, str(output_file), str(script_dir))
    
    print("\n✨ Done! You can now view your statement.")


if __name__ == "__main__":
    main()
