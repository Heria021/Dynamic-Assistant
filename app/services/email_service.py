import pickle
import os
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.text import MIMEText
import base64
from typing import Optional
from fastapi import HTTPException


class EmailService:
    """Gmail API service for sending emails"""

    def __init__(self, credentials_file: str = "credentials.json", token_file: str = "token.pickle"):
        """
        Initialize Gmail service
        
        Args:
            credentials_file: Path to OAuth credentials JSON file
            token_file: Path to store/read OAuth token
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None

        # Check if token exists
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                creds = pickle.load(token)

        # If no valid credentials, request new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.SCOPES)
                creds = flow.run_local_server(port=0)

            # Save token for future use
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)

        return build('gmail', 'v1', credentials=creds)

    def _create_message(self, to_email: str, subject: str, message_text: str) -> dict:
        """Create email message"""
        message = MIMEText(message_text, 'html')
        message['to'] = to_email
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        return {'raw': raw_message}

    def send_email(self, to_email: str, subject: str, message_text: str) -> bool:
        """
        Send email via Gmail API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            message_text: Email body (HTML supported)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            message = self._create_message(to_email, subject, message_text)
            send_message = self.service.users().messages().send(userId='me', body=message).execute()
            print(f'Email sent successfully to {to_email}. Message ID: {send_message["id"]}')
            return True
        except HttpError as error:
            print(f'An error occurred while sending email: {error}')
            raise HTTPException(status_code=500, detail=f"Failed to send email: {str(error)}")
        except Exception as error:
            print(f'An unexpected error occurred: {error}')
            raise HTTPException(status_code=500, detail=f"Email service error: {str(error)}")

    def send_verification_email(self, to_email: str, verification_code: str) -> bool:
        """Send email verification code"""
        subject = "Verify Your Email - Authentication Code"
        message_text = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; text-align: center;">Email Verification</h2>
                    <p>Hello,</p>
                    <p>Thank you for signing up! To complete your registration, please verify your email address using the code below:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; letter-spacing: 5px; font-size: 24px; margin: 0;">
                            {verification_code}
                        </h3>
                    </div>
                    
                    <p><strong>This code expires in 24 hours.</strong></p>
                    <p>If you didn't sign up for this account, you can safely ignore this email.</p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        return self.send_email(to_email, subject, message_text)

    def send_password_reset_email(self, to_email: str, reset_code: str) -> bool:
        """Send password reset code"""
        subject = "Reset Your Password - Authentication Code"
        message_text = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; text-align: center;">Password Reset Request</h2>
                    <p>Hello,</p>
                    <p>We received a request to reset your password. Use the code below to reset your password:</p>
                    
                    <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-radius: 5px; margin: 20px 0;">
                        <h3 style="color: #2c3e50; letter-spacing: 5px; font-size: 24px; margin: 0;">
                            {reset_code}
                        </h3>
                    </div>
                    
                    <p><strong>This code expires in 1 hour.</strong></p>
                    <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">
                        This is an automated message, please do not reply to this email.
                    </p>
                </div>
            </body>
        </html>
        """
        return self.send_email(to_email, subject, message_text)

    def send_welcome_email(self, to_email: str, user_name: str = None) -> bool:
        """Send welcome email after email verification"""
        subject = "Welcome!"
        greeting = f"Welcome, {user_name}!" if user_name else "Welcome!"
        
        message_text = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; text-align: center;">{greeting}</h2>
                    <p>Your email has been successfully verified and your account is now active.</p>
                    <p>You can now log in and start using our platform.</p>
                    
                    <p style="text-align: center; margin-top: 30px;">
                        <a href="#" style="background-color: #3498db; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                            Go to Dashboard
                        </a>
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">
                        If you have any questions, please contact our support team.
                    </p>
                </div>
            </body>
        </html>
        """
        return self.send_email(to_email, subject, message_text)

    def send_password_reset_confirmation_email(self, to_email: str, user_name: str = None) -> bool:
        """Send confirmation email after successful password reset"""
        subject = "Password Successfully Reset"
        greeting = f"Hello, {user_name}!" if user_name else "Hello!"
        
        message_text = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                    <h2 style="color: #2c3e50; text-align: center;">Password Reset Successful</h2>
                    <p>{greeting}</p>
                    <p>Your password has been successfully reset. You can now log in with your new password.</p>
                    
                    <p style="background-color: #e8f5e9; padding: 10px; border-left: 4px solid #4caf50; margin: 20px 0;">
                        <strong>💡 Tip:</strong> For security purposes, make sure to use a strong, unique password.
                    </p>
                    
                    <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 30px 0;">
                    <p style="font-size: 12px; color: #999;">
                        If you didn't reset your password, please contact support immediately.
                    </p>
                </div>
            </body>
        </html>
        """
        return self.send_email(to_email, subject, message_text)
