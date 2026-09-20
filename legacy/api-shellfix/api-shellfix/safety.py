"""
safety.py - destructive-command detection and a confirmation prompt that
still works when this process's stdout is being captured by a shell hook
(fixed=$(python fixcmd.py "$last")). We write prompts to stderr and, on
Windows, read straight from the CONIN$ console device so the prompt still
works even inside a `for /f ... in ('...')` batch construct, which normally
breaks stdin.

Nothing in here ever executes a command. It only decides yes/no.
"""
import os
import re
import sys

# Patterns that should never be auto-run, and should require an explicit
# typed "yes" even when a fix is otherwise found. This list is deliberately
# broad rather than exhaustive - when in doubt, treat it as destructive.
DENYLIST = [
    r"\brm\s+[^\n]*-[a-zA-Z]*r[a-zA-Z]*f",       # rm -rf, rm -fr, rm -Rf ...
    r"\brm\s+[^\n]*-[a-zA-Z]*f[a-zA-Z]*r",
    r"\bdel\s+/s\b",
    r"\brd\s+/s\b",
    r"\brmdir\s+/s\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bdiskpart\b",
    r"\bmkfs\b",
    r"\bdrop\s+(table|database)\b",
    r"\btruncate\s+table\b",
    r"\bgit\s+push\b[^\n]*--force\b",
    r"\bgit\s+reset\b[^\n]*--hard\b",
    r"\bgit\s+clean\b[^\n]*-[a-zA-Z]*f[a-zA-Z]*d",
    r"\bgit\s+clean\b[^\n]*-[a-zA-Z]*d[a-zA-Z]*f",
    r"\bshutdown\b",
    r"\breboot\b",
    r":\(\)\s*\{\s*:\|\s*:\s*&\s*\}\s*;\s*:",     # classic fork bomb
    r">\s*/dev/sd[a-z]\b",
    r"\bsudo\s+rm\b",
]
_DENY_RE = [re.compile(p, re.IGNORECASE) for p in DENYLIST]


def is_destructive(cmd: str) -> bool:
    if not cmd:
        return False
    return any(p.search(cmd) for p in _DENY_RE)


def is_safe_autorun(tokens, vocab) -> bool:
    """True only for read-only / idempotent-ish subcommands we know about.
    Used to gate --auto; unknown commands are never considered safe."""
    if not tokens:
        return False
    prog = tokens[0].lower()
    entry = vocab.get(prog)
    if not entry:
        return False
    safe = entry.get("safe_autorun", [])
    if len(tokens) < 2:
        return True
    return tokens[1] in safe or tokens[1] in ("--version", "-v", "--help", "-h")


def _read_console_line(prompt: str):
    try:
        sys.stderr.write(prompt)
        sys.stderr.flush()
    except Exception:
        return None
    if os.name == "nt":
        try:
            with open("CONIN$", "r", encoding="utf-8", errors="ignore") as con:
                return con.readline()
        except OSError:
            pass
    try:
        return sys.stdin.readline()
    except Exception:
        return None


def confirm(prompt: str, default_yes: bool = True, require_word: str = None) -> bool:
    """Ask a yes/no question on the real console.
    If require_word is set (e.g. "yes"), only that exact word (case
    insensitive) counts as approval - used for destructive commands so a
    stray Enter can never approve them."""
    ans = _read_console_line(prompt)
    if ans is None:
        return False if require_word else default_yes
    ans = ans.strip().lower()
    if require_word:
        return ans == require_word.lower()
    if not ans:
        return default_yes
    return (ans not in ("n", "no")) if default_yes else (ans in ("y", "yes"))
