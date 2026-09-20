"""
xsf.offline.help_parser - Dynamic multi-format --help flag extractor and corrector.

Tier 1b: When static rules and vocabulary do not match, this module runs `<cmd> --help`
(cached persistently to disk) and parses valid options using multi-format strategies
(Argparse, Cobra/Go, POSIX/GNU, and token fallback) to correct mistyped flags.
"""
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Dict, List, Optional, Set, Tuple

from xsf.core.command import Command

CACHE_FILE = Path.home() / ".shellfix" / "help_cache.json"

# Regex parsing strategies
RE_ARGPARSE = re.compile(r"^\s*(?:(-\w),\s+)?(--[\w-]+)(?:[=\s][\w<>\[\]]+)?\s{2,}", re.MULTILINE)
RE_COBRA = re.compile(r"^\s*(?:(-\w),\s+)?(--[\w-]+)(?:\s+\w+)?\s{2,}", re.MULTILINE)
RE_POSIX = re.compile(r"^\s*(-\w)(?:,\s+(--[\w-]+))?\s{2,}", re.MULTILINE)
RE_ALL_FLAGS = re.compile(r"(?:\s|^)(--[\w-]+|-\w)\b")


class HelpCache:
    """Disk cache for extracted command flags."""
    _data: Dict[str, List[str]] = {}
    _loaded: bool = False

    @classmethod
    def load(cls) -> None:
        if cls._loaded:
            return
        if CACHE_FILE.exists():
            try:
                cls._data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                cls._data = {}
        cls._loaded = True

    @classmethod
    def save(cls) -> None:
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(json.dumps(cls._data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def get(cls, key: str) -> Optional[List[str]]:
        cls.load()
        return cls._data.get(key)

    @classmethod
    def put(cls, key: str, flags: List[str]) -> None:
        cls.load()
        cls._data[key] = flags
        cls.save()


def extract_flags_from_text(help_text: str) -> List[str]:
    """Applies multi-format extraction strategies to extract unique flags."""
    flags: Set[str] = set()

    # Strategy 1: Argparse format
    for short, long in RE_ARGPARSE.findall(help_text):
        if short:
            flags.add(short)
        if long:
            flags.add(long)

    # Strategy 2: Cobra/Go CLI format
    for short, long in RE_COBRA.findall(help_text):
        if short:
            flags.add(short)
        if long:
            flags.add(long)

    # Strategy 3: POSIX / GNU format
    for short, long in RE_POSIX.findall(help_text):
        if short:
            flags.add(short)
        if long:
            flags.add(long)

    # Strategy 4: Fallback token scanner
    if len(flags) < 3:
        for match in RE_ALL_FLAGS.findall(help_text):
            cleaned = match.strip()
            if cleaned.startswith("-") and len(cleaned) > 1 and not cleaned.startswith("---"):
                flags.add(cleaned)

    return sorted(list(flags))


def get_command_flags(binary_name: str, subcommand: Optional[str] = None) -> List[str]:
    """Executes `<cmd> [subcmd] --help` in a quick, timed subprocess with disk caching."""
    cache_key = f"{binary_name}:{subcommand or ''}"
    cached = HelpCache.get(cache_key)
    if cached is not None:
        return cached

    # Verify binary exists on PATH to avoid spawning dead processes
    if not shutil.which(binary_name):
        return []

    cmd_args = [binary_name]
    if subcommand and not subcommand.startswith("-"):
        cmd_args.append(subcommand)
    cmd_args.append("--help")

    try:
        proc = subprocess.run(
            cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=1.2,  # Hard timeout to prevent hangs on slow CLIs
            text=True,
            errors="ignore",
        )
        output = proc.stdout if proc.stdout else proc.stderr
    except (subprocess.SubprocessError, OSError):
        output = ""

    flags = extract_flags_from_text(output)
    if flags:
        HelpCache.put(cache_key, flags)
    return flags


def correct_flag_typos(cmd: Command) -> Optional[Tuple[str, float, str]]:
    """
    Tier 1b: Inspects command tokens for flag typos against dynamically extracted `--help` flags.
    Returns: (fixed_command, confidence, explanation) or None.
    """
    tokens = cmd.tokens
    if len(tokens) < 2:
        return None

    prog = tokens[0]
    # Check if there is a subcommand
    subcmd = tokens[1] if len(tokens) > 2 and not tokens[1].startswith("-") else None

    # Get flags for either `prog subcmd` or `prog`
    valid_flags = get_command_flags(prog, subcmd)
    if not valid_flags and subcmd:
        valid_flags = get_command_flags(prog)

    if not valid_flags:
        return None

    valid_flag_set = set(valid_flags)
    new_tokens = list(tokens)
    changed = False
    notes = []
    min_confidence = 1.0

    for idx, token in enumerate(tokens):
        if not token.startswith("-"):
            continue

        # Handle `--flag=value`
        prefix = ""
        flag_part = token
        val_part = ""
        if "=" in token:
            flag_part, val_part = token.split("=", 1)
            val_part = "=" + val_part

        if flag_part in valid_flag_set:
            continue

        # Find closest match among valid flags
        matches = difflib.get_close_matches(flag_part, valid_flags, n=1, cutoff=0.6)
        if matches:
            best = matches[0]
            conf = difflib.SequenceMatcher(None, flag_part, best).ratio()
            min_confidence = min(min_confidence, conf)
            new_tokens[idx] = f"{best}{val_part}"
            changed = True
            notes.append(f"'{flag_part}' \u2192 '{best}'")

    if not changed:
        return None

    fixed_cmd = cmd.quote_join(new_tokens)
    explanation = f"Corrected flags via help-introspection: {', '.join(notes)}"
    return fixed_cmd, min_confidence, explanation
