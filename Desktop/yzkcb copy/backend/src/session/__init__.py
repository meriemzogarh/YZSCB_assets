"""
Session management module for Yazaki Chatbot

Provides session lifecycle management, inactivity monitoring, 
and automated cleanup with email notifications.
"""

from .session_manager import SessionManager, get_session_manager

__all__ = ['SessionManager', 'get_session_manager']
