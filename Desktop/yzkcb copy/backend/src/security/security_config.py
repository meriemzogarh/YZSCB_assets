# src/security/security_config.py

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import os

def setup_security(app):
    """
    Configure security measures
    """
    
    # Rate limiting
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"]
    )
    
    # CORS - restrict to Yazaki domains only
    allowed_origins = os.getenv('ALLOWED_ORIGINS', 'http://localhost:3000').split(',')
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": allowed_origins,
                "methods": ["GET", "POST"],
                "allow_headers": ["Content-Type", "Authorization"],
                "max_age": 3600
            }
        }
    )
    
    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = "default-src 'self'"
        return response
    
    return limiter

def chat():
    # ... existing code
    pass