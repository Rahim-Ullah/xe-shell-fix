"""
xsf.core.safety - Universal safety gate and confirmation controller.

CRITICAL INVARIANT:
Every proposed command from EVERY tier (static rules, dynamic help flag fixes,
local LLM, or cloud AI) MUST pass through this module before reaching the shell.
"""
import os
import re
import shlex
import sys
from typing import List, Optional, Tuple

_EXEC_WRAPPERS = {
    "sudo", "doas", "env", "command", "nohup", "busybox",
    "winpty", "nice", "ionice", "time", "timeout", "xargs", "pkexec",
}
_WRAPPER_FLAGS_WITH_ARG = {"-u", "-g", "-C", "-D", "-h", "-p", "-r", "-t", "-U", "-n", "-c", "-s", "-k"}
_RE_SHELL_SPLIT = re.compile(r"(?:&&|\|\||[;|&`\n]|\$\()")
_RE_ESCAPE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def _sanitize_display(text: str) -> str:
    """Strips raw ANSI/OSC escape sequences and control characters before terminal display."""
    if not text:
        return ""
    cleaned = _RE_ESCAPE.sub("", text)
    return "".join(ch for ch in cleaned if ch in ("\n", "\t") or ord(ch) >= 32)


def _unwrap_command_tokens(tokens: List[str]) -> List[str]:
    """Strips outer execution wrappers (sudo, doas, env, xargs, etc.), env vars, and flags to reach actual command."""
    idx = 0
    while idx < len(tokens):
        tok = tokens[idx]
        # Skip inline environment variable assignments (e.g. FOO=bar)
        if "=" in tok and not tok.startswith("-") and tok.split("=", 1)[0].isidentifier():
            idx += 1
            continue

        base = tok.lower()
        base_name = base.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        if base_name in _EXEC_WRAPPERS:
            idx += 1
            while idx < len(tokens):
                curr = tokens[idx]
                if "=" in curr and not curr.startswith("-") and curr.split("=", 1)[0].isidentifier():
                    idx += 1
                    continue
                if curr.startswith("-"):
                    if curr in _WRAPPER_FLAGS_WITH_ARG and idx + 1 < len(tokens):
                        idx += 2
                    else:
                        idx += 1
                else:
                    break
            # `timeout` takes a duration argument before the command
            if base_name == "timeout" and idx < len(tokens):
                idx += 1
        else:
            break
    return tokens[idx:] if idx < len(tokens) else tokens


def _segment_has_rm_danger(segment: str) -> bool:
    """Checks if a single command segment invokes rm with recursive or root-wildcard flags."""
    try:
        raw_tokens = shlex.split(segment, posix=True)
    except ValueError:
        raw_tokens = segment.split()
    if not raw_tokens:
        return False
    tokens = _unwrap_command_tokens(raw_tokens)
    if not tokens:
        return False
    prog = tokens[0].lower().rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if prog != "rm":
        return False
    args = tokens[1:]
    # Any recursive deletion is destructive, with or without force flag
    has_recursive = any(
        t.lower() in ("--recursive", "-r", "-r/")
        or ("r" in t.lower() and t.startswith("-") and not t.startswith("--"))
        for t in args
    )
    if has_recursive:
        return True
    # Force deletion or wildcard deletion at root
    has_force = any(
        t.lower() == "--force"
        or ("f" in t.lower() and t.startswith("-") and not t.startswith("--"))
        for t in args
    )
    has_root_target = any(t in ("/", "/*", "~", "~/*") for t in args)
    return has_force and has_root_target


def _has_rm_danger(cmd: str) -> bool:
    """Checks if any sub-command in a (potentially chained/piped) command has dangerous rm flags."""
    if not cmd:
        return False
    for segment in _RE_SHELL_SPLIT.split(cmd):
        segment = segment.strip().rstrip(")")
        if segment and _segment_has_rm_danger(segment):
            return True
    return False


