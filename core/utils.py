import os
import time
import shutil

def safe_atomic_replace(src: str, dst: str, max_retries: int = 5, backoff_factor: float = 0.5) -> bool:
    """
    Safely moves src to dst. On Windows, os.replace can fail with WinError 5 
    if a background process briefly locks the file. This handles retries with backoff 
    and uses shutil.move as a fallback.
    """
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source file not found: {src}")

    for attempt in range(max_retries):
        try:
            os.replace(src, dst)
            return True
        except PermissionError:
            time.sleep(backoff_factor * (2 ** attempt))
            
    # Fallback to shutil.move if os.replace fails entirely (e.g. across drives)
    try:
        if os.path.exists(dst):
            os.remove(dst) # shutil.move might fail if destination exists
        shutil.move(src, dst)
        return True
    except Exception as e:
        print(f"[AtomicReplace] Failed to move {src} to {dst}: {e}")
        return False

import json

def save_learning_history(channel_name: str, issue: str):
    history_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", f"learning_history_{channel_name}.json"
    )
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    
    from datetime import datetime
    entry = {"date": datetime.now().isoformat(), "issue": issue}
    history.insert(0, entry)
    history = history[:5]
    
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

def get_learning_history(channel_name: str) -> list:
    history_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config", f"learning_history_{channel_name}.json"
    )
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


import re
import unicodedata

def title_to_snake_case(title: str, max_length: int = 64) -> str:
    """
    Converts a video title into a clean, filesystem-safe snake_case string.
    Example: "Silicon Chips vs Quantum Doom!" -> "silicon_chips_vs_quantum_doom"
    """
    if not title or not isinstance(title, str):
        return "short_video"
    
    # Normalize unicode to decompose accents (e.g., é -> e)
    normalized = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    # Lowercase
    clean = normalized.lower()
    # Replace non-alphanumeric chars with underscores
    clean = re.sub(r"[^a-z0-9]+", "_", clean)
    # Collapse multiple consecutive underscores and strip ends
    clean = re.sub(r"_+", "_", clean).strip("_")
    
    if not clean:
        return "short_video"
    
    # Truncate to max_length avoiding dangling trailing underscores
    truncated = clean[:max_length].rstrip("_")
    return truncated if truncated else "short_video"

