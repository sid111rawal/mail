#!/usr/bin/env python3
"""
Email Sender Program
Sends emails to clients using Gmail or custom domain SMTP settings.
"""

import smtplib
import ssl
import json
import csv
import logging
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import time
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('email_log.txt'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EmailSender:
    """Email sender class that supports Gmail and custom domain SMTP."""
    
    def __init__(self, config_file: Optional[str] = None):
        """Initialize email sender with configuration from environment variables or JSON file."""
        self.config = self.load_config(config_file)
        self.smtp_server = None
        
    def load_config(self, config_file: Optional[str] = None) -> Dict:
        """Load email configuration from environment variables or JSON file."""
        # Try environment variables first (preferred for production)
        sender_email = os.getenv('SMTP_SENDER_EMAIL')
        sender_password = os.getenv('SMTP_SENDER_PASSWORD')
        sender_name = os.getenv('SMTP_SENDER_NAME', 'Interac e-Transfer')
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        
        if sender_email and sender_password:
            # Use environment variables
            return {
                'sender': {
                    'name': sender_name,
                    'email': sender_email,
                    'password': sender_password
                },
                'smtp': {
                    'server': smtp_server,
                    'port': smtp_port,
                    'use_tls': smtp_use_tls
                },
                'settings': {
                    'batch_size': int(os.getenv('SMTP_BATCH_SIZE', '50')),
                    'delay_between_emails': int(os.getenv('SMTP_DELAY', '1')),
                    'max_retries': int(os.getenv('SMTP_MAX_RETRIES', '3'))
                }
            }
        
        # Fallback to JSON file (for local development)
        if config_file is None:
            config_file = "email_config.json"
        
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {config_file} not found and environment variables not set!")
            raise ValueError("Email configuration not found. Set SMTP_SENDER_EMAIL and SMTP_SENDER_PASSWORD environment variables or provide email_config.json")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in {config_file}")
            raise
    
    def connect_smtp(self) -> bool:
        """Connect to SMTP server."""
        try:
            # Create SMTP connection with SSL
            context = ssl.create_default_context()
            
            if self.config['smtp']['use_tls']:
                self.smtp_server = smtplib.SMTP(
                    self.config['smtp']['server'], 
                    self.config['smtp']['port']
                )
                self.smtp_server.starttls(context=context)
            else:
                self.smtp_server = smtplib.SMTP_SSL(
                    self.config['smtp']['server'], 
                    self.config['smtp']['port'],
                    context=context
                )
            
            # Login
            self.smtp_server.login(
                self.config['sender']['email'], 
                self.config['sender']['password']
            )
            logger.info("Successfully connected to SMTP server")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {e}")
            return False
    
    def disconnect_smtp(self):
        """Disconnect from SMTP server."""
        if self.smtp_server:
            self.smtp_server.quit()
            logger.info("Disconnected from SMTP server")
    
    def create_message(self, recipient: Dict, subject: str, body: str, 
                      body_html: Optional[str] = None, attachments: List[str] = None,
                      from_email: Optional[str] = None) -> MIMEMultipart:
        """Create email message."""
        message = MIMEMultipart("alternative")
        if from_email:
            message["From"] = from_email
        else:
            message["From"] = f"{self.config['sender']['name']} <{self.config['sender']['email']}>"
        message["To"] = recipient['email']
        message["Subject"] = subject
        
        # Add plain text part
        text_part = MIMEText(body, "plain")
        message.attach(text_part)
        
        # Add HTML part if provided
        if body_html:
            html_part = MIMEText(body_html, "html")
            message.attach(html_part)
        
        # Add attachments if provided
        if attachments:
            for file_path in attachments:
                if Path(file_path).exists():
                    with open(file_path, "rb") as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                    
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {Path(file_path).name}'
                    )
                    message.attach(part)
        
        return message
    
    def personalize_content(self, content: str, recipient: Dict) -> str:
        """Personalize email content with recipient data."""
        replacements = {
            '{name}': recipient.get('name', 'Valued Customer'),
            '{first_name}': recipient.get('name', 'Valued Customer').split()[0],
            '{email}': recipient.get('email', ''),
            '{company}': recipient.get('company', ''),
            '{date}': datetime.now().strftime('%B %d, %Y'),
            '{sender_name}': self.config['sender']['name']
        }
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value)
        
        return content
    
    def generate_random_subject(self) -> str:
        """Generate a random subject line."""
        subjects = [
            "Important Update from {sender_name}",
            "Exciting News for You!",
            "Don't Miss Out - Special Offer Inside",
            "Your Weekly Update from {sender_name}",
            "Thank You for Being Our Valued Customer",
            "New Features and Updates Available",
            "Monthly Newsletter - {date}",
            "Exclusive Offer Just for You",
            "Important Information Regarding Your Account",
            "Stay Connected with {sender_name}"
        ]
        
        subject = random.choice(subjects)
        return subject.replace('{sender_name}', self.config['sender']['name']).replace('{date}', datetime.now().strftime('%B %Y'))
    
    def load_recipients(self, file_path: str) -> List[Dict]:
        """Load recipients from CSV file."""
        recipients = []
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    recipients.append(row)
            logger.info(f"Loaded {len(recipients)} recipients from {file_path}")
        except Exception as e:
            logger.error(f"Error loading recipients: {e}")
        
        return recipients
    
    def send_single_email(self, recipient: Dict, subject: str, body: str, 
                         body_html: Optional[str] = None, attachments: List[str] = None,
                         from_email: Optional[str] = None) -> bool:
        """Send a single email."""
        try:
            # Personalize content
            personalized_subject = self.personalize_content(subject, recipient)
            personalized_body = self.personalize_content(body, recipient)
            personalized_body_html = self.personalize_content(body_html, recipient) if body_html else None
            
            # Create message
            message = self.create_message(
                recipient, 
                personalized_subject, 
                personalized_body,
                personalized_body_html,
                attachments,
                from_email
            )
            
            # Send email
            self.smtp_server.send_message(message)
            logger.info(f"Email sent successfully to {recipient['email']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient['email']}: {e}")
            return False
    
    def send_bulk_emails(self, recipients: List[Dict], subject: str = None, 
                        body: str = None, body_html: str = None, 
                        attachments: List[str] = None, delay: int = 1) -> Dict:
        """Send emails to multiple recipients."""
        if not subject:
            subject = self.generate_random_subject()
        
        if not body:
            body = self.get_default_body()
        
        results = {"sent": 0, "failed": 0, "errors": []}
        
        if not self.connect_smtp():
            return results
        
        try:
            for i, recipient in enumerate(recipients):
                logger.info(f"Sending email {i+1}/{len(recipients)} to {recipient['email']}")
                
                if self.send_single_email(recipient, subject, body, body_html, attachments):
                    results["sent"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(recipient['email'])
                
                # Add delay between emails to avoid rate limiting
                if delay > 0 and i < len(recipients) - 1:
                    time.sleep(delay)
        
        finally:
            self.disconnect_smtp()
        
        logger.info(f"Bulk email completed: {results['sent']} sent, {results['failed']} failed")
        return results
    
    def get_default_body(self) -> str:
        """Get default email body template."""
        return """Dear {name},

I hope this email finds you well. I wanted to reach out to share some exciting updates and opportunities with you.

As a valued member of our community, we're committed to providing you with the best possible experience and keeping you informed about important developments.

If you have any questions or would like to learn more, please don't hesitate to reach out to us.

Best regards,
{sender_name}

---
This email was sent to {email}. If you no longer wish to receive these emails, please reply with "UNSUBSCRIBE" in the subject line.
"""
    
    def get_default_html_body(self) -> str:
        """Get default HTML email body template."""
        return """
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2c3e50;">Hello {name}!</h2>
                
                <p>I hope this email finds you well. I wanted to reach out to share some exciting updates and opportunities with you.</p>
                
                <p>As a valued member of our community, we're committed to providing you with the best possible experience and keeping you informed about important developments.</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>What's New:</strong></p>
                    <ul>
                        <li>Enhanced features and improvements</li>
                        <li>Better customer support</li>
                        <li>Exclusive offers and updates</li>
                    </ul>
                </div>
                
                <p>If you have any questions or would like to learn more, please don't hesitate to reach out to us.</p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>{sender_name}</strong>
                </p>
                
                <hr style="margin-top: 30px; border: none; border-top: 1px solid #ddd;">
                <p style="font-size: 12px; color: #666;">
                    This email was sent to {email}. If you no longer wish to receive these emails, 
                    please reply with "UNSUBSCRIBE" in the subject line.
                </p>
            </div>
        </body>
        </html>
        """

def main():
    """Main function to demonstrate email sending."""
    try:
        # Initialize email sender
        sender = EmailSender()
        
        # Option 1: Send to a single recipient
        single_recipient = {
            'name': 'John Doe',
            'email': 'johndoe@example.com',
            'company': 'Example Corp'
        }
        
        # Option 2: Load recipients from CSV
        # recipients = sender.load_recipients('clients.csv')
        
        # Send emails
        print("Choose an option:")
        print("1. Send single test email")
        print("2. Send bulk emails from CSV")
        print("3. Generate random subject and send test email")
        
        choice = input("Enter your choice (1-3): ").strip()
        
        if choice == "1":
            # Send single email with custom content
            subject = "Test Email from EmailTestTools"
            body = sender.get_default_body()
            html_body = sender.get_default_html_body()
            
            if sender.connect_smtp():
                success = sender.send_single_email(single_recipient, subject, body, html_body)
                sender.disconnect_smtp()
                if success:
                    print("✅ Email sent successfully!")
                else:
                    print("❌ Failed to send email")
        
        elif choice == "2":
            csv_file = input("Enter CSV file path (default: clients.csv): ").strip() or "clients.csv"
            if Path(csv_file).exists():
                recipients = sender.load_recipients(csv_file)
                if recipients:
                    subject = input("Enter subject (press Enter for random): ").strip()
                    if not subject:
                        subject = sender.generate_random_subject()
                    
                    body = sender.get_default_body()
                    html_body = sender.get_default_html_body()
                    
                    results = sender.send_bulk_emails(recipients, subject, body, html_body)
                    print(f"✅ Sent: {results['sent']}, ❌ Failed: {results['failed']}")
                else:
                    print("No recipients found in CSV file")
            else:
                print(f"CSV file '{csv_file}' not found")
        
        elif choice == "3":
            subject = sender.generate_random_subject()
            print(f"Generated subject: {subject}")
            body = sender.get_default_body()
            html_body = sender.get_default_html_body()
            
            if sender.connect_smtp():
                success = sender.send_single_email(single_recipient, subject, body, html_body)
                sender.disconnect_smtp()
                if success:
                    print("✅ Email sent successfully!")
                else:
                    print("❌ Failed to send email")
        
        else:
            print("Invalid choice")
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Email sending interrupted by user")
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
