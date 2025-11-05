"""
Flask REST API routes for the Yazaki Chatbot.

Provides endpoints for:
- POST /api/chat - synchronous chat responses
- POST /api/stream - server-sent events streaming  
- POST /api/init - database and system initialization
- GET /api/health - health check endpoint
"""

import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flask import Blueprint, request, jsonify, Response
from backend.services.chat_service import get_chat_service
from backend.db import get_db_manager, init_database

logger = logging.getLogger(__name__)

# Create blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/api')

@chat_bp.route('/chat', methods=['POST'])
def chat():
    """
    Handle synchronous chat requests.
    
    Expected JSON payload:
    {
        "session_id": "optional-session-id",
        "history": [{"role": "user|assistant", "content": "message"}],
        "message": "user message"
    }
    
    Returns:
    {
        "reply": "assistant response",
        "session_id": "session-identifier",
        "metadata": {...}
    }
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('message'):
            return jsonify({
                "error": "Missing required field: 'message'"
            }), 400
        
        message = data['message'].strip()
        if not message:
            return jsonify({
                "error": "Message cannot be empty"
            }), 400
        
        # Extract optional fields
        session_id = data.get('session_id')
        history = data.get('history', [])
        user_state = data.get('user_state', {})
        
        # Ensure user_state has form_completed for backward compatibility
        if 'form_completed' not in user_state:
            user_state['form_completed'] = True  # Default to true for API usage
        
        logger.info(f"Chat request - Session: {session_id[:8] if session_id else 'new'}, Message: {message[:50]}...")
        
        # Get chat service and process request
        chat_service = get_chat_service()
        response = chat_service.respond_sync(
            session_id=session_id,
            history=history,
            message=message,
            user_state=user_state
        )
        
        # Check for errors in response
        if 'error' in response:
            status_code = 500 if response.get('error') != 'Session validation failed' else 401
            return jsonify(response), status_code
        
        logger.info(f"Chat response - Session: {response['session_id'][:8]}, Success")
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

@chat_bp.route('/stream', methods=['POST'])
def stream_chat():
    """
    Handle streaming chat requests using Server-Sent Events.
    
    Expected JSON payload: same as /chat endpoint
    
    Returns: text/event-stream with chunks of response
    """
    try:
        # Validate request
        if not request.is_json:
            return jsonify({
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('message'):
            return jsonify({
                "error": "Missing required field: 'message'"
            }), 400
        
        message = data['message'].strip()
        if not message:
            return jsonify({
                "error": "Message cannot be empty"
            }), 400
        
        # Extract optional fields
        session_id = data.get('session_id')
        history = data.get('history', [])
        user_state = data.get('user_state', {})
        
        # Ensure user_state has form_completed for backward compatibility
        if 'form_completed' not in user_state:
            user_state['form_completed'] = True  # Default to true for API usage
        
        logger.info(f"Stream request - Session: {session_id[:8] if session_id else 'new'}, Message: {message[:50]}...")
        
        # Get chat service
        chat_service = get_chat_service()
        
        def generate_stream():
            """Generator function for streaming response."""
            try:
                for chunk_data in chat_service.stream_response_generator(
                    session_id=session_id,
                    history=history,
                    message=message,
                    user_state=user_state
                ):
                    # Format as Server-Sent Events
                    chunk_json = json.dumps(chunk_data)
                    yield f"data: {chunk_json}\n\n"
                    
                    # End stream if done
                    if chunk_data.get('done'):
                        yield "data: [DONE]\n\n"
                        break
                        
            except Exception as e:
                error_data = {
                    "error": str(e),
                    "session_id": session_id,
                    "done": True
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return Response(
            generate_stream(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Cache-Control'
            }
        )
        
    except Exception as e:
        logger.error(f"Error in stream endpoint: {e}", exc_info=True)
        return jsonify({
            "error": f"Internal server error: {str(e)}"
        }), 500

@chat_bp.route('/init', methods=['POST'])
def initialize_system():
    """
    Initialize database and vector store systems.
    
    Optional JSON payload:
    {
        "vector_store_name": "vector_store_json"
    }
    
    Returns:
    {
        "status": "ok|error",
        "details": {...}
    }
    """
    try:
        # Get vector store name from request or use default
        vector_store_name = 'vector_store_json'
        
        if request.is_json:
            data = request.get_json() or {}
            vector_store_name = data.get('vector_store_name', vector_store_name)
        
        logger.info(f"Initializing system with vector store: {vector_store_name}")
        
        # Initialize database
        success, health_status = init_database(vector_store_name)
        
        if success:
            logger.info("System initialization completed successfully")
            return jsonify({
                "status": "ok",
                "message": "System initialized successfully",
                "details": health_status
            }), 200
        else:
            logger.warning("System initialization completed with warnings")
            return jsonify({
                "status": "partial",
                "message": "System partially initialized",
                "details": health_status
            }), 200
            
    except Exception as e:
        logger.error(f"Error in init endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Initialization failed: {str(e)}",
            "details": {}
        }), 500

@chat_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for system status.
    
    Returns:
    {
        "status": "healthy|unhealthy|partial", 
        "timestamp": "iso-timestamp",
        "details": {...}
    }
    """
    try:
        db_manager = get_db_manager()
        health_status = db_manager.health_check()
        
        timestamp = datetime.now().isoformat()
        
        return jsonify({
            "status": health_status["overall"],
            "timestamp": timestamp,
            "details": health_status
        }), 200
        
    except Exception as e:
        logger.error(f"Error in health endpoint: {e}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@chat_bp.route('/models', methods=['GET'])
def list_models():
    """
    List available LLM models.
    
    Returns:
    {
        "models": [...],
        "current": "model-name"
    }
    """
    try:
        import subprocess
        
        # Get available Ollama models
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        models = []
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines[1:]:  # Skip header
                if line.strip():
                    model_name = line.split()[0]
                    models.append(model_name)
        
        # Get current model from db_manager
        db_manager = get_db_manager()
        llm_manager = db_manager.get_llm_manager()
        current_model = getattr(llm_manager, 'model_name', 'unknown') if llm_manager else 'unknown'
        
        return jsonify({
            "models": models or ['mistral:latest'],
            "current": current_model
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({
            "models": ['mistral:latest'],
            "current": "unknown",
            "error": str(e)
        }), 500

@chat_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session_info(session_id: str):
    """
    Get information about a specific session.
    
    Returns:
    {
        "session_id": "...",
        "active": true|false,
        "details": {...}
    }
    """
    try:
        chat_service = get_chat_service()
        
        if not chat_service.session_manager:
            return jsonify({
                "error": "Session management not available"
            }), 503
        
        is_active = chat_service.session_manager.is_session_active(session_id)
        
        # Try to get session details (this would need session_manager method)
        details = {}
        try:
            # This assumes session_manager has a get_session method
            session_data = getattr(chat_service.session_manager, 'get_session', lambda x: {})(session_id)
            details = session_data
        except:
            pass
        
        return jsonify({
            "session_id": session_id,
            "active": is_active,
            "details": details
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting session info: {e}")
        return jsonify({
            "error": str(e)
        }), 500


@chat_bp.route('/sessions', methods=['POST'])
def create_session():
    """
    Create a new session and persist user registration info.

    Expected JSON payload:
    {
        "user_info": { ... }    # Arbitrary user info collected from the frontend
    }

    Returns:
    {
        "session_id": "...",
        "created": true
    }
    """
    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json()
        user_info = data.get('user_info', {}) or {}

        chat_service = get_chat_service()
        if not chat_service or not chat_service.session_manager:
            return jsonify({"error": "Session management not available"}), 503

        # Generate a canonical session id
        session_id = str(uuid.uuid4())

        created = chat_service.session_manager.create_session(session_id, user_info)

        if not created:
            return jsonify({"error": "Failed to create session"}), 500

        return jsonify({"session_id": session_id, "created": True}), 201

    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@chat_bp.route('/sessions/<session_id>/close', methods=['POST'])
def close_session(session_id):
    """
    Close a session and optionally send summary email.
    
    Expected JSON payload:
    {
        "send_email": true  // Optional, defaults to true
    }
    """
    try:
        logger.info(f"Session close request for: {session_id[:8]}...")
        
        # Validate session ID format
        if not session_id or len(session_id) < 8:
            return jsonify({
                "error": "Invalid session ID format"
            }), 400
        
        # Parse request body
        data = request.get_json() if request.is_json else {}
        send_email = data.get('send_email', True)  # Default to sending email
        
        # Get session manager
        chat_service = get_chat_service()
        if not chat_service.session_manager:
            logger.warning("Session manager not available")
            return jsonify({
                "message": "Session closed successfully (no session manager available)",
                "email_sent": False
            }), 200
        
        # Check if session exists and is active
        if not chat_service.session_manager.is_session_active(session_id):
            logger.info(f"Session {session_id[:8]} already inactive")
            return jsonify({
                "message": "Session was already inactive",
                "email_sent": False
            }), 200
        
        # End the session
        logger.info(f"Ending session: {session_id[:8]}...")
        chat_service.session_manager.end_session(session_id)
        
        email_sent = False
        
        # Send summary email if requested
        if send_email:
            try:
                logger.info(f"Sending summary email for session: {session_id[:8]}...")
                email_sent = chat_service.session_manager.send_summary_email(session_id)
                
                if email_sent:
                    logger.info(f"✅ Summary email sent successfully for session: {session_id[:8]}")
                else:
                    logger.warning(f"⚠️ Failed to send summary email for session: {session_id[:8]}")
                    
            except Exception as email_error:
                logger.error(f"Error sending summary email: {email_error}")
                email_sent = False
        
        return jsonify({
            "message": "Session closed successfully",
            "session_id": session_id,
            "email_sent": email_sent
        }), 200
        
    except Exception as e:
        logger.error(f"Error closing session {session_id}: {e}", exc_info=True)
        return jsonify({
            "error": f"Failed to close session: {str(e)}"
        }), 500

# Error handlers
@chat_bp.errorhandler(404)
def not_found(error):
    return jsonify({
        "error": "Endpoint not found"
    }), 404

@chat_bp.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method not allowed"
    }), 405

@chat_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        "error": "Internal server error"
    }), 500