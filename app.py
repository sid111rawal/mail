#!/usr/bin/env python3
"""
Flask web application for Interac e-Transfer
"""
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from models import Database
from email_sender import EmailSender
from datetime import datetime
import random
import string
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))  # For session management

# Initialize database
db = Database()

# Email configuration - now uses environment variables via EmailSender

def generate_reference_number() -> str:
    """Generate a random reference number."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(12))

def format_amount(amount: float) -> str:
    """Format amount as currency string."""
    return f"${amount:,.2f}"

def format_transfer_date(transfer: dict) -> str:
    """Format transfer date with time."""
    if transfer.get('completed_at'):
        try:
            dt = datetime.strptime(transfer['completed_at'], '%Y-%m-%d %H:%M:%S')
            month_names = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 
                          'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
            return f"{month_names[dt.month - 1]} {dt.day}, {dt.year} at {dt.hour}:{dt.minute:02d}"
        except:
            return transfer.get('date', 'Unknown date').upper()
    return transfer.get('date', 'Unknown date').upper()

def format_currency(amount: float) -> str:
    """Format currency with proper comma/period formatting."""
    return f"${amount:,.2f}"

@app.route('/')
def index():
    """Main banking dashboard."""
    balance = db.get_balance()
    # Get transfers from last 30 days
    transfers = db.get_transfers(limit=100, days=30)
    # Get deposits from last 30 days
    deposits = db.get_deposits(limit=100, days=30)
    
    # Format transfers
    all_transactions = []
    for transfer in transfers:
        all_transactions.append({
            'type': 'transfer',
            'date': transfer.get('completed_at') or transfer.get('created_at'),
            'formatted_date': format_transfer_date(transfer),
            'description': f"INTERAC e-Transfer To: {transfer['to_name']}",
            'category': f"Ref: {transfer['reference_number']}",
            'amount': -transfer['amount'],  # Negative for outgoing
            'formatted_amount': format_currency(transfer['amount']),
            'is_positive': False
        })
    
    # Format deposits
    for deposit in deposits:
        try:
            dt = datetime.strptime(deposit['created_at'], '%Y-%m-%d %H:%M:%S')
            month_names = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 
                          'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
            formatted_date = f"{month_names[dt.month - 1]} {dt.day}, {dt.year} at {dt.hour}:{dt.minute:02d}"
        except:
            formatted_date = deposit['created_at']
        
        all_transactions.append({
            'type': 'deposit',
            'date': deposit['created_at'],
            'formatted_date': formatted_date,
            'description': f"Deposit from {deposit['from_account']} account",
            'category': 'Deposit',
            'amount': deposit['amount'],
            'formatted_amount': format_currency(deposit['amount']),
            'is_positive': True
        })
    
    # Sort by date (most recent first)
    all_transactions.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate running balances (starting from initial balance)
    starting_balance = 5299.34
    running_balance = starting_balance
    
    # Calculate balance backwards from current
    # First, sum all transactions
    total_outgoing = sum(abs(t['amount']) for t in all_transactions if not t['is_positive'])
    total_deposits = sum(t['amount'] for t in all_transactions if t['is_positive'])
    running_balance = starting_balance - total_outgoing + total_deposits
    
    # Now calculate balance after each transaction (going backwards in time)
    formatted_transactions = []
    for transaction in all_transactions:
        if transaction['type'] == 'transfer':
            running_balance += abs(transaction['amount'])  # Add back for transfers
        elif transaction['type'] == 'deposit':
            running_balance -= transaction['amount']  # Subtract to get balance before deposit
        transaction['balance_after'] = running_balance
        transaction['formatted_balance'] = format_currency(running_balance)
        formatted_transactions.append(transaction)
    
    return render_template('banking_dashboard.html', 
                         balance=balance, 
                         formatted_balance=format_currency(balance),
                         transactions=formatted_transactions)

@app.route('/interac/select-contact')
def select_contact():
    """Step 1: Select contact to send transfer to."""
    search = request.args.get('search', '')
    contacts = db.get_contacts(search)
    balance = db.get_balance()
    return render_template('select_contact.html', 
                         contacts=contacts, 
                         search=search,
                         balance=balance,
                         formatted_balance=format_currency(balance))

@app.route('/interac/enter-details')
def enter_details():
    """Step 2: Enter transfer details."""
    contact_id = request.args.get('contact_id')
    if not contact_id:
        return redirect(url_for('select_contact'))
    
    contact = db.get_contact(int(contact_id))
    if not contact:
        return redirect(url_for('select_contact'))
    
    # Store contact in session
    session['selected_contact'] = {
        'id': contact['id'],
        'name': contact['name'],
        'email': contact['email']
    }
    
    # Get today's date in YYYY-MM-DD format
    date_today = datetime.now().strftime('%Y-%m-%d')
    
    # Get current balance
    balance = db.get_balance()
    
    return render_template('enter_details.html', 
                         contact=contact, 
                         date_today=date_today,
                         balance=balance,
                         formatted_balance=format_currency(balance))

@app.route('/interac/review')
def review_transfer():
    """Step 3: Review transfer before sending."""
    # Get data from session or query params
    contact = session.get('selected_contact')
    if not contact:
        return redirect(url_for('select_contact'))
    
    amount = request.args.get('amount')
    date = request.args.get('date')
    message = request.args.get('message', '')
    
    if not amount or not date:
        return redirect(url_for('enter_details', contact_id=contact['id']))
    
    # Store transfer details in session
    session['transfer_details'] = {
        'amount': float(amount),
        'date': date,
        'message': message
    }
    
    # Get current balance
    balance = db.get_balance()
    
    return render_template('review_transfer.html', 
                         contact=contact,
                         amount=format_amount(float(amount)),
                         date=date,
                         message=message,
                         balance=balance,
                         formatted_balance=format_currency(balance))

@app.route('/api/create-transfer', methods=['POST'])
def create_transfer():
    """API endpoint to create and process transfer."""
    data = request.json
    contact = session.get('selected_contact')
    transfer_details = session.get('transfer_details')
    
    if not contact or not transfer_details:
        return jsonify({'error': 'Missing transfer data'}), 400
    
    # Generate reference number
    reference_number = generate_reference_number()
    
    # Create transfer record
    transfer_id = db.create_transfer(
        from_account="Chequing *** 3982",
        to_email=contact['email'],
        to_name=contact['name'],
        amount=transfer_details['amount'],
        date=transfer_details['date'],
        message=transfer_details.get('message', ''),
        reference_number=reference_number
    )
    
    # Mark as completed (simulating successful transfer)
    db.update_transfer_status(transfer_id, 'completed')
    
    # Update balance (subtract transfer amount)
    db.update_balance(transfer_details['amount'])
    
    # Get the transfer record
    transfer = db.get_transfer(transfer_id)
    
    # Send email notification
    try:
        send_transfer_email(transfer)
        print(f"✓ Interac e-Transfer email sent to {contact['email']}")
    except Exception as e:
        print(f"❌ Error sending email: {e}")
        # Continue even if email fails
    
    # Store transfer ID in session for success page
    session['last_transfer_id'] = transfer_id
    
    return jsonify({
        'success': True,
        'transfer_id': transfer_id,
        'reference_number': reference_number,
        'new_balance': db.get_balance()
    })

@app.route('/interac/success')
def transfer_success():
    """Step 4: Transfer success page."""
    transfer_id = session.get('last_transfer_id')
    if not transfer_id:
        return redirect(url_for('index'))
    
    transfer = db.get_transfer(transfer_id)
    if not transfer:
        return redirect(url_for('index'))
    
    # Clear session data
    session.pop('selected_contact', None)
    session.pop('transfer_details', None)
    session.pop('last_transfer_id', None)
    
    return render_template('transfer_success.html', transfer=transfer)

@app.route('/api/contacts', methods=['GET'])
def get_contacts_api():
    """API endpoint to get contacts."""
    search = request.args.get('search', '')
    contacts = db.get_contacts(search)
    return jsonify(contacts)

@app.route('/add-contact')
def add_contact_page():
    """Page to add a new contact."""
    return render_template('add_contact.html')

@app.route('/api/contacts', methods=['POST'])
def add_contact_api():
    """API endpoint to add a new contact."""
    data = request.json
    try:
        contact_id = db.add_contact(data['name'], data['email'])
        return jsonify({'success': True, 'contact_id': contact_id})
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@app.route('/add-money')
def add_money_page():
    """Page to add money to account."""
    balance = db.get_balance()
    return render_template('add_money.html', formatted_balance=format_currency(balance))

@app.route('/api/add-money', methods=['POST'])
def add_money_api():
    """API endpoint to add money to account."""
    data = request.json
    amount = float(data.get('amount', 0))
    
    if amount <= 0:
        return jsonify({'error': 'Amount must be greater than 0'}), 400
    
    try:
        # Create deposit record
        deposit_id = db.add_deposit(amount)
        new_balance = db.get_balance()
        return jsonify({
            'success': True,
            'deposit_id': deposit_id,
            'new_balance': new_balance,
            'formatted_balance': format_currency(new_balance)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def send_transfer_email(transfer: dict):
    """Send Interac e-Transfer notification email."""
    sender = EmailSender()  # Uses environment variables
    
    # Load and customize template
    template_path = "interac_template.html"
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        print(f"Template {template_path} not found")
        return
    
    # Customize template
    email_data = {
        'recipient_name': transfer['to_name'].upper(),
        'amount': format_amount(transfer['amount']),
        'bank_name': 'Scotiabank',  # Default, can be customized
        'account_number': '2242',  # Default, can be customized
        'transfer_date': transfer['date'],
        'reference_number': transfer['reference_number'],
        'sender_name': '12012442438 ONTARIO INC.'
    }
    
    # Replace placeholders
    html_body = template
    for placeholder, value in email_data.items():
        html_body = html_body.replace(f'{{{placeholder}}}', str(value))
    
    # Plain text fallback
    body = f"""Hi {email_data['recipient_name']},

Your funds have been automatically deposited into your account at {email_data['bank_name']}.

Amount: {email_data['amount']}
Date: {email_data['transfer_date']}
Reference Number: {email_data['reference_number']}
Sent From: {email_data['sender_name']}

This is an automated notification.
"""
    
    # Subject line
    subject = f"Interac e-Transfer: You've received {email_data['amount']} from {email_data['sender_name']} and it has been automatically deposited."
    
    # From address
    from_email = f"{email_data['sender_name']} <notify@payments.interac.ca>"
    
    # Recipient
    recipient = {
        'name': transfer['to_name'],
        'email': transfer['to_email'],
        'company': 'Personal'
    }
    
    # Send email
    if sender.connect_smtp():
        sender.send_single_email(recipient, subject, body, html_body, None, from_email)
        sender.disconnect_smtp()
        print(f"Email sent to {transfer['to_email']}")

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug, host='0.0.0.0', port=port)

