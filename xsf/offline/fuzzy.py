"""
xsf.offline.fuzzy - Levenshtein and sequence matcher for typo correction.
"""
import difflib
import json
from pathlib import Path
from typing import Optional, Tuple

from xsf.core.command import Command

VOCAB_PATH = Path(__file__).resolve().parent / "vocabulary.json"
try:
    VOCAB = json.loads(VOCAB_PATH.read_text(encoding="utf-8"))
except Exception:
    VOCAB = {}

KNOWN_SAFE_COMMANDS = {c.lower() for c in VOCAB.get("_known_safe_commands", [])}
TOOL_NAMES = {k for k in VOCAB if not k.startswith("_")}
ALL_TARGET_PROGRAMS = sorted(list(TOOL_NAMES | KNOWN_SAFE_COMMANDS))


def fuzzy_match_command(cmd: Command) -> Optional[Tuple[str, float, str]]:
    """
    Corrects tool name and/or subcommand typos.
    Returns: (fixed_command_string, confidence, explanation) or None.
    """
    tokens = cmd.tokens
    if not tokens:
        return None

    prog = tokens[0]
    prog_key = prog.lower()
    fixed = list(tokens)
    changed = False
    confidence = 1.0
    notes = []

    # 1. Correct program name if it's unrecognized and not a safe builtin
    if prog_key not in TOOL_NAMES and prog_key not in KNOWN_SAFE_COMMANDS:
        match = difflib.get_close_matches(prog_key, ALL_TARGET_PROGRAMS, n=1, cutoff=0.6)
        if match:
            fixed[0] = match[0]
            prog_key = match[0]
            changed = True
            confidence = difflib.SequenceMatcher(None, prog.lower(), match[0]).ratio()
            notes.append(f"'{prog}' \u2192 '{match[0]}'")

    # 2. If program is known, correct subcommand typo
    if prog_key in VOCAB and len(tokens) > 1:
        subs = VOCAB[prog_key].get("subcommands", [])
        sub = tokens[1]
        if subs and sub not in subs and sub.lower() not in KNOWN_SAFE_COMMANDS and not sub.startswith("-"):
            match = difflib.get_close_matches(sub.lower(), subs, n=1, cutoff=0.6)
            if match:
                fixed[1] = match[0]
                changed = True
                sub_conf = difflib.SequenceMatcher(None, sub.lower(), match[0]).ratio()
                confidence = min(confidence, sub_conf)
                notes.append(f"'{sub}' \u2192 '{match[0]}'")

    if not changed:
        return None

    fixed_cmd_str = cmd.quote_join(fixed)
    explanation = f"Corrected typo: {', '.join(notes)}"
    return fixed_cmd_str, confidence, explanation