# Patterns that permanently modify or destroy filesystem, git history, or database state.
DESTRUCTIVE_PATTERNS = [
    # Filesystem destruction (POSIX + Windows)
    re.compile(r"\b(rd|rmdir)\b.*\/[sS]\b", re.IGNORECASE),
    re.compile(r"\bdel\b.*\/[sS]\b", re.IGNORECASE),
    re.compile(r"\bRemove-Item\b.*-(Recurse|Force)", re.IGNORECASE),
    re.compile(r"--no-preserve-root", re.IGNORECASE),
    re.compile(r"\bformat\s+[a-zA-Z]:", re.IGNORECASE),
    re.compile(r"\bfind\b.*\s-delete\b", re.IGNORECASE),
    re.compile(r"\bfind\b.*-exec\s+(?:\S*/)?rm\b", re.IGNORECASE),
    # Raw disk & block manipulation
    re.compile(r"\b(wipefs|shred|srm)\b", re.IGNORECASE),
    re.compile(r"\bmkfs(\.[a-z0-9]+)?\b", re.IGNORECASE),
    re.compile(r"\bdd\b.*\b(of=|if=)", re.IGNORECASE),
    re.compile(r"\b(fdisk|parted|diskpart)\b", re.IGNORECASE),
    re.compile(r">\s*/dev/(sd[a-z]|nvme\d|hd[a-z]|vd[a-z]|xvd[a-z]|mmcblk\d)", re.IGNORECASE),
    # Git destructive commands
    re.compile(r"\bgit\s+push\b.*(\s--force\b|\s-f\b|\s\+[a-zA-Z0-9_\-]+)", re.IGNORECASE),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.IGNORECASE),
    re.compile(r"\bgit\s+clean\b.*(-[a-zA-Z]*[fd][a-zA-Z]*[fd]|\b-f\b.*\b-d\b|\b-d\b.*\b-f\b)", re.IGNORECASE),
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
    # Cloud & container mass-destructive actions
    re.compile(r"\bterraform\s+destroy\b", re.IGNORECASE),
    re.compile(r"\bpulumi\s+destroy\b", re.IGNORECASE),
    re.compile(r"\bkubectl\s+delete\s+namespace\b", re.IGNORECASE),
    re.compile(r"\bkubectl\s+delete\s+--all\b", re.IGNORECASE),
    re.compile(r"\bdocker\s+system\s+prune\b.*(-a|--all)", re.IGNORECASE),
    re.compile(r"\bdocker\s+(container\s+)?rm\b.*(-f|--force)", re.IGNORECASE),
    re.compile(r"\bpodman\s+system\s+prune\b.*(-a|--all)", re.IGNORECASE),
    # File truncation to zero bytes
    re.compile(r"\btruncate\s+-s\s+0\b", re.IGNORECASE),
    # Additional DB mass-drop variants
    re.compile(r"\bDROP\s+ALL\s+TABLES\b", re.IGNORECASE),
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


def prompt_edit_command(initial_cmd: str) -> Optional[str]:
    """
    Opens an inline editable command prompt pre-filled with `initial_cmd`.
    Uses GNU readline on POSIX or msvcrt keystroke injection on Windows,
    while redirecting stdout to stderr during input() so stdout (captured for shell eval)
    remains 100% clean.
    """
    clean_initial = _sanitize_display(initial_cmd).strip()
    orig_stdout = sys.stdout
    rl_mod = None
    is_tty = hasattr(sys.stdin, "isatty") and sys.stdin.isatty() and hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
    try:
        sys.stdout = sys.stderr
        if is_tty and os.name != "nt":
            try:
                import readline as _rl
                rl_mod = _rl
                rl_mod.set_startup_hook(lambda: rl_mod.insert_text(clean_initial))
            except Exception:
                rl_mod = None
                sys.stderr.write(f"  \033[90m(Current: {clean_initial})\033[0m\n")
        elif is_tty and os.name == "nt":
            try:
                import msvcrt
                for ch in clean_initial:
                    msvcrt.ungetwch(ch)
            except Exception:
                sys.stderr.write(f"  \033[90m(Current: {clean_initial})\033[0m\n")

        sys.stderr.write("  \033[1;36mEdit command:\033[0m ")
        sys.stderr.flush()
        edited = input().strip()
        return edited if edited else None
    except (EOFError, KeyboardInterrupt):
        sys.stderr.write("\n")
        return None
    finally:
        if rl_mod is not None:
            try:
                rl_mod.set_startup_hook(None)
            except Exception:
                pass
        sys.stdout = orig_stdout


