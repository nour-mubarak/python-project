#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Notifications Module
====================

Email notifications for LinguaEval.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Email notification service."""

    def __init__(
        self,
        smtp_host: str = None,
        smtp_port: int = None,
        smtp_user: str = None,
        smtp_password: str = None,
        from_email: str = None,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
        self.smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD", "")
        self.from_email = from_email or os.environ.get("SMTP_FROM", self.smtp_user)
        self.use_tls = use_tls

    @property
    def is_configured(self) -> bool:
        """Check if email is properly configured."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def send_email(
        self,
        to: str,
        subject: str,
        body_html: str,
        body_text: str = None,
    ) -> bool:
        """
        Send an email.

        Returns True if successful, False otherwise.
        """
        if not self.is_configured:
            logger.warning("Email not configured - skipping notification")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to

            # Add text version
            if body_text:
                part1 = MIMEText(body_text, "plain")
                msg.attach(part1)

            # Add HTML version
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

            # Send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to, msg.as_string())

            logger.info(f"Email sent to {to}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_evaluation_complete(
        self,
        to: str,
        client_name: str,
        project_id: str,
        overall_score: float,
        status: str,
        dashboard_url: str = None,
    ):
        """Send evaluation completion notification."""
        subject = f"LinguaEval: Evaluation Complete - {client_name}"

        status_color = (
            "#22c55e"
            if status == "Ready for Pilot"
            else ("#f59e0b" if status == "Restricted Pilot Only" else "#ef4444")
        )

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .score {{ font-size: 48px; font-weight: bold; color: #2563eb; text-align: center; }}
                .status {{ padding: 10px 20px; background: {status_color}; color: white; 
                          display: inline-block; border-radius: 20px; font-weight: bold; }}
                .button {{ background: #2563eb; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Evaluation Complete</h1>
                </div>
                <div class="content">
                    <h2>Project: {client_name}</h2>
                    <p>Your multilingual AI evaluation has completed successfully.</p>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <div class="score">{overall_score:.1f}%</div>
                        <p>Overall Score</p>
                        <span class="status">{status}</span>
                    </div>
                    
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="{dashboard_url or '#'}" class="button">View Dashboard</a>
                    </p>
                    
                    <p><strong>Project ID:</strong> {project_id}</p>
                    <p><strong>Completed:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                <div class="footer">
                    <p>LinguaEval - Multilingual AI Evaluation Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
LinguaEval - Evaluation Complete

Project: {client_name}
Project ID: {project_id}
Overall Score: {overall_score:.1f}%
Status: {status}
Completed: {datetime.now().strftime('%Y-%m-%d %H:%M')}

View dashboard: {dashboard_url or 'N/A'}
        """

        return self.send_email(to, subject, body_html, body_text)

    def send_evaluation_failed(
        self,
        to: str,
        client_name: str,
        project_id: str,
        error_message: str,
    ):
        """Send evaluation failure notification."""
        subject = f"LinguaEval: Evaluation Failed - {client_name}"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #ef4444; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .error {{ background: #fef2f2; border: 1px solid #fee2e2; padding: 15px; 
                         border-radius: 5px; color: #991b1b; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>⚠️ Evaluation Failed</h1>
                </div>
                <div class="content">
                    <h2>Project: {client_name}</h2>
                    <p>Unfortunately, your evaluation encountered an error.</p>
                    
                    <div class="error">
                        <strong>Error:</strong><br>
                        {error_message}
                    </div>
                    
                    <p style="margin-top: 20px;">
                        <strong>Project ID:</strong> {project_id}<br>
                        <strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M')}
                    </p>
                    
                    <p>Please check your configuration and try again, or contact support.</p>
                </div>
                <div class="footer">
                    <p>LinguaEval - Multilingual AI Evaluation Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
LinguaEval - Evaluation Failed

Project: {client_name}
Project ID: {project_id}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Error: {error_message}

Please check your configuration and try again.
        """

        return self.send_email(to, subject, body_html, body_text)

    def send_welcome_email(self, to: str, username: str):
        """Send welcome email to new user."""
        subject = "Welcome to LinguaEval!"

        body_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 20px; background: #f9fafb; }}
                .button {{ background: #2563eb; color: white; padding: 12px 24px; 
                          text-decoration: none; border-radius: 5px; display: inline-block; }}
                .footer {{ text-align: center; padding: 20px; color: #6b7280; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to LinguaEval!</h1>
                </div>
                <div class="content">
                    <h2>Hello, {username}!</h2>
                    <p>Thank you for registering with LinguaEval, the comprehensive platform 
                       for evaluating multilingual AI systems.</p>
                    
                    <h3>Getting Started:</h3>
                    <ol>
                        <li>Create a new evaluation using the wizard</li>
                        <li>Select your prompt pack (Government, University, Healthcare, etc.)</li>
                        <li>Choose your models to evaluate</li>
                        <li>View results on the interactive dashboard</li>
                    </ol>
                    
                    <p style="text-align: center; margin: 30px 0;">
                        <a href="#" class="button">Go to Dashboard</a>
                    </p>
                </div>
                <div class="footer">
                    <p>LinguaEval - Multilingual AI Evaluation Platform</p>
                </div>
            </div>
        </body>
        </html>
        """

        body_text = f"""
Welcome to LinguaEval!

Hello, {username}!

Thank you for registering with LinguaEval, the comprehensive platform 
for evaluating multilingual AI systems.

Getting Started:
1. Create a new evaluation using the wizard
2. Select your prompt pack (Government, University, Healthcare, etc.)
3. Choose your models to evaluate
4. View results on the interactive dashboard
        """

        return self.send_email(to, subject, body_html, body_text)


# Global instance
notifier = EmailNotifier()
