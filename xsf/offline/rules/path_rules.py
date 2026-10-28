"""
xsf.offline.rules.path_rules - Deterministic fuzzy and case-insensitive path corrector.

Fixes mistyped filenames and directory paths in commands (cat, ls, vim, python, etc.)
by checking real filesystem entries in parent directories with difflib and case matching.
"""
import difflib
import os
from pathlib import Path
from typing import List, Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule


_PATH_ERRORS = (
    "no such file or directory",
    "cannot find the path",
    "cannot find file",
    "the system cannot find the file specified",
    "the system cannot find the path specified",
    "could not open file",
    "can't open file",
    "does not exist",
    "not a directory",
)


def _resolve_fuzzy_segment(parent: Path, segment: str) -> Optional[str]:
    """Finds best matching child name in parent directory (exact, case-insensitive, or difflib)."""
    if not parent.exists() or not parent.is_dir():
        return None
    try:
        entries = [e.name for e in parent.iterdir()]
    except (PermissionError, OSError):
        return None

    if not entries:
        return None

    # 1. Exact match
    if segment in entries:
        return segment

    # 2. Case-insensitive match (crucial for Linux cross-platform casing slips)
    seg_lower = segment.lower()
    for e in entries:
        if e.lower() == seg_lower:
            return e

    # 3. Fuzzy match via difflib SequenceMatcher
    matches = difflib.get_close_matches(segment, entries, n=1, cutoff=0.6)
    if matches:
        return matches[0]

    return None


def resolve_path_typo(raw_path: str, cwd: Optional[str] = None) -> Optional[str]:
    """
    Attempts to resolve a nonexistent path to an existing filesystem path
    by healing typos or case mismatches segment by segment.
    """
    if not raw_path:
        return None

    # Handle quotes and whitespace
    clean = raw_path.strip('\'"')
    if not clean or any(c in clean for c in "*?"):
        return None

    # Detect separator style
    sep = "\\" if "\\" in clean and "/" not in clean else "/"
    normalized = clean.replace("\\", "/")

    is_absolute = normalized.startswith("/")
    has_leading_dot = normalized.startswith("./") or normalized.startswith("../")

    parts = [p for p in normalized.split("/") if p]
    if not parts:
        return None

    base_dir = Path(cwd) if cwd else Path.cwd()

    # If it already exists on disk, check if casing matches exactly
    try:
        p = Path(clean) if is_absolute else (base_dir / clean)
        if p.exists():
            if os.name == "nt":
                # On Windows, p.exists() is True even if casing differs.
                # Check if disk casing actually matches the requested casing.
                try:
                    real_path = p.resolve()
                    real_parts = real_path.parts[-len(parts):]
                    if tuple(parts) == tuple(real_parts):
                        return None
                except Exception:
                    return None
            else:
                return None
    except Exception:
        pass

    # Determine starting root
    if is_absolute:
        curr = Path("/")
    else:
        curr = base_dir

    corrected_parts = []
    typo_found = False

    for part in parts:
        if part in (".", ".."):
            corrected_parts.append(part)
            curr = curr / part
            continue

        resolved = _resolve_fuzzy_segment(curr, part)
        if resolved is None:
            # Cannot heal this path
            return None

        if resolved != part:
            typo_found = True

        corrected_parts.append(resolved)
        curr = curr / resolved

    if not typo_found:
        return None

    # Verify that the healed path actually exists
    try:
        if not curr.exists():
            return None
    except Exception:
        return None

    # Reconstruct in original separator format
    rebuilt = sep.join(corrected_parts)
    if is_absolute:
        rebuilt = "/" + rebuilt
    elif has_leading_dot:
        if normalized.startswith("./"):
            rebuilt = f".{sep}{rebuilt}"
        elif normalized.startswith("../"):
            rebuilt = f"..{sep}{rebuilt}"

    return rebuilt


class FuzzyPathCorrectionRule(Rule):
    """
    Auto-corrects misspelled file/directory paths on disk.
    Priority 7: Runs before Git and Stderr generic rules.
    """
    name = "fuzzy_path_correction"
    priority = 7
    requires_output = True

    def match(self, cmd: Command) -> bool:
        if not cmd.stderr_text:
            return False
        err = cmd.stderr_text.lower()
        if not any(signal in err for signal in _PATH_ERRORS):
            return False

        # Look for path tokens in the command
        for tok in cmd.tokens[1:]:
            if tok.startswith("-"):
                continue
            healed = resolve_path_typo(tok, cwd=cmd.cwd)
            if healed is not None:
                return True
        return False

    def get_candidates(self, cmd: Command) -> List[Tuple[str, float, str]]:
        candidates = []
        new_tokens = list(cmd.tokens)
        modified = False
        replaces = []

        for i in range(1, len(new_tokens)):
            tok = new_tokens[i]
            if tok.startswith("-"):
                continue
            healed = resolve_path_typo(tok, cwd=cmd.cwd)
            if healed is not None and healed != tok:
                new_tokens[i] = healed
                modified = True
                replaces.append((tok, healed))

        if modified:
            fixed_cmd = cmd.quote_join(new_tokens)
            desc_parts = [f"'{old}' -> '{new}'" for old, new in replaces]
            explanation = f"Corrected path: {', '.join(desc_parts)}"
            candidates.append((fixed_cmd, 0.90, explanation))

        return candidates
