"""
xsf.ui.selector - Terminal colored diff and interactive multi-candidate selector.

Features:
  - Interactive arrow-key navigation (↑ / ↓ or k / j)
  - Direct number selection (1-9)
  - Enter to confirm selected candidate
  - Esc / q / Ctrl+C to cancel
  - Clean headless fallback for non-TTY, pipes, and automated tests
"""
import difflib
import os
import sys
from typing import List, Optional, Tuple

Candidate = Tuple[str, float, str, str]  # (fixed_command, confidence, explanation, source)


def render_diff(old_tokens: List[str], new_tokens: List[str]) -> str:
    """Renders colored inline token-by-token diff."""
    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    parts = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            parts.append(" ".join(old_tokens[i1:i2]))
        elif tag == "replace":
            old_str = " ".join(old_tokens[i1:i2])
            new_str = " ".join(new_tokens[j1:j2])
            parts.append(f"\033[9;31m{old_str}\033[0m \033[1;32m{new_str}\033[0m")
        elif tag == "delete":
            old_str = " ".join(old_tokens[i1:i2])
            parts.append(f"\033[9;31m{old_str}\033[0m")
        elif tag == "insert":
            new_str = " ".join(new_tokens[j1:j2])
            parts.append(f"\033[1;32m{new_str}\033[0m")
    return " ".join(parts)


def _read_key_cross_platform() -> str:
    """
    Reads a single keypress cross-platform.
    Returns: 'UP', 'DOWN', 'ENTER', 'CANCEL', or single char ('1'-'9', etc.)
    """
    if os.name == "nt":
        import msvcrt
        try:
            ch = msvcrt.getwch()
        except Exception:
            return "CANCEL"

        if ch in ("\r", "\n"):
            return "ENTER"
        if ch in ("\x1b", "q", "Q"):
            return "CANCEL"
        if ch in ("\x00", "\xe0"):
            # Extended key prefix
            ext = msvcrt.getwch()
            if ext == "H":
                return "UP"
            if ext == "P":
                return "DOWN"
        return ch
    else:
        import termios
        import tty
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
        except Exception:
            return "CANCEL"
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch in ("q", "Q"):
                return "CANCEL"
            if ch == "\x1b":
                # Check for escape sequence
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass
                # Read next characters if available
                import select
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    seq = sys.stdin.read(2)
                    if seq == "[A":
                        return "UP"
                    elif seq == "[B":
                        return "DOWN"
                return "CANCEL"
            return ch
        except Exception:
            return "CANCEL"
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass


def _safe_write(stream, text: str, fallback: str) -> None:
    """Writes text to stream, falling back to ASCII if encoding fails (e.g. Windows cp1252)."""
    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.write(fallback)


def _render_menu(candidates: List[Candidate], selected_idx: int) -> int:
    """Renders the candidate list on stderr and returns the number of lines printed."""
    lines_count = 0
    sys.stderr.write("\033[1;36m=== Multiple Fix Candidates Found ===\033[0m\n")
    lines_count += 1

    for i, (cmd, conf, exp, src) in enumerate(candidates):
        is_sel = (i == selected_idx)
        cursor = "\033[1;32m>\033[0m" if is_sel else " "
        badge = "\033[32m[OFFLINE]\033[0m" if src == "offline" else "\033[36m[AI]\033[0m"
        pct = f"{int(conf * 100)}%"

        if is_sel:
            line = f"  [{i + 1}] {cursor} \033[1;4m{cmd}\033[0m  \033[90m({pct} {badge})\033[0m\n"
        else:
            line = f"  [{i + 1}] {cursor} \033[1m{cmd}\033[0m  \033[90m({pct} {badge})\033[0m\n"
        sys.stderr.write(line)
        lines_count += 1

        if exp and is_sel:
            _safe_write(sys.stderr, f"      \033[90m\u2514\u2500 {exp}\033[0m\n", f"      \033[90m\\-- {exp}\033[0m\n")
            lines_count += 1

    _safe_write(
        sys.stderr,
        "\033[90m[Use \u2191/\u2193 to navigate, Enter to run, 1-9 direct, Esc/q to cancel]\033[0m\n",
        "\033[90m[Use Up/Down to navigate, Enter to run, 1-9 direct, Esc/q to cancel]\033[0m\n",
    )
    lines_count += 1
    sys.stderr.flush()
    return lines_count


def _clear_menu(lines_count: int) -> None:
    """Moves cursor up lines_count times and clears each line."""
    for _ in range(lines_count):
        sys.stderr.write("\033[F\033[K")
    sys.stderr.flush()


def choose_candidate(
    candidates: List[Candidate],
    default_index: int = 0,
) -> Optional[Candidate]:
    """
    Presents an interactive menu to choose between multiple candidate fixes.
    Returns the chosen Candidate or None if cancelled.
    """
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Non-interactive / non-TTY fallback (pipes, scripts, CI environments, automated testing)
    is_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS") or os.environ.get("TF_BUILD"))
    is_not_tty = (
        not hasattr(sys.stdin, "isatty")
        or not sys.stdin.isatty()
        or not hasattr(sys.stderr, "isatty")
        or not sys.stderr.isatty()
    )
    if is_ci or is_not_tty:
        sys.stderr.write("\n\033[1mMultiple fixes found:\033[0m\n")
        for i, (cmd, conf, exp, src) in enumerate(candidates):
            badge = "[OFFLINE]" if src == "offline" else "[AI]"
            sys.stderr.write(f"  [{i + 1}] {cmd} ({int(conf * 100)}% {badge})\n")
        sys.stderr.write(f"Select fix [1-{len(candidates)}, Enter=1, n=Cancel]: ")
        sys.stderr.flush()
        try:
            choice = sys.stdin.readline().strip().lower()
            if not choice or choice == "1" or choice == "y":
                return candidates[0]
            if choice in ("n", "q", "no", "cancel"):
                return None
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                return candidates[idx]
        except Exception:
            return None
        return candidates[0]

    # Interactive TTY Mode
    idx = max(0, min(default_index, len(candidates) - 1))
    lines_printed = _render_menu(candidates, idx)

    while True:
        key = _read_key_cross_platform()

        if key == "ENTER":
            _clear_menu(lines_printed)
            return candidates[idx]
        elif key == "CANCEL":
            _clear_menu(lines_printed)
            return None
        elif key in ("UP", "k", "K"):
            _clear_menu(lines_printed)
            idx = (idx - 1) % len(candidates)
            lines_printed = _render_menu(candidates, idx)
        elif key in ("DOWN", "j", "J"):
            _clear_menu(lines_printed)
            idx = (idx + 1) % len(candidates)
            lines_printed = _render_menu(candidates, idx)
        elif key.isdigit():
            num = int(key)
            if 1 <= num <= len(candidates):
                _clear_menu(lines_printed)
                return candidates[num - 1]
