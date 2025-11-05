"""
Main application entry point that launches both frontend and backend.
"""
import os
import sys
from pathlib import Path

# Add repository root to Python path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def launch_app(server_name: str = "localhost", server_port: int = 7861, share: bool = False):
    """Launch the complete application"""
    try:
        # Import and initialize backend
        from backend.api import ChatBackend
        backend = ChatBackend()
        print("✅ Backend initialized successfully")
        
        # Import and launch frontend
        from frontend.gradio_app import launch
        print("🚀 Launching frontend interface...")
        launch(server_name=server_name, server_port=server_port, share=share)
        
    except Exception as e:
        print(f"❌ Error launching application: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    launch_app()