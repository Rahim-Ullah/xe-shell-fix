#!/usr/bin/env python3
"""
fixcmd_ai.py - AI-assisted command fixer (Gemini by default, free tier).

Same stdout/stderr contract as the offline engine (fixcmd.py) - read that
docstring if you haven't. Short version: stdout gets nothing, or exactly
one approved corrected command; everything else goes to stderr; the shell
hook is what actually executes the approved command, not this script.

Exit codes: 0 = approved fix on stdout
            1 = no fix / declined / not configured
            2 = destructive fix found, not approved

Standalone testing (no shell hook, no API key needed to see the error path):
    python fixcmd_ai.py "some broken command" --dry-run
"""
import argparse
import os
import sys
from pathlib import Path

HOME = Path(__file__).resolve().parent
sys.path.insert(0, str(HOME))
import cache        # noqa: E402
import providers     # noqa: E402
import safety         # noqa: E402


def load_config() -> dict:
    cfg = {"provider": "gemini", "model": "gemini-2.5-flash", "api_key": None}
    cfg_file = Path.home() / ".shellfix" / "config.toml"
    if cfg_file.exists():
        try:
            import tomllib  # Python 3.11+
            with open(cfg_file, "rb") as f:
                cfg.update(tomllib.load(f))
        except ModuleNotFoundError:
            sys.stderr.write(
                "fixcmd-ai: found ~/.shellfix/config.toml but this Python is "
                "older than 3.11 (no tomllib) - use the GEMINI_API_KEY env "
                "var instead, or upgrade Python.\n"
            )
        except Exception as e:
            sys.stderr.write(f"fixcmd-ai: couldn't parse config.toml: {e}\n")

    env_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("SHELLFIX_API_KEY")
    if env_key:
        cfg["api_key"] = env_key
    return cfg


def main():
    ap = argparse.ArgumentParser(description="AI-assisted shell-command fixer")
    ap.add_argument("command", nargs="?", default="", help="the failed command, as one string")
    ap.add_argument("--shell", choices=["bash", "powershell", "cmd"], default="bash")
    ap.add_argument("--stderr-file", default=None, help="path to captured stderr from a controlled --rerun")
    ap.add_argument("--auto", action="store_true", help="auto-approve non-destructive, high-confidence fixes")
    ap.add_argument("--dry-run", action="store_true", help="only print the suggestion, never ask to run it")
    ap.add_argument("--no-cache", action="store_true", help="skip the local cache, always call the API")
    args = ap.parse_args()

    raw = args.command.strip()
    if not raw:
        sys.stderr.write("fixcmd-ai: no command given\n")
        sys.exit(1)

    stderr_text = ""
    if args.stderr_file and os.path.exists(args.stderr_file):
        try:
            stderr_text = Path(args.stderr_file).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    cfg = load_config()
    if not cfg.get("api_key"):
        sys.stderr.write(
            "fixcmd-ai: no API key configured.\n"
            "  Set GEMINI_API_KEY, or put api_key = \"...\" in ~/.shellfix/config.toml\n"
            "  Free key, no card required: https://aistudio.google.com/apikey\n"
        )
        sys.exit(1)

    cache_key = cache.make_key(raw, stderr_text, args.shell)
    cached = None if args.no_cache else cache.get(cache_key)

    if cached:
        fixed_cmd = cached["command"]
        explanation = cached.get("explanation", "")
        confidence = float(cached.get("confidence", 0.5))
        sys.stderr.write("  (from local cache, no API call made)\n")
    else:
        try:
            provider = providers.get_provider(cfg)
            fixed_cmd, explanation, confidence = provider.fix(raw, stderr_text, args.shell)
        except providers.ProviderError as e:
            sys.stderr.write(f"fixcmd-ai: {e}\n")
            sys.exit(1)
        if fixed_cmd:
            cache.put(cache_key, fixed_cmd, explanation, confidence)

    if not fixed_cmd or fixed_cmd.strip() == raw.strip():
        sys.stderr.write("fixcmd-ai: model found no confident fix\n")
        sys.exit(1)

    destructive = safety.is_destructive(fixed_cmd) or safety.is_destructive(raw)

    sys.stderr.write(f"\nfixcmd-ai suggests:\n  {fixed_cmd}\n")
    if explanation:
        sys.stderr.write(f"  {explanation} (confidence {confidence:.0%})\n")
    if destructive:
        sys.stderr.write("  \u26a0  this touches a destructive/irreversible command\n")

    if args.dry_run:
        sys.exit(0)

    if args.auto and not destructive and confidence >= 0.8:
        sys.stderr.write("  auto-approved (non-destructive + high confidence)\n")
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
