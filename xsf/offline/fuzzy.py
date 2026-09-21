"""
xsf.offline.fuzzy - Levenshtein and sequence matcher for typo correction.

Handles:
  - Program name typos (e.g. doker → docker)
  - Known tool aliases (e.g. k → kubectl, tf → terraform, g → git)
  - Subcommand typos with flag-skipping (e.g. git statsu → git status, git -C /path statsu → git -C /path status)
  - Compound tool subcommands (e.g. docker compose bulid → docker compose build)
  - Common flag dash typos (e.g. python -version → python --version, docker -help → docker --help)
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

# Build reverse alias map: alias → canonical  (e.g. "k" → "kubectl")
_ALIAS_TO_CANONICAL: dict = {}
for _tool, _data in VOCAB.items():
    if _tool.startswith("_") or not isinstance(_data, dict):
        continue
    for _alias in _data.get("aliases", []):
        _ALIAS_TO_CANONICAL[_alias.lower()] = _tool

ALL_TARGET_PROGRAMS = sorted(list(TOOL_NAMES | KNOWN_SAFE_COMMANDS | set(_ALIAS_TO_CANONICAL.keys())))

# Common flag dash slips: words that are almost universally double-dash long options
_COMMON_LONG_FLAGS = {
    "-version": "--version",
    "-help": "--help",
    "-verbose": "--verbose",
    "-force": "--force",
    "-all": "--all",
    "-output": "--output",
    "-config": "--config",
    "-dry-run": "--dry-run",
    "-recursive": "--recursive",
}

# Flags that take an argument, so the next token is a value, not a subcommand
_FLAGS_WITH_ARGS = {"-c", "-C", "-m", "-f", "-o", "-p", "-u", "-e", "-i", "--config", "--file", "--work-tree"}


def fuzzy_match_command(cmd: Command) -> Optional[Tuple[str, float, str]]:
    """
    Corrects tool name, subcommands, and flags using vocabulary + alias resolution.
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

    # 1. Resolve alias first (e.g. k → kubectl, tf → terraform, g → git)
    if prog_key in _ALIAS_TO_CANONICAL and prog_key not in TOOL_NAMES:
        canonical = _ALIAS_TO_CANONICAL[prog_key]
        fixed[0] = canonical
        prog_key = canonical
        changed = True
        confidence = 0.95
        notes.append(f"alias '{prog}' → '{canonical}'")

    # 2. Correct program name if still unrecognized and not a known safe command
    elif prog_key not in TOOL_NAMES and prog_key not in KNOWN_SAFE_COMMANDS:
        match = difflib.get_close_matches(prog_key, ALL_TARGET_PROGRAMS, n=1, cutoff=0.62)
        if match:
            fixed[0] = match[0]
            prog_key = match[0]
            changed = True
            confidence = difflib.SequenceMatcher(None, prog.lower(), match[0]).ratio()
            notes.append(f"'{prog}' → '{match[0]}'")

    # 3. Compound command detection: e.g. "docker compose" -> subcommands in "docker-compose"
    active_vocab_key = prog_key
    subcommand_idx = -1

    if len(tokens) > 2 and f"{prog_key}-{tokens[1].lower()}" in VOCAB:
        compound_key = f"{prog_key}-{tokens[1].lower()}"
        active_vocab_key = compound_key
        subcommand_idx = 2
    elif prog_key in VOCAB and len(tokens) > 1:
        # Scan for the actual subcommand token (skip flags and flag arguments)
        i = 1
        while i < len(tokens):
            tok = tokens[i]
            if tok in _FLAGS_WITH_ARGS and i + 1 < len(tokens):
                i += 2  # Skip flag and its argument value
                continue
            if not tok.startswith("-"):
                subcommand_idx = i
                break
            i += 1

    # 4. Correct subcommand typo if found
    if active_vocab_key in VOCAB and subcommand_idx != -1 and subcommand_idx < len(tokens):
        subs = VOCAB[active_vocab_key].get("subcommands", [])
        sub = tokens[subcommand_idx]
        if (
            subs
            and sub not in subs
            and sub.lower() not in KNOWN_SAFE_COMMANDS
            and not sub.startswith("-")
        ):
            match = difflib.get_close_matches(sub.lower(), [s.lower() for s in subs], n=1, cutoff=0.62)
            if match:
                correct_sub = next((s for s in subs if s.lower() == match[0]), match[0])
                fixed[subcommand_idx] = correct_sub
                changed = True
                sub_conf = difflib.SequenceMatcher(None, sub.lower(), match[0]).ratio()
                confidence = min(confidence, sub_conf)
                notes.append(f"'{sub}' → '{correct_sub}'")

    # 5. Correct single-dash vs double-dash long flag slips
    for idx in range(1, len(fixed)):
        token_val = fixed[idx]
        if token_val in _COMMON_LONG_FLAGS:
            corrected_flag = _COMMON_LONG_FLAGS[token_val]
            fixed[idx] = corrected_flag
            changed = True
            confidence = min(confidence, 0.98)
            notes.append(f"'{token_val}' → '{corrected_flag}'")

    if not changed:
        return None

    fixed_cmd_str = cmd.quote_join(fixed)
    explanation = f"Corrected: {', '.join(notes)}"
    return fixed_cmd_str, confidence, explanation