class SafetyGuard:
    """Universal gate ensuring no destructive action executes without explicit confirmation."""

    last_approved_command: Optional[str] = None

    @staticmethod
    def inspect(cmd: str) -> Tuple[bool, str]:
        """Inspects command and returns (is_destructive, reason)."""
        if _has_rm_danger(cmd):
            return True, "Matches dangerous rm command: recursive and force flags detected"
        for pat in DESTRUCTIVE_PATTERNS:
            match = pat.search(cmd)
            if match:
                return True, f"Matches dangerous pattern: '{_sanitize_display(match.group(0))}'"
        return False, "Safe"

    @staticmethod
    def _prompt_destructive_yes(reason: str) -> bool:
        sys.stderr.write("\n")
        sys.stderr.write("  \033[1;31m[CAUTION: POTENTIALLY DESTRUCTIVE COMMAND]\033[0m\n")
        sys.stderr.write(f"  {reason}\n")
        sys.stderr.write("  To approve this command, you must type the full word \033[1m'yes'\033[0m (or \033[1m'e'\033[0m to edit): ")
        sys.stderr.flush()
        try:
            ans = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\n")
            return False
        if ans.lower() in ("e", "edit"):
            edited = prompt_edit_command(SafetyGuard.last_approved_command or "")
            if not edited:
                return False
            SafetyGuard.last_approved_command = edited
            d2, r2 = SafetyGuard.inspect(edited)
            if d2:
                return SafetyGuard._prompt_destructive_yes(r2)
            return True
        return ans.lower() == "yes"

    @staticmethod
    def confirm(cmd: str, auto_approve: bool = False, dry_run: bool = False) -> bool:
        """
        Prompts user for confirmation (or inline editing via 'e').
        - Destructive commands ALWAYS require typing full 'yes'.
        - Safe commands accept Enter/y to run, 'e' to edit inline before running, or 'n' to cancel.
        - dry_run only prints and returns False.
        """
        SafetyGuard.last_approved_command = cmd
        destructive, reason = SafetyGuard.inspect(cmd)
        safe_cmd_display = _sanitize_display(cmd)

        if dry_run:
            sys.stderr.write(f"  [DRY-RUN] Would execute: {safe_cmd_display}\n")
            if destructive:
                sys.stderr.write(f"  [WARNING] Command is flagged DESTRUCTIVE ({reason})\n")
            return False

        if auto_approve and not destructive:
            return True

        if destructive:
            return SafetyGuard._prompt_destructive_yes(reason)

        # Standard non-destructive prompt with [e]dit support
        sys.stderr.write("\nExecute? [\033[1mEnter\033[0m/y/\033[1me\033[0m=edit/n]: ")
        sys.stderr.flush()
        try:
            ans = input().strip()
        except (EOFError, KeyboardInterrupt):
            sys.stderr.write("\n")
            return False

        if ans.lower() in ("e", "edit"):
            edited = prompt_edit_command(cmd)
            if not edited:
                return False
            SafetyGuard.last_approved_command = edited
            d2, r2 = SafetyGuard.inspect(edited)
            if d2:
                return SafetyGuard._prompt_destructive_yes(r2)
            return True

        return ans == "" or ans.lower().startswith("y")
