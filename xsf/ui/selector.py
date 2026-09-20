"""
xsf.ui.selector - Terminal colored diff and formatting display.
"""
import difflib
from typing import List


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
