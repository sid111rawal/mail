#!/usr/bin/env python3
"""
Test script for Outlook SMTP
"""
import os
from email_sender import EmailSender
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_outlook_smtp():
    """Test sending email via Outlook SMTP."""
    
    # Set Outlook SMTP environment variables (or use .env file)
    os.environ['SMTP_SERVER'] = 'smtp-mail.outlook.com'
    os.environ['SMTP_PORT'] = '587'
    os.environ['SMTP_USE_TLS'] = 'true'
    
    # Get credentials from environment or prompt
    sender_email = os.getenv('SMTP_SENDER_EMAIL') or input("Enter your Outlook email: ")
    sender_password = os.getenv('SMTP_SENDER_PASSWORD') or input("Enter your Outlook password: ")
    recipient_email = os.getenv('TEST_RECIPIENT_EMAIL', 'sidrawal1200@gmail.com')
    
    # Set environment variables
    os.environ['SMTP_SENDER_EMAIL'] = sender_email
    os.environ['SMTP_SENDER_PASSWORD'] = sender_password
    os.environ['SMTP_SENDER_NAME'] = 'Interac e-Transfer'
    
    print("\n" + "="*50)
    print("Testing Outlook SMTP Connection...")
    print("="*50)
    print(f"SMTP Server: smtp-mail.outlook.com")
    print(f"Port: 587")
    print(f"From: {sender_email}")
    print(f"To: {recipient_email}")
    print("="*50 + "\n")
    
    # Initialize email sender (will use environment variables)
    try:
        sender = EmailSender()
        
        # Test connection
        if sender.connect_smtp():
            print("✓ Successfully connected to Outlook SMTP server!")
            
            # Create test email
            recipient = {
                'name': 'Test Recipient',
                'email': recipient_email,
                'company': 'Test'
            }
            
            subject = "Test Email from Outlook SMTP"
            body = "This is a test email sent via Outlook SMTP. If you receive this, the configuration is working!"
            html_body = f"""
            <html>
                <body>
                    <h2>Test Email</h2>
                    <p>This is a test email sent via Outlook SMTP.</p>
                    <p>If you receive this, the configuration is working!</p>
                </body>
            </html>
            """
            
            # Send email
            print(f"\n📧 Sending test email to {recipient_email}...")
            success = sender.send_single_email(recipient, subject, body, html_body)
            
            if success:
                print("✓ Email sent successfully!")
                print(f"✓ Check {recipient_email} inbox")
            else:
                print("❌ Failed to send email")
            
            sender.disconnect_smtp()
            print("\n✓ Disconnected from SMTP server")
            
        else:
            print("❌ Failed to connect to Outlook SMTP server")
            print("\n" + "="*50)
            print("Microsoft has disabled basic authentication.")
            print("You need to use an App Password instead.")
            print("="*50)
            print("\nSteps to create App Password:")
            print("1. Go to: https://account.microsoft.com/security")
            print("2. Click 'Advanced security options'")
            print("3. Under 'App passwords', click 'Create a new app password'")
            print("4. Name it (e.g., 'SMTP Email') and click 'Generate'")
            print("5. Copy the 16-character password")
            print("6. Use that password instead of your regular password")
            print("\nThen run this script again with the App Password.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify your Outlook credentials")
        print("2. Check if 2FA requires an App Password")
        print("3. Ensure SMTP access is enabled for your account")

if __name__ == '__main__':
    test_outlook_smtp()

