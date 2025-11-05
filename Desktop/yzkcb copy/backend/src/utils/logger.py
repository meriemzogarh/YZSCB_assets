# src/utils/logger.py

import logging
import json
from datetime import datetime
from pathlib import Path
from logging.handlers import RotatingFileHandler

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easier parsing"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)

def setup_logging(log_dir: str = "logs"):
    """
    Configure comprehensive logging
    """
    
    Path(log_dir).mkdir(exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers.clear()
    
    root_logger.setLevel(logging.DEBUG)
    
    # JSON file handler (for machine parsing)
    json_handler = RotatingFileHandler(
        f"{log_dir}/chatbot.jsonl",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    json_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(json_handler)
    
    # Text file handler (for human reading)
    text_handler = RotatingFileHandler(
        f"{log_dir}/chatbot.log",
        maxBytes=10*1024*1024,
        backupCount=5
    )
    text_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    text_handler.setFormatter(text_formatter)
    root_logger.addHandler(text_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(text_formatter)
    root_logger.addHandler(console_handler)
    
    # Query-specific logger
    query_logger = logging.getLogger("queries")
    query_file = RotatingFileHandler(
        f"{log_dir}/queries.jsonl",
        maxBytes=50*1024*1024,  # 50MB
        backupCount=10
    )
    query_file.setFormatter(JSONFormatter())
    query_logger.addHandler(query_file)
    
    return root_logger, query_logger

# Usage in app.py
logger, query_logger = setup_logging()