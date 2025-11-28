"""
Quick test to send actual email via AWS SES
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

def send_test_email():
    """Send a test email"""
    from app.services.email_service import email_service
    from app.core.config import settings

    # Send to the verified sender email (in sandbox mode, sender must be verified)
    recipient = settings.SES_SENDER_EMAIL

    print(f"📧 Sending test email to: {recipient}")

    success = email_service.send_notification_email(
        to_emails=[recipient],
        subject="[TEST] Sales Checklist - AWS SES Verification",
        message="Congratulations! AWS SES email service is working correctly. This test email confirms your backend can send transactional emails.",
        user_name="Product Team"
    )

    if success:
        print("✅ EMAIL SENT SUCCESSFULLY!")
        print(f"   Check inbox: {recipient}")
        return True
    else:
        print("❌ EMAIL SEND FAILED")
        print("   Check AWS SES console for errors")
        return False

if __name__ == "__main__":
    result = send_test_email()
    sys.exit(0 if result else 1)
