# src/security/privacy.py

from datetime import datetime, timedelta
from pathlib import Path
import json
import os

class DataPrivacyManager:
    """
    Manage data retention and privacy
    """
    
    def __init__(self, retention_days: int = 30):
        self.retention_days = retention_days
    
    def cleanup_old_data(self, log_dir: str = "logs"):
        """
        Delete logs older than retention period
        GDPR/privacy compliance
        """
        
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        
        for log_file in Path(log_dir).glob("*.jsonl"):
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
            
            if file_time < cutoff:
                log_file.unlink()
                print(f"Deleted: {log_file}")
    
    def anonymize_query(self, query: str) -> str:
        """
        Anonymize sensitive data in queries
        """
        import re
        
        # Remove email addresses
        query = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', query)
        
        # Remove phone numbers
        query = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', query)
        
        # Remove IP addresses
        query = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]', query)
        
        return query
    
    def should_log_query(self, query: str) -> bool:
        """
        Determine if query should be logged
        (avoid logging sensitive information)
        """
        
        sensitive_keywords = ['password', 'token', 'secret', 'api_key']
        query_lower = query.lower()
        
        return not any(kw in query_lower for kw in sensitive_keywords)