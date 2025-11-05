"""
Email Configuration for Session Manager

Centralized email settings and customization options
"""

import os

class EmailConfig:
    """Email configuration settings"""
    
    # SMTP Settings
    SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
    SMTP_USER = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
    
    # Email addresses
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '')
    FROM_EMAIL = os.getenv('FROM_EMAIL', SMTP_USER)
    
    # Email content settings
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Yazaki')
    SYSTEM_NAME = os.getenv('SYSTEM_NAME', 'Yazaki Chatbot System')
    
    # Debug settings
    MAIL_DEBUG = os.getenv('MAIL_DEBUG', 'false').lower() == 'true'
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if email is properly configured"""
        return bool(cls.SMTP_USER and cls.ADMIN_EMAIL)
    
    @classmethod
    def get_subject_template(cls, user_name: str = "Unknown User") -> str:
        """Get email subject template"""
        return f"{cls.SYSTEM_NAME} - Session Summary - {user_name}"