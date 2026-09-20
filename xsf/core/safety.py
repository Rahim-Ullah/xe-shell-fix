"""
xsf.core.safety - Universal safety gate and confirmation controller.

CRITICAL INVARIANT:
Every proposed command from EVERY tier (static rules, dynamic help flag fixes,
local LLM, or cloud AI) MUST pass through this module before reaching the shell.
"""
import re
import sys
from typing import Tuple

def _has_rm_danger(cmd: str) -> bool:
    """Checks if an rm command has both recursive and force flags."""
    tokens = cmd.split()
    if not tokens or tokens[0].lower() != 'rm':
        return False
    has_recursive = any(t in ('--recursive', '-R') or ('r' in t and t.startswith('-') and not t.startswith('--')) for t in tokens[1:])
    has_force = any(t in ('--force',) or ('f' in t and t.startswith('-') and not t.startswith('--')) for t in tokens[1:])
    return has_recursive and has_force


# Patterns that permanently modify or destroy filesystem, git history, or database state.
DESTRUCTIVE_PATTERNS = [
    # Filesystem destruction (POSIX + Windows)
    re.compile(r"\brmdir\b.*\/[sS]\b", re.IGNORECASE),
    re.compile(r"\bdel\b.*\/[sS]\b", re.IGNORECASE),
    re.compile(r"\bRemove-Item\b.*-(Recurse|Force)", re.IGNORECASE),
    re.compile(r"--no-preserve-root", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
    # Raw disk & block manipulation
    re.compile(r"\bmkfs\b", re.IGNORECASE),
    re.compile(r"\bdd\s+if=", re.IGNORECASE),
    re.compile(r"\b(fdisk|parted|diskpart)\b", re.IGNORECASE),
    re.compile(r">\s*/dev/(sd[a-z]|nvme\d|hd[a-z])", re.IGNORECASE),
    # Git destructive commands
    re.compile(r"\bgit\s+push\b.*(\s--force\b|\s-f\b|\s\+[a-zA-Z0-9_\-]+)", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\s+-[a-zA-Z]*f[a-zA-Z]*d\b", re.IGNORECASE),
    re.compile(r"\bgit\s+branch\s+-[dD]\b", re.IGNORECASE),
    # System permissions & ownership
    re.compile(r"\bchmod\s+-[rR]\s+777\s+/", re.IGNORECASE),
    re.compile(r"\bchown\s+-[rR].*\s+/", re.IGNORECASE),
    # Dangerous remote script execution pipes
    re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash|zsh|powershell|pwsh)\b", re.IGNORECASE),
    # Database mass-drop
    re.compile(r"\bDROP\s+(DATABASE|TABLE|SCHEMA)\b", re.IGNORECASE),
    re.compile(r"\bTRUNCATE\s+TABLE\b", re.IGNORECASE),
    # System reboot/shutdown
    re.compile(r"\b(shutdown|reboot|poweroff|init\s+0)\b", re.IGNORECASE),
    re.compile(r"\bStop-Computer\b", re.IGNORECASE),
]


def is_destructive(cmd: str) -> bool:
    """Returns True if the command matches any destructive pattern."""
    if not cmd:
        return False
    if _has_rm_danger(cmd):
        return True
    for pat in DESTRUCTIVE_PATTERNS:
        if pat.search(cmd):
            return True
    return False


class SafetyGuard:
    """Universal gate ensuring no destructive action executes without explicit confirmation."""

    @staticmethod
    def inspect(cmd: str) -> Tuple[bool, str]:
        """Inspects command and returns (is_destructive, reason)."""
        if _has_rm_danger(cmd):
            return True, "Matches dangerous rm command: recursive and force flags detected"
        for pat in DESTRUCTIVE_PATTERNS:
            match = pat.search(cmd)
            if match:
                return True, f"Matches dangerous pattern: '{match.group(0)}'"
        return False, "Safe"

    @staticmethod
    def confirm(cmd: str, auto_approve: bool = False, dry_run: bool = False) -> bool:
        """
        Prompts user for confirmation.
        - Destructive commands ALWAYS require typing full 'yes'.
        - Safe commands require pressing Enter or 'y' (or auto-approve if flag is set).
        - dry_run only prints and returns False.
        """
        destructive, reason = SafetyGuard.inspect(cmd)

        if dry_run:
            sys.stderr.write(f"  [DRY-RUN] Would execute: {cmd}\n")
            if destructive:
                sys.stderr.write(f"  [WARNING] Command is flagged DESTRUCTIVE ({reason})\n")
            return False

        if auto_approve and not destructive:
            return True

        if destructive:
            sys.stderr.write("\n")
            sys.stderr.write("  \033[1;31m[CAUTION: POTENTIALLY DESTRUCTIVE COMMAND]\033[0m\n")
            sys.stderr.write(f"  {reason}\n")
            sys.stderr.write("  To approve this command, you must type the full word \033[1m'yes'\033[0m: ")
            sys.stderr.flush()
            try:
                ans = input().strip()
            except (EOFError, KeyboardInterrupt):
                sys.stderr.write("\n")
                return False
            return ans.lower() == "yes"

        # Standard non-destructive prompt
        sys.stderr.write(f"\nExecute? [\033[1mEnter\033[0m/y/n]: ")
        sys.stderr.flush()
        try:
            ans = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\n")
            return False

        return ans == "" or ans.lower().startswith("y")
