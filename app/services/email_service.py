"""
Amazon SES Email Service
"""
import boto3
import logging
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from jinja2 import Environment, BaseLoader
from app.core.config import settings

logger = logging.getLogger(__name__)


class TemplateLoader(BaseLoader):
    """Simple template loader for email templates"""
    
    def __init__(self):
        self.templates = {
            'email_verification': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email - {{ project_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ project_name }}</h1>
        <p>Welcome to the Sales Checklist™ Platform</p>
    </div>
    <div class="content">
        <h2>Verify Your Email Address</h2>
        <p>Hello {{ user_name }},</p>
        <p>Thank you for registering with {{ project_name }}! To complete your account setup and access all features, please verify your email address by clicking the button below:</p>
        <p style="text-align: center;">
            <a href="{{ verification_url }}" class="button">Verify Email Address</a>
        </p>
        <p>If the button above doesn't work, you can copy and paste this URL into your browser:</p>
        <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px;">{{ verification_url }}</p>
        <p>This verification link will expire in <strong>24 hours</strong>.</p>
        <p>If you didn't create an account with us, please ignore this email.</p>
        <p>Best regards,<br>The {{ project_name }} Team</p>
    </div>
    <div class="footer">
        <p>&copy; 2024 {{ project_name }}. All rights reserved.</p>
        <p>This email was sent to {{ user_email }}</p>
    </div>
</body>
</html>
            ''',
            'password_reset': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Your Password - {{ project_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; background: #e74c3c; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
        .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #666; }
        .warning { background: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ project_name }}</h1>
        <p>Password Reset Request</p>
    </div>
    <div class="content">
        <h2>Reset Your Password</h2>
        <p>Hello {{ user_name }},</p>
        <p>We received a request to reset your password for your {{ project_name }} account. If you made this request, click the button below to reset your password:</p>
        <p style="text-align: center;">
            <a href="{{ reset_url }}" class="button">Reset Password</a>
        </p>
        <p>If the button above doesn't work, you can copy and paste this URL into your browser:</p>
        <p style="word-break: break-all; background: #eee; padding: 10px; border-radius: 5px;">{{ reset_url }}</p>
        <div class="warning">
            <strong>Security Notice:</strong> This password reset link will expire in <strong>1 hour</strong> for your security.
        </div>
        <p>If you didn't request a password reset, please ignore this email. Your password will remain unchanged.</p>
        <p>For security reasons, if you continue to receive these emails, please contact our support team.</p>
        <p>Best regards,<br>The {{ project_name }} Team</p>
    </div>
    <div class="footer">
        <p>&copy; 2024 {{ project_name }}. All rights reserved.</p>
        <p>This email was sent to {{ user_email }}</p>
    </div>
</body>
</html>
            ''',
            'welcome': '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Welcome to {{ project_name }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; background: #27ae60; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
        .feature { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #667eea; }
        .footer { text-align: center; margin-top: 30px; font-size: 14px; color: #666; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎉 Welcome to {{ project_name }}!</h1>
        <p>Your account is now active and ready to use</p>
    </div>
    <div class="content">
        <h2>Hello {{ user_name }},</h2>
        <p>Welcome to {{ project_name }}! We're thrilled to have you on board. Your email has been verified and your account is now fully activated.</p>
        
        <h3>Get Started with These Key Features:</h3>
        <div class="feature">
            <strong>📊 Sales Session Analysis</strong><br>
            Upload and analyze your sales calls with AI-powered insights
        </div>
        <div class="feature">
            <strong>✅ Checklist Scoring</strong><br>
            Get detailed scores and feedback based on sales best practices
        </div>
        <div class="feature">
            <strong>📈 Performance Tracking</strong><br>
            Monitor your progress and identify areas for improvement
        </div>
        <div class="feature">
            <strong>📝 Detailed Reports</strong><br>
            Generate comprehensive reports for your sales activities
        </div>
        
        <p style="text-align: center;">
            <a href="{{ dashboard_url }}" class="button">Go to Dashboard</a>
        </p>
        
        <p>If you have any questions or need assistance getting started, don't hesitate to reach out to our support team.</p>
        <p>Best regards,<br>The {{ project_name }} Team</p>
    </div>
    <div class="footer">
        <p>&copy; 2024 {{ project_name }}. All rights reserved.</p>
        <p>This email was sent to {{ user_email }}</p>
    </div>
</body>
</html>
            '''
        }

    def get_source(self, environment, template):
        if template not in self.templates:
            raise Exception(f"Template {template} not found")
        source = self.templates[template]
        return source, None, lambda: True


class EmailService:
    """Amazon SES email service for sending transactional emails"""

    def __init__(self):
        """Initialize SES client"""
        self.ses_client = None
        self.env = Environment(loader=TemplateLoader())
        
        # Only initialize if we have AWS credentials
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            try:
                self.ses_client = boto3.client(
                    'ses',
                    region_name=settings.SES_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                logger.info(f"SES client initialized for region: {settings.SES_REGION}")
            except Exception as e:
                logger.error(f"Failed to initialize SES client: {str(e)}")
                self.ses_client = None
        else:
            logger.warning("AWS credentials not configured. Email service disabled.")

    def _send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send an email using Amazon SES
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content (optional)
            reply_to: Reply-to address (optional)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not self.ses_client:
            logger.error("SES client not initialized. Cannot send email.")
            return False

        if not settings.SES_SENDER_EMAIL:
            logger.error("SES_SENDER_EMAIL not configured. Cannot send email.")
            return False

        try:
            # Prepare message
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
            
            if text_body:
                message['Body']['Text'] = {'Data': text_body, 'Charset': 'UTF-8'}

            # Send email
            response = self.ses_client.send_email(
                Source=settings.SES_SENDER_EMAIL,
                Destination={'ToAddresses': to_emails},
                Message=message,
                ReplyToAddresses=[reply_to] if reply_to else []
            )
            
            message_id = response['MessageId']
            logger.info(f"Email sent successfully. MessageId: {message_id}")
            return True

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"AWS SES ClientError [{error_code}]: {error_message}")
            return False
        except BotoCoreError as e:
            logger.error(f"AWS SES BotoCoreError: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending email: {str(e)}")
            return False

    def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_token: str,
        base_url: str = "https://app.saleschecklist.com"
    ) -> bool:
        """
        Send email verification email
        
        Args:
            user_email: User's email address
            user_name: User's display name
            verification_token: Email verification token
            base_url: Base URL for verification link
            
        Returns:
            bool: True if email was sent successfully
        """
        verification_url = f"{base_url}/verify-email?token={verification_token}"
        
        template = self.env.get_template('email_verification')
        html_content = template.render(
            user_name=user_name,
            user_email=user_email,
            verification_url=verification_url,
            project_name=settings.PROJECT_NAME
        )
        
        subject = f"Verify Your Email - {settings.PROJECT_NAME}"
        
        return self._send_email(
            to_emails=[user_email],
            subject=subject,
            html_body=html_content
        )

    def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str,
        base_url: str = "https://app.saleschecklist.com"
    ) -> bool:
        """
        Send password reset email
        
        Args:
            user_email: User's email address
            user_name: User's display name
            reset_token: Password reset token
            base_url: Base URL for reset link
            
        Returns:
            bool: True if email was sent successfully
        """
        reset_url = f"{base_url}/reset-password?token={reset_token}"
        
        template = self.env.get_template('password_reset')
        html_content = template.render(
            user_name=user_name,
            user_email=user_email,
            reset_url=reset_url,
            project_name=settings.PROJECT_NAME
        )
        
        subject = f"Reset Your Password - {settings.PROJECT_NAME}"
        
        return self._send_email(
            to_emails=[user_email],
            subject=subject,
            html_body=html_content
        )

    def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        dashboard_url: str = "https://app.saleschecklist.com/dashboard"
    ) -> bool:
        """
        Send welcome email after successful registration
        
        Args:
            user_email: User's email address
            user_name: User's display name
            dashboard_url: URL to the user dashboard
            
        Returns:
            bool: True if email was sent successfully
        """
        template = self.env.get_template('welcome')
        html_content = template.render(
            user_name=user_name,
            user_email=user_email,
            dashboard_url=dashboard_url,
            project_name=settings.PROJECT_NAME
        )
        
        subject = f"Welcome to {settings.PROJECT_NAME}!"
        
        return self._send_email(
            to_emails=[user_email],
            subject=subject,
            html_body=html_content
        )

    def send_notification_email(
        self,
        to_emails: List[str],
        subject: str,
        message: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send a general notification email
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            message: Email message content
            user_name: Optional user name for personalization
            
        Returns:
            bool: True if email was sent successfully
        """
        greeting = f"Hello {user_name}," if user_name else "Hello,"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #667eea; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 14px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{settings.PROJECT_NAME}</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                <p>{message}</p>
                <p>Best regards,<br>The {settings.PROJECT_NAME} Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2024 {settings.PROJECT_NAME}. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        return self._send_email(
            to_emails=to_emails,
            subject=subject,
            html_body=html_content
        )

    def verify_email_address(self, email: str) -> bool:
        """
        Verify an email address with Amazon SES
        
        Args:
            email: Email address to verify
            
        Returns:
            bool: True if verification was initiated successfully
        """
        if not self.ses_client:
            logger.error("SES client not initialized. Cannot verify email.")
            return False

        try:
            response = self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Email verification initiated for {email}")
            return True
        except ClientError as e:
            logger.error(f"Failed to verify email {email}: {str(e)}")
            return False

    def get_send_quota(self) -> Dict[str, Any]:
        """
        Get the current send quota for the AWS account
        
        Returns:
            dict: Send quota information including daily limit and current usage
        """
        if not self.ses_client:
            return {"error": "SES client not initialized"}

        try:
            response = self.ses_client.get_send_quota()
            return {
                "max_24_hour_send": response['Max24HourSend'],
                "max_send_rate": response['MaxSendRate'],
                "sent_last_24_hours": response['SentLast24Hours']
            }
        except ClientError as e:
            return {"error": str(e)}


# Global email service instance
email_service = EmailService()