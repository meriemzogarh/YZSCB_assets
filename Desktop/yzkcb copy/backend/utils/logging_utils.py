"""
Centralized logging utilities for the Yazaki Chatbot backend.

Provides:
- Conversation logging to JSON files 
- Structured log message formatting
- Integration with MongoDB for chat history
- Query logging capabilities
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure logs directory exists
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

CHATBOT_LOG_FILE = LOGS_DIR / "chatbot.jsonl"
QUERIES_LOG_FILE = LOGS_DIR / "queries.jsonl"

logger = logging.getLogger(__name__)

def log_message(
    session_id: str,
    user_message: str, 
    assistant_message: str,
    metadata: Optional[Dict[str, Any]] = None,
    user_state: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Log a conversation message to the chatbot.jsonl file.
    
    Args:
        session_id: Unique session identifier
        user_message: User's input message
        assistant_message: Assistant's response
        metadata: Optional metadata (sources, response time, etc.)
        user_state: Optional user information from session
        
    Returns:
        bool: True if logging successful, False otherwise
    """
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "metadata": metadata or {},
            "user_info": _extract_user_info(user_state)
        }
        
        # Write to JSON Lines format
        with open(CHATBOT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        logger.debug(f"💬 Conversation logged for session: {session_id[:8]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging conversation: {e}")
        return False

def log_query(
    query: str,
    session_id: str,
    response_time: float,
    num_results: int,
    success: bool = True,
    error: Optional[str] = None
) -> bool:
    """
    Log a query to the queries.jsonl file.
    
    Args:
        query: The search/query string
        session_id: Session identifier
        response_time: Time taken to process query
        num_results: Number of results returned
        success: Whether query was successful
        error: Error message if query failed
        
    Returns:
        bool: True if logging successful
    """
    try:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "query": query,
            "response_time_seconds": response_time,
            "num_results": num_results,
            "success": success,
            "error": error
        }
        
        with open(QUERIES_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error logging query: {e}")
        return False

def save_conversation_to_mongodb(
    session_id: str,
    user_message: str, 
    assistant_message: str,
    conversations_collection,
    metadata: Optional[Dict[str, Any]] = None,
    user_state: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save conversation to MongoDB conversations collection.
    
    Args:
        session_id: Session identifier
        user_message: User's message
        assistant_message: Assistant's response
        conversations_collection: MongoDB collection for conversations
        metadata: Optional metadata
        user_state: Optional user session state
        
    Returns:
        bool: True if save successful
    """
    try:
        if conversations_collection is None:
            logger.debug("MongoDB conversations collection not available, skipping save")
            return False

        conversation_data = {
            "session_id": session_id,
            "timestamp": datetime.now(),
            "user_message": user_message,
            "assistant_message": assistant_message,
            "metadata": metadata or {},
            "user_info": _extract_user_info(user_state)
        }

        result = conversations_collection.insert_one(conversation_data)
        logger.debug(f"💬 Conversation saved to MongoDB (Session: {session_id[:8]}...)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error saving conversation to MongoDB: {e}")
        return False

def _extract_user_info(user_state: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    Extract user information from session state.
    
    Args:
        user_state: User session state dictionary
        
    Returns:
        Dictionary with user information fields
    """
    if not user_state:
        return {
            "full_name": "",
            "company_name": "", 
            "project_name": ""
        }
    
    return {
        "full_name": user_state.get("full_name", ""),
        "company_name": user_state.get("company_name", ""),
        "project_name": user_state.get("project_name", ""),
        "email": user_state.get("email", ""),
        "supplier_type": user_state.get("supplier_type", ""),
        "city": user_state.get("city", ""),
        "country": user_state.get("country", "")
    }

def get_recent_logs(limit: int = 100, session_id: Optional[str] = None) -> list:
    """
    Retrieve recent conversation logs.
    
    Args:
        limit: Maximum number of logs to retrieve
        session_id: Optional session ID to filter by
        
    Returns:
        List of log entries
    """
    try:
        logs = []
        
        if not CHATBOT_LOG_FILE.exists():
            return logs
        
        with open(CHATBOT_LOG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        log_entry = json.loads(line)
                        if session_id is None or log_entry.get("session_id") == session_id:
                            logs.append(log_entry)
                    except json.JSONDecodeError:
                        continue
        
        # Return most recent first
        return logs[-limit:] if limit > 0 else logs
        
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return []

def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration for the backend.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Configured logger instance
    """
    # Setup main logger
    main_logger = logging.getLogger("yazaki_chatbot")
    main_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Avoid duplicate handlers
    if main_logger.handlers:
        return main_logger
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler for errors
    error_handler = logging.FileHandler(LOGS_DIR / "chatbot_errors.log")
    error_handler.setLevel(logging.ERROR)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    error_handler.setFormatter(formatter)
    
    main_logger.addHandler(console_handler)
    main_logger.addHandler(error_handler)
    
    return main_logger