#!/usr/bin/env python3
"""
fixcmd.py - offline typo & missing-flag fixer for shell commands.

CONTRACT (do not break this - shell hooks depend on it):
  - This script NEVER executes the fixed command itself.
  - stdout gets AT MOST ONE line: the corrected command, and only after
    it has been approved (by the user, or by --auto for a command judged
    safe). Everything else - prompts, explanations, errors - goes to
    stderr. This lets a shell hook safely do:
        fixed=$(python fixcmd.py "$last")
    and then `eval "$fixed"` in ITS OWN process, so things like `cd` and
    exported variables actually take effect in the calling shell.
  - Exit codes:
        0 = a fix was approved and printed to stdout
        1 = no fix found, or the user declined a non-destructive fix
        2 = a fix was found but is destructive and was not approved

Standalone testing (no shell hook needed):
    python fixcmd.py "pip instaaaaal fastapi" --dry-run
    python fixcmd.py "python venv .venv" --shell powershell --dry-run
"""
import argparse
import difflib
import json
import os
import shlex
import sys
from pathlib import Path

HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(HOME))
import flag_rules            # noqa: E402
import safety                 # noqa: E402
from shellutil import quote_join  # noqa: E402

VOCAB = json.loads((HOME / "vocabulary.json").read_text(encoding="utf-8"))
KNOWN_SAFE_COMMANDS = {c.lower() for c in VOCAB.get("_known_safe_commands", [])}
TOOL_NAMES = {k for k in VOCAB if not k.startswith("_")}


def tokenize(cmd: str):
    try:
        return shlex.split(cmd, posix=(os.name != "nt"))
    except ValueError:
        return cmd.split()


def fuzzy_fix(tokens):
    """Correct the program name and, if the program is known, the
    subcommand. Returns (fixed_command_str, confidence, explanation) or
    None.

    Only ever touches a token that ISN'T already a recognized valid
    command - either one of our known tools (TOOL_NAMES) or a common
    shell builtin (KNOWN_SAFE_COMMANDS, e.g. cd/cp/ps/grep). Without that
    guard, short real commands get "corrected" into unrelated tools purely
    because edit-distance ratios on short strings are noisy (e.g. 'cp'
    vs 'scp', 'ps' vs 'psql')."""
    if not tokens:
        return None
    prog = tokens[0]
    prog_key = prog.lower()
    fixed = list(tokens)
    changed = False
    confidence = 1.0
    notes = []

    if prog_key not in TOOL_NAMES and prog_key not in KNOWN_SAFE_COMMANDS:
        match = difflib.get_close_matches(prog_key, TOOL_NAMES, n=1, cutoff=0.6)
        if match:
            fixed[0] = match[0]
            prog_key = match[0]
            changed = True
            confidence = difflib.SequenceMatcher(None, prog.lower(), match[0]).ratio()
            notes.append(f"'{prog}' looked like '{match[0]}'")

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
                notes.append(f"'{sub}' looked like '{match[0]}'")

    if not changed:
        return None
    return quote_join(fixed), confidence, "; ".join(notes)


def main():
    ap = argparse.ArgumentParser(description="Offline shell-command typo & flag fixer")
    ap.add_argument("command", nargs="?", default="", help="the failed command, as one string")
    ap.add_argument("--shell", choices=["bash", "powershell", "cmd"], default="bash")
    ap.add_argument("--stderr-file", default=None, help="path to captured stderr from a controlled --rerun")
    ap.add_argument("--auto", action="store_true", help="auto-approve safe, high-confidence fixes")
    ap.add_argument("--dry-run", action="store_true", help="only print the suggestion, never ask to run it")
    args = ap.parse_args()

    raw = args.command.strip()
    if not raw:
        sys.stderr.write("fixcmd: no command given\n")
        sys.exit(1)

    tokens = tokenize(raw)

    stderr_text = ""
    if args.stderr_file and os.path.exists(args.stderr_file):
        try:
            stderr_text = Path(args.stderr_file).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    # 1) deterministic flag/pattern rules first - highest precision
    result = flag_rules.apply(raw, tokens, args.shell, stderr_text, VOCAB)
    # 2) fall back to fuzzy typo correction
    if result is None:
        result = fuzzy_fix(tokens)

    if result is None:
        sys.stderr.write(f"fixcmd: could not offline-fix: {raw}\n")
        sys.stderr.write("Try the AI version (fixai) for less common errors.\n")
        sys.exit(1)

    fixed_cmd, confidence, explanation = result
    if fixed_cmd.strip() == raw.strip():
        sys.stderr.write("fixcmd: no change needed\n")
        sys.exit(1)

    destructive = safety.is_destructive(fixed_cmd) or safety.is_destructive(raw)
    # Check safety against the FIXED tokens, not the original (possibly
    # misspelled) ones - "gti" isn't in vocab, "git" is.
    safe_sub = safety.is_safe_autorun(tokenize(fixed_cmd), VOCAB)

    sys.stderr.write(f"\nfixcmd suggests:\n  {fixed_cmd}\n")
    if explanation:
        sys.stderr.write(f"  ({explanation}, confidence {confidence:.0%})\n")
    if destructive:
        sys.stderr.write("  \u26a0  this touches a destructive/irreversible command\n")

    if args.dry_run:
        sys.exit(0)

    if args.auto and not destructive and safe_sub and confidence >= 0.85:
        sys.stderr.write("  auto-approved (safe + high confidence)\n")
        approve = True
    elif destructive:
        approve = safety.confirm("  Run it anyway? type 'yes' to confirm: ", require_word="yes")
    else:
        approve = safety.confirm("  Run it? [Y/n] ", default_yes=True)

    if approve:
        print(fixed_cmd)
        sys.exit(0)
    sys.stderr.write("  cancelled\n")
    sys.exit(2 if destructive else 1)


if __name__ == "__main__":
    main()
