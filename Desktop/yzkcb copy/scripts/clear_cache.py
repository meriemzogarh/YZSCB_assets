"""
Script to clear all cache files from the project
"""
import os
import shutil
from pathlib import Path

def clear_cache():
    # Get project root directory
    project_root = Path(__file__).parent.parent.absolute()
    print(f"🧹 Clearing cache in: {project_root}")
    
    # 1. Clear Python cache (__pycache__)
    print("\n📦 Clearing Python cache...")
    for pycache in project_root.rglob("__pycache__"):
        try:
            shutil.rmtree(pycache)
            print(f"  ✓ Removed: {pycache}")
        except Exception as e:
            print(f"  ✗ Error removing {pycache}: {e}")

    # 2. Clear Hugging Face cache
    print("\n🤗 Clearing Hugging Face cache...")
    hf_cache = Path.home() / ".cache" / "huggingface"
    if hf_cache.exists():
        try:
            shutil.rmtree(hf_cache)
            print(f"  ✓ Removed: {hf_cache}")
        except Exception as e:
            print(f"  ✗ Error removing Hugging Face cache: {e}")
    
    # 3. Clear transformer cache
    print("\n🤖 Clearing Transformers cache...")
    transformers_cache = Path.home() / ".cache" / "torch" / "transformers"
    if transformers_cache.exists():
        try:
            shutil.rmtree(transformers_cache)
            print(f"  ✓ Removed: {transformers_cache}")
        except Exception as e:
            print(f"  ✗ Error removing Transformers cache: {e}")

    # 4. Clear sentence transformers cache
    print("\n📝 Clearing Sentence Transformers cache...")
    st_cache = Path.home() / ".cache" / "torch" / "sentence_transformers"
    if st_cache.exists():
        try:
            shutil.rmtree(st_cache)
            print(f"  ✓ Removed: {st_cache}")
        except Exception as e:
            print(f"  ✗ Error removing Sentence Transformers cache: {e}")

    print("\n✨ Cache clearing completed!")

if __name__ == "__main__":
    clear_cache()