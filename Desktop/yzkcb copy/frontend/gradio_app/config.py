"""
Frontend configuration module.
"""
from pathlib import Path

# Frontend paths
REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = REPO_ROOT / "assets"
AVATAR_PATH = ASSETS_DIR / "yazaki-avatar.png"