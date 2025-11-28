"""
Test script for AWS SES Email Service
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

def test_ses():
    """Test AWS SES email service"""
    from app.services.email_service import email_service
    from app.core.config import settings

    print("=== AWS SES EMAIL SERVICE TEST ===\n")

    # Test 1: Check SES client initialization
    print("1. Testing SES Client Initialization...")
    if email_service.ses_client:
        print("   ✅ SES client initialized successfully")
    else:
        print("   ❌ SES client NOT initialized")
        print("   Check your AWS credentials in .env file")
        return False

    # Test 2: Check SES region
    print(f"\n2. SES Region: {settings.SES_REGION}")

    # Test 3: Check sender email
    print(f"\n3. Sender Email: {settings.SES_SENDER_EMAIL}")
    if not settings.SES_SENDER_EMAIL:
        print("   ⚠️  Warning: SES_SENDER_EMAIL not configured")

    # Test 4: Get send quota (tests AWS credentials)
    print("\n4. Testing AWS Credentials (Get Send Quota)...")
    quota = email_service.get_send_quota()

    if "error" in quota:
        print(f"   ❌ Failed to get quota: {quota['error']}")
        return False
    else:
        print(f"   ✅ AWS SES Credentials Working!")
        print(f"   📊 Max 24-hour send: {quota['max_24_hour_send']}")
        print(f"   📊 Max send rate: {quota['max_send_rate']}/sec")
        print(f"   📊 Sent last 24 hours: {quota['sent_last_24_hours']}")

    # Test 5: Send test email (optional - requires verified sender)
    print("\n5. Testing Email Send...")
    test_recipient = os.getenv("TEST_EMAIL_RECIPIENT")

    if not test_recipient:
        print("   ⚠️  TEST_EMAIL_RECIPIENT not set in .env")
        print("   Skipping actual email send test")
        print("   Add TEST_EMAIL_RECIPIENT=your_email@example.com to test")
    else:
        print(f"   Sending test email to: {test_recipient}")

        success = email_service.send_notification_email(
            to_emails=[test_recipient],
            subject="[TEST] Sales Checklist - SES Test Email",
            message="This is a test email from the Sales Checklist backend API. If you received this email, AWS SES is working correctly!",
            user_name="Test User"
        )

        if success:
            print("   ✅ Test email sent successfully!")
        else:
            print("   ❌ Failed to send test email")
            print("   Note: Sender email must be verified in AWS SES")
            return False

    print("\n=== AWS SES TEST COMPLETED ===")
    return True


def test_email_templates():
    """Test email template rendering"""
    from app.services.email_service import email_service
    from app.core.config import settings

    print("\n=== EMAIL TEMPLATE TEST ===\n")

    templates = ['email_verification', 'password_reset', 'welcome']

    for template_name in templates:
        try:
            template = email_service.env.get_template(template_name)
            # Test rendering with sample data
            html = template.render(
                user_name="Test User",
                user_email="test@example.com",
                verification_url="https://example.com/verify",
                reset_url="https://example.com/reset",
                dashboard_url="https://example.com/dashboard",
                project_name=settings.PROJECT_NAME
            )
            print(f"✅ Template '{template_name}' renders correctly ({len(html)} chars)")
        except Exception as e:
            print(f"❌ Template '{template_name}' failed: {e}")
            return False

    print("\n=== TEMPLATE TEST COMPLETED ===")
    return True


if __name__ == "__main__":
    print("\n" + "="*50)
    print("   SALES CHECKLIST - AWS SES TEST SUITE")
    print("="*50 + "\n")

    # Test templates first
    template_result = test_email_templates()

    # Test SES service
    ses_result = test_ses()

    print("\n" + "="*50)
    print("   FINAL RESULTS")
    print("="*50)
    print(f"   Templates: {'✅ PASSED' if template_result else '❌ FAILED'}")
    print(f"   SES Service: {'✅ PASSED' if ses_result else '❌ FAILED'}")
    print("="*50 + "\n")

    sys.exit(0 if (template_result and ses_result) else 1)
