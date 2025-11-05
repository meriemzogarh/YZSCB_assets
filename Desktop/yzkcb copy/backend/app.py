"""
Backend adapter entrypoint

This file provides a stable entrypoint for the backend grouped under `backend/`.
It imports your existing `src` package (which remains at repo root) and exposes a
simple `run()` function. When you finish migrating `src/` into `backend/src/`, update
imports accordingly.
"""
import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path so existing `src` imports continue to work.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Minimal run wrapper. You can extend this to start a FastAPI/Flask app.

def run_cli():
    """Run a simple check to ensure backend modules import correctly."""
    print("Starting backend adapter...\n")
    try:
        # Import session manager to verify backend imports
        from backend.src.session import session_manager as _sm  # type: ignore
        print("Imported src.session successfully")
    except Exception as e:
        print("Failed to import backend modules:", e)
        raise


if __name__ == "__main__":
    run_cli()
