"""
Session Manager - Handles session lifecycle, timeouts, and cleanup

Features:
- Session creation and tracking
- Inactivity timeout monitoring
- Automatic session expiration
- Email notifications for ended sessions
- MongoDB integration for persistence
"""

import os
import time
import threading
import smtplib
import socket
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from .email_templates import build_session_summary_html

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages chatbot sessions with automatic timeout and cleanup
    
    Sessions are stored in MongoDB and monitored for inactivity.
    Inactive sessions are automatically ended and summary emails are sent.
    """
    
    def __init__(self, mongodb_uri: str, db_name: str):
        """
        Initialize the session manager
        
        Args:
            mongodb_uri: MongoDB connection string
            db_name: Database name
        """
        self.mongodb_uri = mongodb_uri
        self.db_name = db_name
        self.client = None
        self.db = None
        self.sessions_collection = None
        self.conversations_collection = None
        self.monitor_thread = None
        self.running = False
        
        # Configuration from environment variables
        self.INACTIVITY_TIMEOUT_MINUTES = int(os.getenv('SESSION_TIMEOUT_MINUTES', '2'))
        self.MONITOR_INTERVAL_SECONDS = int(os.getenv('SESSION_MONITOR_INTERVAL_SECONDS', '30'))
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.admin_email = os.getenv('ADMIN_EMAIL', '')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        
        logger.info("Session Manager initialized")
    
    def connect(self) -> bool:
        """
        Connect to MongoDB
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.client = MongoClient(self.mongodb_uri, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client[self.db_name]
            self.sessions_collection = self.db['sessions']
            self.conversations_collection = self.db['conversations']
            
            # Create indexes for efficient queries
            self.sessions_collection.create_index([("session_id", 1)], unique=True)
            self.sessions_collection.create_index([("status", 1), ("last_activity", 1)])
            
            logger.info(f"✅ Session Manager connected to MongoDB: {self.db_name}")
            return True
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Error connecting to MongoDB: {e}")
            return False
    
    def create_session(self, session_id: str, user_info: Dict) -> bool:
        """
        Create a new session in the database
        
        Args:
            session_id: Unique session identifier
            user_info: Dictionary containing user information
            
        Returns:
            bool: True if session created successfully
        """
        try:
            session_data = {
                "session_id": session_id,
                "user_info": user_info,
                "status": "active",
                "created_at": datetime.now(),
                "last_activity": datetime.now(),
                "message_count": 0,
                "ended_at": None,
                "processing": False  # Track if currently processing a message
            }
            
            self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": session_data},
                upsert=True
            )
            
            logger.info(f"📝 Session created: {session_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"❌ Error creating session: {e}")
            return False
    
    def is_session_active(self, session_id: str) -> bool:
        """
        Check if a session is currently active
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if session exists and is active
        """
        try:
            session = self.sessions_collection.find_one({
                "session_id": session_id,
                "status": "active"
            })
            return session is not None
        except Exception as e:
            logger.error(f"❌ Error checking session status: {e}")
            return False
    
    def update_activity(self, session_id: str, increment_count: bool = True) -> bool:
        """
        Update the last activity timestamp for a session
        
        Args:
            session_id: Session identifier
            increment_count: Whether to increment message count (default True)
            
        Returns:
            bool: True if update successful
        """
        try:
            update_fields = {"$set": {"last_activity": datetime.now()}}
            if increment_count:
                update_fields["$inc"] = {"message_count": 1}
                # Set processing to False when completing a message
                update_fields["$set"]["processing"] = False
            else:
                # Set processing to True when starting a message
                update_fields["$set"]["processing"] = True
            
            result = self.sessions_collection.update_one(
                {"session_id": session_id, "status": "active"},
                update_fields
            )
            
            if result.modified_count > 0:
                logger.debug(f"🔄 Activity updated for session: {session_id[:8]}...")
                return True
            else:
                logger.warning(f"⚠️ Failed to update activity - session may be inactive: {session_id[:8]}...")
            return False
        except Exception as e:
            logger.error(f"❌ Error updating activity: {e}")
            return False
    
    def find_inactive_sessions(self) -> List[Dict]:
        """
        Find all active sessions that have exceeded the inactivity timeout
        Excludes sessions that are currently processing a message
        
        Returns:
            List of inactive session documents
        """
        try:
            timeout_threshold = datetime.now() - timedelta(minutes=self.INACTIVITY_TIMEOUT_MINUTES)
            
            # Find sessions that are:
            # 1. Active status
            # 2. Last activity older than threshold
            # 3. NOT currently processing (to avoid ending sessions mid-conversation)
            inactive_sessions = list(self.sessions_collection.find({
                "status": "active",
                "last_activity": {"$lt": timeout_threshold},
                "$or": [
                    {"processing": {"$exists": False}},  # Backward compatibility
                    {"processing": False}  # Not currently processing
                ]
            }))
            
            if inactive_sessions:
                logger.info(f"⏰ Found {len(inactive_sessions)} inactive session(s)")
            
            return inactive_sessions
        except Exception as e:
            logger.error(f"❌ Error finding inactive sessions: {e}")
            return []
    
    def end_session(self, session_id: str) -> bool:
        """
        Mark a session as ended
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if session ended successfully
        """
        try:
            result = self.sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "ended",
                        "ended_at": datetime.now()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"🔚 Session ended: {session_id[:8]}...")
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Error ending session: {e}")
            return False
    
    def get_session_conversations(self, session_id: str) -> List[Dict]:
        """
        Retrieve all conversations for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of conversation documents
        """
        try:
            conversations = list(self.conversations_collection.find(
                {"session_id": session_id}
            ).sort("timestamp", 1))
            
            return conversations
        except Exception as e:
            logger.error(f"❌ Error retrieving conversations: {e}")
            return []
    
    def send_summary_email(self, session_id: str) -> bool:
        """
        Send a summary email for an ended session
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            logger.info(f"📧 Starting email summary for session: {session_id[:8]}...")
            
            # Check if email is configured
            if not self.smtp_user or not self.admin_email:
                logger.warning(f"❌ Email not configured!")
                logger.warning(f"   SMTP_USER: {'SET' if self.smtp_user else 'MISSING'}")
                logger.warning(f"   ADMIN_EMAIL: {'SET' if self.admin_email else 'MISSING'}")
                return False
            
            logger.info(f"✓ Email configuration verified")
            logger.info(f"   Sending to: {self.admin_email}")
            
            # Get session data
            session = self.sessions_collection.find_one({"session_id": session_id})
            if not session:
                logger.error(f"❌ Session not found in database: {session_id}")
                return False
            
            logger.info(f"✓ Session data retrieved from database")
            
            # Get conversations
            conversations = self.get_session_conversations(session_id)
            logger.info(f"✓ Retrieved {len(conversations)} conversation(s)")
            
            # Build email content
            logger.info(f"📝 Building email HTML content...")
            email_html = self._build_email_html(session, conversations)
            
            # Send email
            logger.info(f"📮 Sending email via SMTP...")
            success = self._send_email(
                to_email=self.admin_email,
                subject=f"Session Summary - {session['user_info'].get('full_name', 'Unknown User')}",
                html_content=email_html
            )
            
            if success:
                logger.info(f"✅ Summary email sent successfully for session: {session_id[:8]}...")
            else:
                logger.error(f"❌ Failed to send email for session: {session_id[:8]}...")
            
            return success
        except Exception as e:
            logger.error(f"❌ Error sending summary email: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def _build_email_html(self, session: Dict, conversations: List[Dict]) -> str:
        """
        Build HTML content for summary email using external template
        
        Args:
            session: Session document
            conversations: List of conversation documents
            
        Returns:
            HTML string
        """
        return build_session_summary_html(session, conversations)
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Send an email via SMTP
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            
        Returns:
            bool: True if email sent successfully
        """
        try:
            logger.info("📬 Preparing email message...")
            logger.info(f"   From: {self.from_email}")
            logger.info(f"   To: {to_email}")
            logger.info(f"   Subject: {subject}")
            logger.info(f"   SMTP Server: {self.smtp_host}:{self.smtp_port}")
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email

            # Optional debug: print email body when MAIL_DEBUG=true
            if os.getenv('MAIL_DEBUG', 'false').lower() == 'true':
                try:
                    logger.info('--- MAIL_DEBUG: email HTML content start ---')
                    logger.info(html_content)
                    logger.info('--- MAIL_DEBUG: email HTML content end ---')
                except Exception:
                    logger.warning('Could not log html content for MAIL_DEBUG')

            # Attach HTML content
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            logger.info(f"✓ Email message created (size: {len(html_content)} bytes)")
            
            # Send via SMTP
            logger.info(f"🔌 Connecting to SMTP server {self.smtp_host}:{self.smtp_port}...")
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                logger.info("✓ SMTP connection established")
                
                logger.info("🔐 Initiating TLS encryption...")
                server.starttls()
                logger.info("✓ TLS encryption enabled")
                
                logger.info(f"🔑 Authenticating as {self.smtp_user}...")
                server.login(self.smtp_user, self.smtp_password)
                logger.info("✓ SMTP authentication successful")
                
                logger.info("📤 Sending email message...")
                server.send_message(msg)
                logger.info("✓ Email message sent to SMTP server")
            
            logger.info(f"✅ Email sent successfully to {to_email}")
            return True
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"❌ SMTP Authentication failed: {e}")
            logger.error(f"   Check SMTP_USER and SMTP_PASSWORD in .env file")
            return False
        except smtplib.SMTPConnectError as e:
            logger.error(f"❌ Failed to connect to SMTP server: {e}")
            logger.error(f"   Check SMTP_HOST and SMTP_PORT in .env file")
            return False
        except socket.gaierror as e:
            # DNS resolution / network error when trying to connect to SMTP server
            logger.error(f"❌ DNS / network error resolving SMTP host {self.smtp_host}:{self.smtp_port}: {e}")
            logger.error("   Suggested checks: - Verify SMTP_HOST is correct; - Ensure this machine has network/DNS access; - Try 'nslookup smtp.gmail.com' or 'dig smtp.gmail.com' from this host.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"❌ SMTP error occurred: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending email: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def monitor_sessions(self):
        """
        Background job that monitors sessions for inactivity
        
        This function runs in a separate thread and checks for inactive
        sessions every minute. When found, it ends them and sends summary emails.
        """
        logger.info("🔍 Session monitor started")
        logger.info(f"   Checking every {self.MONITOR_INTERVAL_SECONDS} seconds")
        logger.info(f"   Timeout threshold: {self.INACTIVITY_TIMEOUT_MINUTES} minutes")
        logger.info(f"   Email notifications: {'ENABLED' if self.smtp_user and self.admin_email else 'DISABLED'}")
        
        while self.running:
            try:
                # Find inactive sessions
                logger.debug(f"🔍 Checking for inactive sessions...")
                inactive_sessions = self.find_inactive_sessions()
                
                if inactive_sessions:
                    logger.info(f"⏰ Found {len(inactive_sessions)} inactive session(s)")
                    logger.info("=" * 70)
                else:
                    logger.debug(f"✓ No inactive sessions found")
                
                # Process each inactive session
                for session in inactive_sessions:
                    session_id = session['session_id']
                    user_name = session.get('user_info', {}).get('full_name', 'Unknown')
                    user_email = session.get('user_info', {}).get('email', 'N/A')
                    message_count = session.get('message_count', 0)
                    
                    logger.info(f"� Processing Inactive Session:")
                    logger.info(f"   Session ID: {session_id[:8]}...")
                    logger.info(f"   User: {user_name} ({user_email})")
                    logger.info(f"   Messages exchanged: {message_count}")
                    logger.info(f"   Last activity: {session.get('last_activity')}")
                    
                    # End the session
                    logger.info(f"🔚 Ending session: {session_id[:8]}...")
                    if self.end_session(session_id):
                        logger.info(f"✅ Session ended successfully: {session_id[:8]}...")
                        
                        # Send summary email
                        if self.smtp_user and self.admin_email:
                            logger.info(f"📧 Triggering email notification for session: {session_id[:8]}...")
                            email_success = self.send_summary_email(session_id)
                            
                            if email_success:
                                logger.info(f"✅ Email notification sent for session: {session_id[:8]}...")
                            else:
                                logger.error(f"❌ Email notification failed for session: {session_id[:8]}...")
                        else:
                            logger.warning(f"⚠️ Email notifications disabled - skipping email for session: {session_id[:8]}...")
                            logger.warning(f"   Configure SMTP_USER and ADMIN_EMAIL in .env to enable")
                    else:
                        logger.warning(f"⚠️ Failed to end session: {session_id[:8]}...")
                    
                    logger.info("-" * 70)
                
                if inactive_sessions:
                    logger.info("=" * 70)
                
                # Sleep for the monitor interval
                time.sleep(self.MONITOR_INTERVAL_SECONDS)
            except Exception as e:
                logger.error(f"❌ Error in session monitor: {e}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(self.MONITOR_INTERVAL_SECONDS)
        
        logger.info("🛑 Session monitor stopped")
    
    def start_monitor(self):
        """
        Start the background session monitoring thread
        """
        if not self.running:
            self.running = True
            self.monitor_thread = threading.Thread(
                target=self.monitor_sessions,
                daemon=True,
                name="SessionMonitor"
            )
            self.monitor_thread.start()
            logger.info(f"✅ Session monitor started (checking every {self.MONITOR_INTERVAL_SECONDS}s)")
            logger.info(f"⏰ Inactivity timeout: {self.INACTIVITY_TIMEOUT_MINUTES} minutes")
    
    def stop_monitor(self):
        """
        Stop the background session monitoring thread
        """
        if self.running:
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join(timeout=5)
            logger.info("🛑 Session monitor stopped")
    
    def close(self):
        """
        Close connections and cleanup
        """
        self.stop_monitor()
        if self.client:
            self.client.close()
            logger.info("👋 Session Manager closed")
    
    def get_session_stats(self) -> Dict:
        """
        Get statistics about sessions
        
        Returns:
            Dictionary with session statistics
        """
        try:
            total = self.sessions_collection.count_documents({})
            active = self.sessions_collection.count_documents({"status": "active"})
            ended = self.sessions_collection.count_documents({"status": "ended"})
            
            return {
                "total": total,
                "active": active,
                "ended": ended
            }
        except Exception as e:
            logger.error(f"❌ Error getting session stats: {e}")
            return {"total": 0, "active": 0, "ended": 0}


# Global session manager instance
_session_manager = None

def get_session_manager(mongodb_uri: str = None, db_name: str = None) -> SessionManager:
    """
    Get or create the global session manager instance
    
    Args:
        mongodb_uri: MongoDB connection string
        db_name: Database name
        
    Returns:
        SessionManager instance
    """
    global _session_manager
    
    if _session_manager is None:
        uri = mongodb_uri or os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
        db = db_name or os.getenv('MONGODB_DB', 'yazaki_chatbot')
        _session_manager = SessionManager(uri, db)
        _session_manager.connect()
    
    return _session_manager
