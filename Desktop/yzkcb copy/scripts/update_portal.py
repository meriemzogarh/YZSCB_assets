#!/usr/bin/env python3
"""
Robust JSON 'Supplier Portal' updater.

- Finds occurrences of "Supplier Portal" (case-insensitive) in keys and string values.
- Inserts " (EmpowerQLM)" immediately after 'Supplier Portal', keeping punctuation in place.
- Skips occurrences that already have "(EmpowerQLM)" nearby.
- Prints every match (file + JSON path + before -> after).
- Creates a .bak copy using shutil.copy2 before overwriting.
- Use dry_run=True to only show changes without modifying files.
"""

import os
import json
import re
import shutil
from typing import Any, List, Tuple

# Pattern finds "Supplier Portal", case-insensitive; captures trailing punctuation if any.
# Negative lookahead prevents matches already followed (within immediate whitespace) by (EmpowerQLM)
PORTAL_RE = re.compile(r'(?i)\bsupplier\s+portal\b(?!\s*\(EmpowerQLM\))(?P<punc>[\)\]\.,;:!?"\']*)')

def replace_portal_in_string(s: str) -> Tuple[str, bool]:
    """Return (new_string, changed_flag). Insert ' (EmpowerQLM)' after 'Supplier Portal', before punctuation."""
    def repl(m):
        punc = m.group('punc') or ''
        # m.group(0) includes punctuation as well; strip punctuation from that piece
        word = m.group(0)[:-len(punc)] if punc else m.group(0)
        return f"{word} (EmpowerQLM){punc}"
    new_s, n = PORTAL_RE.subn(repl, s)
    return new_s, n > 0

def traverse_and_update(obj: Any, path: str = "") -> Tuple[Any, List[Tuple[str, str, str]]]:
    """
    Recursively search object. Return (new_obj, list_of_changes)
    Each change is a tuple: (json_path, original_text, updated_text)
    """
    changes = []
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            # First, possibly update key if it's a string
            new_key = k
            if isinstance(k, str):
                updated_key, changed_key = replace_portal_in_string(k)
                if changed_key:
                    changes.append((f"{path}/{k} (key)", k, updated_key))
                    new_key = updated_key
            # Traverse value
            new_val, sub_changes = traverse_and_update(v, f"{path}/{new_key}")
            if sub_changes:
                changes.extend(sub_changes)
            new_dict[new_key] = new_val
        return new_dict, changes
    elif isinstance(obj, list):
        new_list = []
        for idx, item in enumerate(obj):
            new_item, sub_changes = traverse_and_update(item, f"{path}[{idx}]")
            if sub_changes:
                changes.extend(sub_changes)
            new_list.append(new_item)
        return new_list, changes
    elif isinstance(obj, str):
        updated, changed = replace_portal_in_string(obj)
        if changed:
            changes.append((path, obj, updated))
        return updated if changed else obj, changes
    else:
        return obj, []

def process_file(file_path: str, dry_run: bool = True) -> bool:
    """Process single JSON file. Returns True if changes were made."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Could not read {file_path}: {e}")
        return False

    updated_data, changes = traverse_and_update(data, path="")
    if not changes:
        print(f"— No 'Supplier Portal' occurrences to change in: {file_path}")
        return False

    print(f"\n=== Changes for {file_path} ===")
    for pth, before, after in changes:
        print(f"Path: {pth}\n  BEFORE: {before}\n  AFTER : {after}\n")

    if dry_run:
        print(f"(dry_run=True) Not writing changes to disk for {file_path}.\n")
        return True

    # Make backup copy
    bak = file_path + ".bak"
    try:
        shutil.copy2(file_path, bak)
        print(f"Backup saved to {bak}")
    except Exception as e:
        print(f"❌ Failed to create backup for {file_path}: {e}")
        return False

    # Write updated JSON (pretty printed with indent=2)
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)
        print(f"✅ Updated and wrote {file_path}\n")
        return True
    except Exception as e:
        print(f"❌ Failed to write updated JSON to {file_path}: {e}")
        # try to restore backup automatically
        try:
            shutil.copy2(bak, file_path)
            print(f"Restored original from {bak}")
        except Exception as re:
            print(f"Also failed to restore backup: {re}")
        return False

def process_path(path: str, dry_run: bool = True):
    """Process a single file or all .json files under a directory."""
    changed_any = False
    if os.path.isfile(path):
        if path.lower().endswith(".json"):
            changed_any |= process_file(path, dry_run=dry_run)
        else:
            print(f"Skipping non-json file: {path}")
    else:
        for root, _, files in os.walk(path):
            for fname in files:
                if fname.lower().endswith(".json"):
                    file_path = os.path.join(root, fname)
                    changed_any |= process_file(file_path, dry_run=dry_run)
    if not changed_any:
        print("\nNo files were changed (or no matches found).")
    else:
        print("\nDone. Some files had replacements (see above).")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Insert (EmpowerQLM) after 'Supplier Portal' in JSON files.")
    ap.add_argument("path", help="File or directory to process")
    ap.add_argument("--apply", action="store_true", help="Actually write changes (default is dry run).")
    args = ap.parse_args()

    process_path(args.path, dry_run=not args.apply)
