"""
Amazon SES Email Service
"""

import boto3
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional, Dict, Any
from botocore.exceptions import ClientError, BotoCoreError
from jinja2 import Environment, BaseLoader
from app.core.config import settings

logger = logging.getLogger(__name__)


class TemplateLoader(BaseLoader):
    """Simple template loader for email templates"""

    def __init__(self):
        self.templates = {
            "email_verification": """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>Verify Your Email — {{ project_name }}</title>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

                    * { box-sizing: border-box; margin: 0; padding: 0; }

                    body {
                    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
                    background-color: #F0EDE8;
                    color: #1A1A1A;
                    -webkit-font-smoothing: antialiased;
                    padding: 40px 16px;
                    line-height: 1.6;
                    }

                    .email-wrapper { max-width: 560px; margin: 0 auto; }

                    /* ─── Pre-header ─── */
                    .pre-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 4px 24px;
                    }

                    .wordmark {
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.1em;
                    text-transform: uppercase;
                    color: #555;
                    }

                    .badge {
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #1A5C8A;
                    background: #D5E9F5;
                    border: 1px solid #A8CDE4;
                    border-radius: 100px;
                    padding: 4px 12px;
                    }

                    /* ─── Header ─── */
                    .header {
                    background-color: #141414;
                    border-radius: 16px 16px 0 0;
                    padding: 48px 40px 40px;
                    position: relative;
                    overflow: hidden;
                    }

                    .header::before {
                    content: '';
                    position: absolute;
                    top: -60px; right: -60px;
                    width: 220px; height: 220px;
                    border-radius: 50%;
                    border: 1px solid rgba(255,255,255,0.05);
                    }

                    .header::after {
                    content: '';
                    position: absolute;
                    top: -100px; right: -100px;
                    width: 320px; height: 320px;
                    border-radius: 50%;
                    border: 1px solid rgba(255,255,255,0.04);
                    }

                    .header-eyebrow {
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    color: #4A9CC4;
                    margin-bottom: 16px;
                    }

                    .header h1 {
                    font-size: 30px;
                    font-weight: 600;
                    color: #FFFFFF;
                    line-height: 1.25;
                    margin-bottom: 12px;
                    letter-spacing: -0.3px;
                    }

                    .header h1 span { color: #E0A84F; }

                    .header-sub {
                    font-size: 15px;
                    color: rgba(255,255,255,0.6);
                    font-weight: 400;
                    }

                    /* ─── Content ─── */
                    .content {
                    background: #FFFFFF;
                    border-radius: 0 0 16px 16px;
                    padding: 40px;
                    border: 1px solid #E8E2DA;
                    border-top: none;
                    }

                    .intro-text {
                    font-size: 16px;
                    color: #444;
                    line-height: 1.7;
                    margin-bottom: 28px;
                    }

                    .intro-text strong { color: #1A1A1A; font-weight: 600; }

                    /* ─── Steps ─── */
                    .steps-label {
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #999;
                    margin-bottom: 16px;
                    }

                    .steps-list { list-style: none; margin-bottom: 28px; }

                    .step-item {
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 10px 0;
                    border-bottom: 1px solid #F0EDE8;
                    font-size: 14px;
                    color: #444;
                    }

                    .step-item:last-child { border-bottom: none; }

                    .step-num {
                    width: 22px;
                    height: 22px;
                    border-radius: 50%;
                    background: #F0EDE8;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 11px;
                    font-weight: 600;
                    color: #888;
                    flex-shrink: 0;
                    margin-top: 1px;
                    }

                    /* ─── CTA ─── */
                    .cta-section { text-align: center; margin: 32px 0; }

                    .cta-button {
                    display: inline-block;
                    background: #1A1A1A;
                    color: #FFFFFF;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 600;
                    letter-spacing: 0.02em;
                    padding: 14px 36px;
                    border-radius: 8px;
                    }

                    .cta-sub { margin-top: 10px; font-size: 12px; color: #999; }

                    /* ─── Divider ─── */
                    .divider { height: 1px; background: #F0EDE8; margin: 28px 0; }

                    /* ─── Fallback URL ─── */
                    .fallback-url {
                    background: #F6F4F0;
                    border-radius: 8px;
                    padding: 14px 16px;
                    margin-bottom: 28px;
                    }

                    .fallback-label {
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #AAA;
                    margin-bottom: 6px;
                    }

                    .fallback-link {
                    font-family: 'DM Mono', 'Courier New', monospace;
                    font-size: 11px;
                    color: #555;
                    word-break: break-all;
                    line-height: 1.6;
                    }

                    /* ─── Expiry notice ─── */
                    .notice {
                    display: flex;
                    gap: 12px;
                    background: #FFFBF4;
                    border: 1px solid #F0D99A;
                    border-radius: 8px;
                    padding: 14px 16px;
                    margin-bottom: 28px;
                    }

                    .notice-text { font-size: 13px; color: #7A5C1A; line-height: 1.5; }
                    .notice-text strong { font-weight: 600; }

                    .body-text { font-size: 14px; color: #555; line-height: 1.7; margin-bottom: 12px; }

                    /* ─── Footer ─── */
                    .footer {
                    padding: 24px 4px 0;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    }

                    .footer-copy { font-size: 12px; color: #AAA; }

                    .footer-ignore {
                    font-size: 12px;
                    color: #BBB;
                    text-align: right;
                    max-width: 240px;
                    line-height: 1.5;
                    }

                    @media (max-width: 480px) {
                    .header, .content { padding: 28px 24px; }
                    .header h1 { font-size: 24px; }
                    .footer { flex-direction: column; gap: 8px; text-align: center; }
                    .footer-ignore { text-align: center; }
                    }
                </style>
                </head>
                <body>
                <div class="email-wrapper">

                    <!-- Pre-header -->
                    <div class="pre-header">
                    <span class="wordmark">{{ project_name }}</span>
                    <span class="badge">Verification</span>
                    </div>

                    <!-- Header -->
                    <div class="header">
                    <div class="header-eyebrow">One more step</div>
                    <h1>Confirm your <span>email</span></h1>
                    <p class="header-sub">You're almost ready — just verify your address to get started.</p>
                    </div>

                    <!-- Body -->
                    <div class="content">

                    <p class="intro-text">
                        Hello <strong>{{ user_name }}</strong>, thanks for signing up for
                        <strong>{{ project_name }}</strong>. Verify your email to unlock your account
                        and access all features.
                    </p>

                    <!-- Steps -->
                    <div class="steps-label">How it works</div>
                    <ul class="steps-list">
                        <li class="step-item">
                        <span class="step-num">1</span>
                        Click "Verify Email Address" below
                        </li>
                        <li class="step-item">
                        <span class="step-num">2</span>
                        You'll be redirected to confirm your account
                        </li>
                        <li class="step-item">
                        <span class="step-num">3</span>
                        Start using {{ project_name }} immediately
                        </li>
                    </ul>

                    <!-- CTA -->
                    <div class="cta-section">
                        <a href="{{ verification_url }}" class="cta-button">Verify Email Address &rarr;</a>
                        <p class="cta-sub">Expires in 24 hours</p>
                    </div>

                    <div class="divider"></div>

                    <!-- Fallback URL -->
                    <div class="fallback-url">
                        <div class="fallback-label">Or open this link in your browser</div>
                        <div class="fallback-link">{{ verification_url }}</div>
                    </div>

                    <!-- Notice -->
                    <div class="notice">
                        <div class="notice-text">
                        This verification link expires in <strong>24 hours</strong>. If you didn't
                        create an account with us, you can safely ignore this email.
                        </div>
                    </div>

                    <p class="body-text">
                        Best regards,<br />The {{ project_name }} Team
                    </p>

                    </div>

                    <!-- Footer -->
                    <div class="footer">
                    <div class="footer-copy">
                        &copy; 2024 {{ project_name }}. All rights reserved.<br />
                        Sent to {{ user_email }}
                    </div>
                    <div class="footer-ignore">
                        Didn't sign up? You can safely ignore this email.
                    </div>
                    </div>

                </div>
                </body>
                </html>
            """,
            "password_reset": """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>Reset Your Password — {{ project_name }}</title>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

                    * { box-sizing: border-box; margin: 0; padding: 0; }

                    body {
                    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
                    background-color: #F0EDE8;
                    color: #1A1A1A;
                    -webkit-font-smoothing: antialiased;
                    padding: 40px 16px;
                    line-height: 1.6;
                    }

                    .email-wrapper { max-width: 560px; margin: 0 auto; }

                    /* ─── Pre-header ─── */
                    .pre-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 4px 24px;
                    }

                    .wordmark {
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.1em;
                    text-transform: uppercase;
                    color: #555;
                    }

                    .badge {
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #A04A4A;
                    background: #F5D5D5;
                    border: 1px solid #E4AAAA;
                    border-radius: 100px;
                    padding: 4px 12px;
                    }

                    /* ─── Header ─── */
                    .header {
                    background-color: #141414;
                    border-radius: 16px 16px 0 0;
                    padding: 48px 40px 40px;
                    position: relative;
                    overflow: hidden;
                    }

                    .header::before {
                    content: '';
                    position: absolute;
                    top: -60px; right: -60px;
                    width: 220px; height: 220px;
                    border-radius: 50%;
                    border: 1px solid rgba(255,255,255,0.05);
                    }

                    .header::after {
                    content: '';
                    position: absolute;
                    top: -100px; right: -100px;
                    width: 320px; height: 320px;
                    border-radius: 50%;
                    border: 1px solid rgba(255,255,255,0.04);
                    }

                    .header-eyebrow {
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    color: #C44A4A;
                    margin-bottom: 16px;
                    }

                    .header h1 {
                    font-size: 30px;
                    font-weight: 600;
                    color: #FFFFFF;
                    line-height: 1.25;
                    margin-bottom: 12px;
                    letter-spacing: -0.3px;
                    }

                    .header-sub {
                    font-size: 15px;
                    color: rgba(255,255,255,0.6);
                    font-weight: 400;
                    }

                    /* ─── Content ─── */
                    .content {
                    background: #FFFFFF;
                    border-radius: 0 0 16px 16px;
                    padding: 40px;
                    border: 1px solid #E8E2DA;
                    border-top: none;
                    }

                    .intro-text {
                    font-size: 16px;
                    color: #444;
                    line-height: 1.7;
                    margin-bottom: 32px;
                    }

                    .intro-text strong { color: #1A1A1A; font-weight: 600; }

                    /* ─── Expiry Banner ─── */
                    .expiry-banner {
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    background: #FDF6F6;
                    border: 1px solid #F0CCCC;
                    border-radius: 10px;
                    padding: 16px 20px;
                    margin-bottom: 28px;
                    }

                    .expiry-icon {
                    width: 36px;
                    height: 36px;
                    border-radius: 50%;
                    background: #F5D5D5;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    flex-shrink: 0;
                    font-size: 16px;
                    }

                    .expiry-text {
                    font-size: 14px;
                    color: #8A3030;
                    line-height: 1.5;
                    }

                    .expiry-text strong { font-weight: 600; }

                    /* ─── CTA ─── */
                    .cta-section { text-align: center; margin: 32px 0; }

                    .cta-button {
                    display: inline-block;
                    background: #1A1A1A;
                    color: #FFFFFF;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 600;
                    letter-spacing: 0.02em;
                    padding: 14px 36px;
                    border-radius: 8px;
                    }

                    .cta-sub { margin-top: 10px; font-size: 12px; color: #999; }

                    /* ─── Divider ─── */
                    .divider { height: 1px; background: #F0EDE8; margin: 28px 0; }

                    /* ─── Fallback URL ─── */
                    .fallback-url {
                    background: #F6F4F0;
                    border-radius: 8px;
                    padding: 14px 16px;
                    margin-bottom: 28px;
                    }

                    .fallback-label {
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #AAA;
                    margin-bottom: 6px;
                    }

                    .fallback-link {
                    font-family: 'DM Mono', 'Courier New', monospace;
                    font-size: 11px;
                    color: #555;
                    word-break: break-all;
                    line-height: 1.6;
                    }

                    /* ─── Notice ─── */
                    .notice {
                    display: flex;
                    gap: 12px;
                    background: #FFFBF4;
                    border: 1px solid #F0D99A;
                    border-radius: 8px;
                    padding: 14px 16px;
                    margin-bottom: 28px;
                    }

                    .notice-text { font-size: 13px; color: #7A5C1A; line-height: 1.5; }

                    /* ─── Body text ─── */
                    .body-text { font-size: 14px; color: #555; line-height: 1.7; margin-bottom: 12px; }
                    .body-text strong { color: #1A1A1A; }

                    /* ─── Footer ─── */
                    .footer {
                    padding: 24px 4px 0;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    }

                    .footer-copy { font-size: 12px; color: #AAA; }

                    .footer-ignore {
                    font-size: 12px;
                    color: #BBB;
                    text-align: right;
                    max-width: 240px;
                    line-height: 1.5;
                    }

                    @media (max-width: 480px) {
                    .header, .content { padding: 28px 24px; }
                    .header h1 { font-size: 24px; }
                    .footer { flex-direction: column; gap: 8px; text-align: center; }
                    .footer-ignore { text-align: center; }
                    }
                </style>
                </head>
                <body>
                <div class="email-wrapper">

                    <!-- Pre-header -->
                    <div class="pre-header">
                    <span class="wordmark">{{ project_name }}</span>
                    <span class="badge">Security</span>
                    </div>

                    <!-- Header -->
                    <div class="header">
                    <div class="header-eyebrow">Password reset request</div>
                    <h1>Reset your password</h1>
                    <p class="header-sub">A reset was requested for your {{ project_name }} account.</p>
                    </div>

                    <!-- Body -->
                    <div class="content">

                    <p class="intro-text">
                        Hello <strong>{{ user_name }}</strong>, we received a request to reset the
                        password on your account. Click below to choose a new one.
                    </p>

                    <!-- Expiry Banner -->
                    <div class="expiry-banner">
                        <div class="expiry-text">
                        This link expires in <strong>1 hour</strong>. After that you'll need to
                        request a new reset.
                        </div>
                    </div>

                    <!-- CTA -->
                    <div class="cta-section">
                        <a href="{{ reset_url }}" class="cta-button">Reset Password &rarr;</a>
                        <p class="cta-sub">Expires in 1 hour</p>
                    </div>

                    <div class="divider"></div>

                    <!-- Fallback URL -->
                    <div class="fallback-url">
                        <div class="fallback-label">Or open this link in your browser</div>
                        <div class="fallback-link">{{ reset_url }}</div>
                    </div>

                    <!-- Notice -->
                    <div class="notice">
                        <div class="notice-text">
                        Didn't request this? You can safely ignore this email — your password
                        will not change. If you keep receiving these, contact our support team.
                        </div>
                    </div>

                    <p class="body-text">
                        Best regards,<br />The {{ project_name }} Team
                    </p>

                    </div>

                    <!-- Footer -->
                    <div class="footer">
                    <div class="footer-copy">
                        &copy; 2024 {{ project_name }}. All rights reserved.<br />
                        Sent to {{ user_email }}
                    </div>
                    <div class="footer-ignore">
                        Didn't request a reset? Ignore this email safely.
                    </div>
                    </div>

                </div>
                </body>
                </html>
            """,
            "welcome": """
                <!DOCTYPE html>
                <html lang="en">
                <head>
                <meta charset="UTF-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                <title>Welcome to {{ project_name }}</title>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

                    * { box-sizing: border-box; margin: 0; padding: 0; }

                    body {
                    font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
                    background-color: #F0EDE8;
                    color: #1A1A1A;
                    -webkit-font-smoothing: antialiased;
                    padding: 40px 16px;
                    line-height: 1.6;
                    }

                    .email-wrapper { max-width: 560px; margin: 0 auto; }

                    /* ─── Pre-header ─── */
                    .pre-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 0 4px 24px;
                    }

                    .wordmark {
                    font-size: 13px;
                    font-weight: 600;
                    letter-spacing: 0.1em;
                    text-transform: uppercase;
                    color: #555;
                    }

                    .badge {
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #2A6B3A;
                    background: #D5F0DC;
                    border: 1px solid #A8D9B2;
                    border-radius: 100px;
                    padding: 4px 12px;
                    }

                    /* ─── Header ─── */
                    .header {
                    background-color: #141414;
                    border-radius: 16px 16px 0 0;
                    padding: 48px 40px 40px;
                    position: relative;
                    overflow: hidden;
                    }

                    .header::before {
                    content: '';
                    position: absolute;
                    top: -60px; right: -60px;
                    width: 220px; height: 220px;
                    border-radius: 50%;
                    border: 1px solid rgba(255,255,255,0.05);
                    }

                    .header::after {
                    content: '';
                    position: absolute;
                    top: -100px; right: -100px;
                    width: 320px; height: 320px;
                    border-radius: 50%;
                    border: 1px solid rgba(255,255,255,0.04);
                    }

                    .header-eyebrow {
                    font-size: 11px;
                    font-weight: 500;
                    letter-spacing: 0.12em;
                    text-transform: uppercase;
                    color: #4AC472;
                    margin-bottom: 16px;
                    }

                    .header h1 {
                    font-size: 30px;
                    font-weight: 600;
                    color: #FFFFFF;
                    line-height: 1.25;
                    margin-bottom: 12px;
                    letter-spacing: -0.3px;
                    }

                    .header h1 span { color: #E0A84F; }

                    .header-sub {
                    font-size: 15px;
                    color: rgba(255,255,255,0.6);
                    font-weight: 400;
                    }

                    /* ─── Content ─── */
                    .content {
                    background: #FFFFFF;
                    border-radius: 0 0 16px 16px;
                    padding: 40px;
                    border: 1px solid #E8E2DA;
                    border-top: none;
                    }

                    .intro-text {
                    font-size: 16px;
                    color: #444;
                    line-height: 1.7;
                    margin-bottom: 32px;
                    }

                    .intro-text strong { color: #1A1A1A; font-weight: 600; }

                    /* ─── Account Active Banner ─── */
                    .active-banner {
                    display: flex;
                    align-items: center;
                    gap: 14px;
                    background: #F2FBF4;
                    border: 1px solid #B8DFC0;
                    border-radius: 10px;
                    padding: 16px 20px;
                    margin-bottom: 32px;
                    }

                    .active-dot {
                    width: 10px;
                    height: 10px;
                    border-radius: 50%;
                    background: #3AB55A;
                    flex-shrink: 0;
                    box-shadow: 0 0 0 3px rgba(58,181,90,0.2);
                    }

                    .active-text {
                    font-size: 14px;
                    font-weight: 500;
                    color: #1E6B34;
                    }

                    /* ─── Features ─── */
                    .features-label {
                    font-size: 11px;
                    font-weight: 600;
                    letter-spacing: 0.08em;
                    text-transform: uppercase;
                    color: #999;
                    margin-bottom: 12px;
                    }

                    .features-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 1px;
                    background: #EDEAE4;
                    border: 1px solid #EDEAE4;
                    border-radius: 10px;
                    overflow: hidden;
                    margin-bottom: 32px;
                    }

                    .feature-cell {
                    background: #FAFAF8;
                    padding: 18px 20px;
                    }

                    .feature-num {
                    font-family: 'DM Mono', 'Courier New', monospace;
                    font-size: 10px;
                    font-weight: 500;
                    color: #BBB;
                    letter-spacing: 0.08em;
                    margin-bottom: 8px;
                    }

                    .feature-title {
                    font-size: 13px;
                    font-weight: 600;
                    color: #1A1A1A;
                    margin-bottom: 4px;
                    line-height: 1.35;
                    }

                    .feature-desc {
                    font-size: 12px;
                    color: #777;
                    line-height: 1.5;
                    }

                    /* ─── CTA ─── */
                    .cta-section { text-align: center; margin: 32px 0; }

                    .cta-button {
                    display: inline-block;
                    background: #1A1A1A;
                    color: #FFFFFF;
                    text-decoration: none;
                    font-size: 14px;
                    font-weight: 600;
                    letter-spacing: 0.02em;
                    padding: 14px 36px;
                    border-radius: 8px;
                    }

                    .cta-sub { margin-top: 10px; font-size: 12px; color: #999; }

                    /* ─── Divider ─── */
                    .divider { height: 1px; background: #F0EDE8; margin: 28px 0; }

                    /* ─── Support note ─── */
                    .support-note {
                    background: #F6F4F0;
                    border-radius: 8px;
                    padding: 14px 18px;
                    font-size: 13px;
                    color: #666;
                    line-height: 1.6;
                    margin-bottom: 24px;
                    }

                    .body-text {
                    font-size: 14px;
                    color: #555;
                    line-height: 1.7;
                    }

                    /* ─── Footer ─── */
                    .footer {
                    padding: 24px 4px 0;
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    }

                    .footer-copy { font-size: 12px; color: #AAA; }

                    .footer-right {
                    font-size: 12px;
                    color: #BBB;
                    text-align: right;
                    max-width: 240px;
                    line-height: 1.5;
                    }

                    @media (max-width: 480px) {
                    .header, .content { padding: 28px 24px; }
                    .header h1 { font-size: 24px; }
                    .features-grid { grid-template-columns: 1fr; }
                    .footer { flex-direction: column; gap: 8px; text-align: center; }
                    .footer-right { text-align: center; }
                    }
                </style>
                </head>
                <body>
                <div class="email-wrapper">

                    <!-- Pre-header -->
                    <div class="pre-header">
                    <span class="wordmark">{{ project_name }}</span>
                    <span class="badge">Welcome</span>
                    </div>

                    <!-- Header -->
                    <div class="header">
                    <div class="header-eyebrow">Account activated</div>
                    <h1>Welcome to <span>{{ project_name }}</span></h1>
                    <p class="header-sub">Your account is live and ready to go.</p>
                    </div>

                    <!-- Body -->
                    <div class="content">

                    <p class="intro-text">
                        Hello <strong>{{ user_name }}</strong> — your email has been verified and your
                        account is fully active. Here's everything you can do from day one.
                    </p>

                    <!-- Active status -->
                    <div class="active-banner">
                        <div class="active-dot"></div>
                        <div class="active-text">Account verified &amp; active</div>
                    </div>

                    <!-- Features -->
                    <div class="features-label">What you have access to</div>
                    <div class="features-grid">
                        <div class="feature-cell">
                        <div class="feature-num">01</div>
                        <div class="feature-title">Sales Session Analysis</div>
                        <div class="feature-desc">Upload calls and get AI-powered insights instantly</div>
                        </div>
                        <div class="feature-cell">
                        <div class="feature-num">02</div>
                        <div class="feature-title">Checklist Scoring</div>
                        <div class="feature-desc">Scores and feedback grounded in sales best practices</div>
                        </div>
                        <div class="feature-cell">
                        <div class="feature-num">03</div>
                        <div class="feature-title">Performance Tracking</div>
                        <div class="feature-desc">Monitor progress and surface improvement areas over time</div>
                        </div>
                        <div class="feature-cell">
                        <div class="feature-num">04</div>
                        <div class="feature-title">Detailed Reports</div>
                        <div class="feature-desc">Generate comprehensive reports across all your sessions</div>
                        </div>
                    </div>

                    <!-- CTA -->
                    <div class="cta-section">
                        <a href="{{ dashboard_url }}" class="cta-button">Go to Dashboard &rarr;</a>
                        <p class="cta-sub">Your workspace is ready</p>
                    </div>

                    <div class="divider"></div>

                    <!-- Support -->
                    <div class="support-note">
                        Questions or need a hand getting started? Reach out to our support team — we're happy to help.
                    </div>

                    <p class="body-text">
                        Best regards,<br />The {{ project_name }} Team
                    </p>

                    </div>

                    <!-- Footer -->
                    <div class="footer">
                    <div class="footer-copy">
                        &copy; 2024 {{ project_name }}. All rights reserved.<br />
                        Sent to {{ user_email }}
                    </div>
                    <div class="footer-right">
                        You're receiving this because you created an account.
                    </div>
                    </div>

                </div>
                </body>
                </html>
            """,
            "invitation": """
                <!doctype html>
                <html lang="en">
                <head>
                    <meta charset="UTF-8" />
                    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
                    <title>You're Invited to Join {{ organization_name }} — {{ project_name }}</title>
                    <style>
                    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

                    * { box-sizing: border-box; margin: 0; padding: 0; }

                    body {
                        font-family: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
                        background-color: #F0EDE8;
                        color: #1A1A1A;
                        -webkit-font-smoothing: antialiased;
                        padding: 40px 16px;
                        line-height: 1.6;
                    }

                    .email-wrapper {
                        max-width: 560px;
                        margin: 0 auto;
                    }

                    /* ─── Wordmark / Pre-header ─── */
                    .pre-header {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        padding: 0 4px 24px;
                    }

                    .wordmark {
                        font-size: 13px;
                        font-weight: 600;
                        letter-spacing: 0.1em;
                        text-transform: uppercase;
                        color: #555;
                    }

                    .badge {
                        font-size: 11px;
                        font-weight: 500;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                        color: #A0845A;
                        background: #F5E8D5;
                        border: 1px solid #E4C99A;
                        border-radius: 100px;
                        padding: 4px 12px;
                    }

                    /* ─── Header Block ─── */
                    .header {
                        background-color: #141414;
                        border-radius: 16px 16px 0 0;
                        padding: 48px 40px 40px;
                        position: relative;
                        overflow: hidden;
                    }

                    .header::before {
                        content: '';
                        position: absolute;
                        top: -60px;
                        right: -60px;
                        width: 220px;
                        height: 220px;
                        border-radius: 50%;
                        border: 1px solid rgba(255,255,255,0.05);
                    }

                    .header::after {
                        content: '';
                        position: absolute;
                        top: -100px;
                        right: -100px;
                        width: 320px;
                        height: 320px;
                        border-radius: 50%;
                        border: 1px solid rgba(255,255,255,0.04);
                    }

                    .header-eyebrow {
                        font-size: 11px;
                        font-weight: 500;
                        letter-spacing: 0.12em;
                        text-transform: uppercase;
                        color: #C4934A;
                        margin-bottom: 16px;
                    }

                    .header h1 {
                        font-size: 30px;
                        font-weight: 600;
                        color: #FFFFFF;
                        line-height: 1.25;
                        margin-bottom: 12px;
                        letter-spacing: -0.3px;
                    }

                    .header h1 span {
                        color: #E0A84F;
                    }

                    .header-sub {
                        font-size: 15px;
                        color: rgba(255,255,255,0.6);
                        font-weight: 400;
                    }

                    /* ─── Content ─── */
                    .content {
                        background: #FFFFFF;
                        border-radius: 0 0 16px 16px;
                        padding: 40px;
                        border: 1px solid #E8E2DA;
                        border-top: none;
                    }

                    .intro-text {
                        font-size: 16px;
                        color: #444;
                        line-height: 1.7;
                        margin-bottom: 32px;
                    }

                    .intro-text strong {
                        color: #1A1A1A;
                        font-weight: 600;
                    }

                    /* ─── Details Row ─── */
                    .details-grid {
                        display: grid;
                        grid-template-columns: 1fr 1fr;
                        gap: 1px;
                        background: #EDEAE4;
                        border: 1px solid #EDEAE4;
                        border-radius: 10px;
                        overflow: hidden;
                        margin-bottom: 28px;
                    }

                    .detail-cell {
                        background: #FAFAF8;
                        padding: 16px 20px;
                    }

                    .detail-cell:nth-child(odd) {
                        border-right: none;
                    }

                    .detail-label {
                        font-size: 11px;
                        font-weight: 600;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                        color: #999;
                        margin-bottom: 5px;
                    }

                    .detail-value {
                        font-size: 14px;
                        font-weight: 500;
                        color: #1A1A1A;
                    }

                    .role-pill {
                        display: inline-block;
                        background: #F0F7EE;
                        color: #3A7A31;
                        border: 1px solid #C5DFC2;
                        border-radius: 100px;
                        font-size: 12px;
                        font-weight: 500;
                        padding: 2px 10px;
                    }

                    /* ─── Divider ─── */
                    .divider {
                        height: 1px;
                        background: #F0EDE8;
                        margin: 28px 0;
                    }

                    /* ─── Credentials Box ─── */
                    .creds-label {
                        font-size: 11px;
                        font-weight: 600;
                        letter-spacing: 0.1em;
                        text-transform: uppercase;
                        color: #999;
                        margin-bottom: 12px;
                    }

                    .creds-box {
                        background: #0F0F0F;
                        border-radius: 10px;
                        padding: 20px 24px;
                        margin-bottom: 20px;
                        position: relative;
                        overflow: hidden;
                    }

                    .creds-box::before {
                        content: 'CREDENTIALS';
                        position: absolute;
                        top: 14px;
                        right: 18px;
                        font-size: 10px;
                        font-weight: 600;
                        letter-spacing: 0.12em;
                        color: rgba(255,255,255,0.12);
                    }

                    .cred-row {
                        display: flex;
                        align-items: baseline;
                        gap: 12px;
                        margin-bottom: 10px;
                    }

                    .cred-row:last-child {
                        margin-bottom: 0;
                    }

                    .cred-key {
                        font-family: 'DM Mono', 'Courier New', monospace;
                        font-size: 11px;
                        color: rgba(255,255,255,0.6);
                        min-width: 60px;
                        flex-shrink: 0;
                    }

                    .cred-value {
                        font-family: 'DM Mono', 'Courier New', monospace;
                        font-size: 13px;
                        color: #F0F0F0;
                        font-weight: 500;
                        word-break: break-all;
                    }

                    .cred-password {
                        font-size: 15px;
                        color: #E0A84F;
                        letter-spacing: 0.04em;
                    }

                    /* ─── Security Notice ─── */
                    .notice {
                        display: flex;
                        gap: 12px;
                        background: #FFFBF4;
                        border: 1px solid #F0D99A;
                        border-radius: 8px;
                        padding: 14px 16px;
                        margin-bottom: 28px;
                    }

                    .notice-icon {
                        font-size: 14px;
                        flex-shrink: 0;
                        margin-top: 1px;
                    }

                    .notice-text {
                        font-size: 13px;
                        color: #7A5C1A;
                        line-height: 1.5;
                    }

                    /* ─── CTA ─── */
                    .cta-section {
                        text-align: center;
                        margin: 32px 0;
                    }

                    .cta-button {
                        display: inline-block;
                        background: #1A1A1A;
                        color: #FFFFFF;
                        text-decoration: none;
                        font-size: 14px;
                        font-weight: 600;
                        letter-spacing: 0.02em;
                        padding: 14px 36px;
                        border-radius: 8px;
                        transition: background 0.2s;
                    }

                    .cta-sub {
                        margin-top: 10px;
                        font-size: 12px;
                        color: #999;
                    }

                    /* ─── Fallback URL ─── */
                    .fallback-url {
                        background: #F6F4F0;
                        border-radius: 8px;
                        padding: 14px 16px;
                        margin-bottom: 24px;
                    }

                    .fallback-label {
                        font-size: 11px;
                        font-weight: 600;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                        color: #AAA;
                        margin-bottom: 6px;
                    }

                    .fallback-link {
                        font-family: 'DM Mono', 'Courier New', monospace;
                        font-size: 11px;
                        color: #555;
                        word-break: break-all;
                        line-height: 1.6;
                    }

                    /* ─── Steps ─── */
                    .steps-label {
                        font-size: 11px;
                        font-weight: 600;
                        letter-spacing: 0.08em;
                        text-transform: uppercase;
                        color: #999;
                        margin-bottom: 16px;
                    }

                    .steps-list {
                        list-style: none;
                    }

                    .step-item {
                        display: flex;
                        align-items: flex-start;
                        gap: 12px;
                        padding: 10px 0;
                        border-bottom: 1px solid #F0EDE8;
                        font-size: 14px;
                        color: #444;
                    }

                    .step-item:last-child {
                        border-bottom: none;
                    }

                    .step-num {
                        width: 22px;
                        height: 22px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 11px;
                        font-weight: 600;
                        color: #888;
                        flex-shrink: 0;
                        margin-top: 1px;
                    }

                    /* ─── Footer ─── */
                    .footer {
                        padding: 24px 4px 0;
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                    }

                    .footer-copy {
                        font-size: 12px;
                        color: #AAA;
                    }

                    .footer-ignore {
                        font-size: 12px;
                        color: #BBB;
                        text-align: right;
                        max-width: 240px;
                        line-height: 1.5;
                    }

                    @media (max-width: 480px) {
                        .header, .content { padding: 28px 24px; }
                        .header h1 { font-size: 24px; }
                        .details-grid { grid-template-columns: 1fr; }
                        .footer { flex-direction: column; gap: 8px; text-align: center; }
                        .footer-ignore { text-align: center; }
                    }
                    </style>
                </head>
                <body>
                    <div class="email-wrapper">

                    <!-- Pre-header -->
                    <div class="pre-header">
                        <span class="wordmark">{{ project_name }}</span>
                        <span class="badge">Invitation</span>
                    </div>

                    <!-- Header -->
                    <div class="header">
                        <div class="header-eyebrow">You have been invited</div>
                        <h1>Join <span>{{ organization_name }}</span></h1>
                        <p class="header-sub">{{ inviter_name }} has added you to their workspace.</p>
                    </div>

                    <!-- Body -->
                    <div class="content">

                        <p class="intro-text">
                        <strong>{{ inviter_name }}</strong> has invited you to collaborate on
                        <strong>{{ organization_name }}</strong>. An account has been created
                        and is ready for you — use the credentials below to sign in.
                        </p>

                        <!-- Details Grid -->
                        <div class="details-grid">
                        <div class="detail-cell">
                            <div class="detail-label">Organization</div>
                            <div class="detail-value">{{ organization_name }}</div>
                        </div>
                        <div class="detail-cell">
                            <div class="detail-label">Team</div>
                            <div class="detail-value">{{ team_name if team_name else '—' }}</div>
                        </div>
                        <div class="detail-cell">
                            <div class="detail-label">Role</div>
                            <div class="detail-value">
                            <span class="role-pill">{{ role|capitalize }}</span>
                            </div>
                        </div>
                        <div class="detail-cell">
                            <div class="detail-label">Expires In</div>
                            <div class="detail-value">7 days</div>
                        </div>
                        </div>

                        <!-- Credentials -->
                        <div class="creds-label">Your login credentials</div>
                        <div class="creds-box">
                        <div class="cred-row">
                            <span class="cred-key">email</span>
                            <span class="cred-value">{{ user_email }}</span>
                        </div>
                        <div class="cred-row">
                            <span class="cred-key">password</span>
                            <span class="cred-value cred-password">{{ temp_password }}</span>
                        </div>
                        </div>

                        <!-- Security Notice -->
                        <div class="notice">
                        <div class="notice-icon">&#9432;</div>
                        <div class="notice-text">
                            This is a temporary password. You will be prompted to set a new
                            password on your first login.
                        </div>
                        </div>

                        <!-- CTA -->
                        <div class="cta-section">
                        <a href="{{ invite_url }}" class="cta-button">Accept Invitation &rarr;</a>
                        <p class="cta-sub">This invitation expires in 7 days</p>
                        </div>

                        <div class="divider"></div>

                        <!-- Fallback URL -->
                        <div class="fallback-url">
                        <div class="fallback-label">Or open this link in your browser</div>
                        <div class="fallback-link">{{ invite_url }}</div>
                        </div>

                        <!-- Steps -->
                        <div class="steps-label">What to do next</div>
                        <ul class="steps-list">
                        <li class="step-item">
                            <span class="step-num">1</span>
                            Click "Accept Invitation" above
                        </li>
                        <li class="step-item">
                            <span class="step-num">2</span>
                            Sign in with your email and the temporary password
                        </li>
                        <li class="step-item">
                            <span class="step-num">3</span>
                            Complete the invitation acceptance flow
                        </li>
                        <li class="step-item">
                            <span class="step-num">4</span>
                            Set a new secure password when prompted
                        </li>
                        </ul>

                    </div>

                    <!-- Footer -->
                    <div class="footer">
                        <div class="footer-copy">
                        &copy; 2024 {{ project_name }}. All rights reserved.<br />
                        Sent to {{ user_email }}
                        </div>
                        <div class="footer-ignore">
                        Didn't expect this? You can safely ignore this email.
                        </div>
                    </div>

                    </div>
                </body>
                </html>
            """,
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
                    "ses",
                    region_name=settings.SES_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
                logger.info(f"SES client initialized for region: {settings.SES_REGION}")
            except Exception as e:
                logger.error(f"Failed to initialize SES client: {str(e)}")
                self.ses_client = None
        else:
            logger.warning(
                "AWS SES credentials not configured. SMTP may be used if configured."
            )

    def _send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email using Amazon SES first; fall back to SMTP if SES isn't configured or fails.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_body: HTML body content
            text_body: Plain text body content (optional)
            reply_to: Reply-to address (optional)

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        # 1) Attempt SES if configured
        if self.ses_client and settings.SES_SENDER_EMAIL:
            try:
                message = {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
                }
                if text_body:
                    message["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}

                response = self.ses_client.send_email(
                    Source=settings.SES_SENDER_EMAIL,
                    Destination={"ToAddresses": to_emails},
                    Message=message,
                    ReplyToAddresses=[reply_to] if reply_to else [],
                )
                message_id = response.get("MessageId")
                logger.info(f"Email sent via SES successfully. MessageId: {message_id}")
                return True
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code")
                error_message = e.response.get("Error", {}).get("Message")
                logger.error(
                    f"AWS SES ClientError [{error_code}]: {error_message}. Falling back to SMTP."
                )
            except BotoCoreError as e:
                logger.error(f"AWS SES BotoCoreError: {str(e)}. Falling back to SMTP.")
            except Exception as e:
                logger.error(f"Unexpected SES error: {str(e)}. Falling back to SMTP.")

        # 2) SMTP fallback
        return self._send_email_via_smtp(
            to_emails=to_emails,
            subject=subject,
            html_body=html_body,
            text_body=text_body,
            reply_to=reply_to,
        )

    def _send_email_via_smtp(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> bool:
        """
        Send an email using SMTP.

        Expected env vars (see app/core/config.py):
        - SMTP_HOST
        - SMTP_PORT
        - SMTP_USERNAME (optional)
        - SMTP_PASSWORD (optional)
        - SMTP_SENDER_EMAIL
        """
        if not settings.SMTP_HOST or not settings.SMTP_SENDER_EMAIL:
            logger.error(
                "SMTP not configured (SMTP_HOST/SMTP_SENDER_EMAIL missing). Cannot send email."
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = str(subject)
            msg["From"] = settings.SMTP_SENDER_EMAIL
            msg["To"] = ", ".join(to_emails)
            if reply_to:
                msg["Reply-To"] = reply_to

            if text_body:
                msg.attach(MIMEText(text_body, "plain", "utf-8"))
            else:
                # Some SMTP providers behave better if Text part exists.
                msg.attach(MIMEText("", "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            timeout = getattr(settings, "SMTP_TIMEOUT_SECONDS", 30)
            if settings.SMTP_USE_SSL:
                server = smtplib.SMTP_SSL(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout
                )
            else:
                server = smtplib.SMTP(
                    settings.SMTP_HOST, settings.SMTP_PORT, timeout=timeout
                )
                if settings.SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    server.starttls(context=context)

            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

            server.sendmail(settings.SMTP_SENDER_EMAIL, to_emails, msg.as_string())
            server.quit()

            logger.info(f"Email sent via SMTP to {to_emails}")
            return True
        except Exception as e:
            logger.error(f"SMTP send failed: {str(e)}")
            return False

    def send_verification_email(
        self,
        user_email: str,
        user_name: str,
        verification_token: str,
        base_url: Optional[str] = None,
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
        resolved_base_url = base_url or settings.FRONTEND_URL
        verification_url = f"{resolved_base_url}/verify-email?token={verification_token}"

        template = self.env.get_template("email_verification")
        html_content = template.render(
            user_name=user_name,
            user_email=user_email,
            verification_url=verification_url,
            project_name=settings.PROJECT_NAME,
        )

        subject = f"Verify Your Email - {settings.PROJECT_NAME}"

        return self._send_email(
            to_emails=[user_email], subject=subject, html_body=html_content
        )

    def send_password_reset_email(
        self,
        user_email: str,
        user_name: str,
        reset_token: str,
        base_url: Optional[str] = None,
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
        resolved_base_url = base_url or settings.FRONTEND_URL
        reset_url = f"{resolved_base_url}/reset-password?token={reset_token}"

        template = self.env.get_template("password_reset")
        html_content = template.render(
            user_name=user_name,
            user_email=user_email,
            reset_url=reset_url,
            project_name=settings.PROJECT_NAME,
        )

        subject = f"Reset Your Password - {settings.PROJECT_NAME}"

        return self._send_email(
            to_emails=[user_email], subject=subject, html_body=html_content
        )

    def send_welcome_email(
        self,
        user_email: str,
        user_name: str,
        dashboard_url: Optional[str] = None,
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
        resolved_dashboard_url = dashboard_url or f"{settings.FRONTEND_URL}/dashboard"

        template = self.env.get_template("welcome")
        html_content = template.render(
            user_name=user_name,
            user_email=user_email,
            dashboard_url=resolved_dashboard_url,
            project_name=settings.PROJECT_NAME,
        )

        subject = f"Welcome to {settings.PROJECT_NAME}!"

        return self._send_email(
            to_emails=[user_email], subject=subject, html_body=html_content
        )

    def send_notification_email(
        self,
        to_emails: List[str],
        subject: str,
        message: str,
        user_name: Optional[str] = None,
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
            to_emails=to_emails, subject=subject, html_body=html_content
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

    async def send_invitation_email(
        self,
        to_email: str,
        organization_name: str,
        inviter_name: str,
        invite_url: str,
        role: str,
        team_name: Optional[str] = None,
        temp_password: Optional[str] = None,
    ) -> bool:
        """
        Send organization invitation email with temporary password

        Args:
            to_email: Email address to send invitation to
            organization_name: Name of the organization
            inviter_name: Name of person sending invitation
            invite_url: URL to accept invitation
            role: User role (rep, manager, admin)
            team_name: Optional team name
            temp_password: Temporary password for initial login

        Returns:
            bool: True if email was sent successfully
        """
        template = self.env.get_template("invitation")
        html_content = template.render(
            user_email=to_email,
            organization_name=organization_name,
            inviter_name=inviter_name,
            invite_url=invite_url,
            role=role,
            team_name=team_name or "No team assigned",
            temp_password=temp_password,
            project_name=settings.PROJECT_NAME,
        )

        subject = (
            f"You're invited to join {organization_name} on {settings.PROJECT_NAME}"
        )

        return self._send_email(
            to_emails=[to_email], subject=subject, html_body=html_content
        )

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
                "max_24_hour_send": response["Max24HourSend"],
                "max_send_rate": response["MaxSendRate"],
                "sent_last_24_hours": response["SentLast24Hours"],
            }
        except ClientError as e:
            return {"error": str(e)}


# Global email service instance
email_service = EmailService()


def get_email_service() -> EmailService:
    """Get the global email service instance"""
    return email_service
