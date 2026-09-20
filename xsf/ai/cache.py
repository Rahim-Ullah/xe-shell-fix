"""
xsf.ai.cache - Local query cache to prevent redundant API or LLM calls.
"""
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Dict, Optional

CACHE_FILE = Path.home() / ".shellfix" / "ai_cache.json"


def make_key(raw_command: str, stderr_text: str, shell: str) -> str:
    """Generates a SHA256 cache key from command, normalized stderr, and shell."""
    # First 500 chars of stderr is usually sufficient for context identification
    norm_err = (stderr_text or "").strip()[:500]
    payload = f"{shell}|{raw_command.strip()}|{norm_err}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class AICache:
    _cache: Dict[str, Dict[str, Any]] = {}
    _loaded: bool = False

    @classmethod
    def load(cls) -> None:
        if cls._loaded:
            return
        if CACHE_FILE.exists():
            try:
                cls._cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                cls._cache = {}
        cls._loaded = True

    @classmethod
    def save(cls) -> None:
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(cls._cache, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def get(cls, key: str) -> Optional[Dict[str, Any]]:
        cls.load()
        entry = cls._cache.get(key)
        if not entry:
            return None
        # Cache entries valid for 7 days
        if time.time() - entry.get("timestamp", 0) > 7 * 86400:
            del cls._cache[key]
            cls.save()
            return None
        return entry

    @classmethod
    def put(cls, key: str, fixed_command: str, explanation: str, confidence: float) -> None:
        cls.load()
        cls._cache[key] = {
            "command": fixed_command,
            "explanation": explanation,
            "confidence": confidence,
            "timestamp": int(time.time()),
        }
        cls.save()
