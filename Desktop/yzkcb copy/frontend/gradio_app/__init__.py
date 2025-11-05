"""
Frontend launcher module that provides launch function
"""
import gradio as gr
from pathlib import Path
import sys

# Add the repository root to the Python path for imports
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

def launch(server_name: str = "localhost", server_port: int = 7861, share: bool = False):
    """Launch the Gradio interface."""
    from .enhanced_gradio import demo
    print("🚀 Launching Enhanced Gradio interface...")
    demo.launch(server_name=server_name, server_port=server_port, share=share)