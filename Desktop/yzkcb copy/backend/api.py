"""
Flask application factory for the Yazaki Chatbot backend.

Creates and configures the Flask app with:
- CORS support
- Blueprint registration
- Static file serving
- Error handling
- Logging configuration
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

from config import get_config
from backend.utils.logging_utils import setup_logging
from backend.routes.chat import chat_bp
from backend.db import init_database

logger = logging.getLogger(__name__)

def create_app(config_name: str = None) -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        config_name: Configuration environment (development, production, testing)
        
    Returns:
        Configured Flask app instance
    """
    # Create Flask app
    app = Flask(__name__, 
                static_folder='../frontend_new',
                static_url_path='')
    
    # Load configuration
    config = get_config()
    
    # Configure Flask app
    app.config['SECRET_KEY'] = config.SECRET_KEY
    app.config['DEBUG'] = config.DEBUG
    
    # Setup logging
    log_level = "DEBUG" if config.DEBUG else "INFO"
    setup_logging(log_level)
    
    logger.info(f"Starting Yazaki Chatbot Backend (Debug: {config.DEBUG})")
    
    # Configure CORS
    cors_origins = os.getenv('CORS_ORIGINS', '*').split(',')
    CORS(app, 
         origins=cors_origins,
         allow_headers=['Content-Type', 'Authorization'],
         methods=['GET', 'POST', 'OPTIONS'])
    
    # Register blueprints
    app.register_blueprint(chat_bp, url_prefix='/api')
    
    # Static file serving routes
    @app.route('/')
    def serve_frontend():
        """Serve the main frontend page."""
        try:
            return send_from_directory(app.static_folder, 'index.html')
        except Exception as e:
            logger.warning(f"Could not serve frontend: {e}")
            return jsonify({
                "message": "Yazaki Chatbot Backend API",
                "version": "1.0.0",
                "endpoints": {
                    "chat": "/api/chat",
                    "stream": "/api/stream", 
                    "init": "/api/init",
                    "health": "/api/health",
                    "models": "/api/models"
                }
            }), 200
    
    @app.route('/favicon.ico')
    def favicon():
        """Serve favicon."""
        try:
            return send_from_directory(app.static_folder, 'favicon.ico')
        except:
            return '', 204
    
    @app.route('/css/<path:path>')
    def serve_css(path):
        """Serve CSS files."""
        return send_from_directory('../frontend_new/css', path)
    
    @app.route('/js/<path:path>')
    def serve_js(path):
        """Serve JavaScript files."""
        return send_from_directory('../frontend_new/js', path)
    
    @app.route('/assets/<path:path>')
    def serve_assets(path):
        """Serve asset files."""
        return send_from_directory('../frontend_new/assets', path)
    
    # API info endpoint
    @app.route('/api')
    def api_info():
        """API information endpoint."""
        return jsonify({
            "name": "Yazaki Chatbot API",
            "version": "1.0.0",
            "description": "REST API for Yazaki Supplier Quality Chatbot",
            "endpoints": {
                "POST /api/chat": "Synchronous chat responses",
                "POST /api/stream": "Streaming chat responses (SSE)",
                "POST /api/init": "Initialize database and vector store",
                "GET /api/health": "System health check",
                "GET /api/models": "List available LLM models",
                "GET /api/sessions/<id>": "Get session information"
            },
            "documentation": "See README.md for detailed usage"
        })
    
    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Not found",
            "message": "The requested resource was not found"
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }), 500
    
    @app.errorhandler(400)
    def bad_request_error(error):
        return jsonify({
            "error": "Bad request",
            "message": "The request could not be processed"
        }), 400
    
    # Health check for load balancers
    @app.route('/health')
    def simple_health():
        """Simple health check endpoint."""
        return jsonify({"status": "ok"}), 200
    
    # Initialize database on app creation (replaces deprecated before_first_request)
    def initialize_app():
        """Initialize application components."""
        try:
            logger.info("Initializing database and vector store...")
            success, health_status = init_database()
            
            if success:
                logger.info("✅ Application initialization completed successfully")
            else:
                logger.warning("⚠️ Application initialization completed with warnings")
                logger.warning(f"Health status: {health_status}")
                
        except Exception as e:
            logger.error(f"❌ Application initialization failed: {e}")
    
    # Call initialization immediately (since before_first_request is deprecated)
    with app.app_context():
        try:
            initialize_app()
        except Exception as e:
            logger.warning(f"Initialization during app creation failed: {e}")
    
    # Request logging middleware
    @app.before_request
    def log_request_info():
        """Log request information."""
        if app.debug:
            logger.debug(f"Request: {request.method} {request.path}")
    
    @app.after_request
    def log_response_info(response):
        """Log response information."""
        if app.debug:
            logger.debug(f"Response: {response.status_code}")
        return response
    
    return app

def run_app():
    """
    Run the Flask application.
    
    This function is used as the entry point for production deployment.
    """
    app = create_app()
    
    # Get configuration
    config = get_config()
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 8000))
    
    logger.info(f"Starting server on {host}:{port}")
    
    app.run(
        host=host,
        port=port,
        debug=config.DEBUG,
        threaded=True
    )

if __name__ == '__main__':
    run_app()