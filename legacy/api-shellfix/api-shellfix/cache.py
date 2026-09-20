"""
cache.py - a small local cache keyed by (command, error text, shell) so
typing the exact same broken command twice doesn't spend a second API call
against your free-tier quota. Plain JSON file, capped size, oldest entries
evicted first. Not shared between machines or users.
"""
import hashlib
import json
import time
from pathlib import Path

CACHE_FILE = Path.home() / ".shellfix" / "ai_cache.json"
MAX_ENTRIES = 500


def make_key(raw_command: str, stderr_text: str, shell: str) -> str:
    h = hashlib.sha256()
    h.update(raw_command.strip().encode("utf-8"))
    h.update(b"|")
    h.update(shell.encode("utf-8"))
    h.update(b"|")
    h.update(stderr_text[:500].encode("utf-8", errors="ignore"))
    return h.hexdigest()[:24]


def _load() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data: dict) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    if len(data) > MAX_ENTRIES:
        oldest = sorted(data.items(), key=lambda kv: kv[1].get("ts", 0))
        for k, _ in oldest[: len(data) - MAX_ENTRIES]:
            data.pop(k, None)
    try:
        CACHE_FILE.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


def get(key: str):
    return _load().get(key)


def put(key: str, command: str, explanation: str, confidence: float = 0.5) -> None:
    data = _load()
    data[key] = {
        "command": command,
        "explanation": explanation,
        "confidence": confidence,
        "ts": time.time(),
    }
    _save(data)
