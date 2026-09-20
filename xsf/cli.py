"""
xsf.cli - Main Command-Line Interface.

Usage:
  xsf "<failed_command>" [options]
  xsf init <powershell|bash|zsh|fish>
  xsf config [--list]
"""
import argparse
import os
from pathlib import Path
import sys

from xsf import __version__
from xsf.config import load_config
from xsf.core.command import Command
from xsf.core.engine import Engine
from xsf.hooks import get_hook_script, SUPPORTED_SHELLS
from xsf.ui.config_tui import run_interactive_tui, print_status


def main() -> int:
    argv = sys.argv[1:]

    # Quick flag checks
    if "-v" in argv or "--version" in argv:
        print(f"xsf {__version__}")
        return 0

    # Dedicated subcommands
    if argv and argv[0] in ("init", "config", "ui"):
        sub = argv[0]
        if sub == "init":
            if len(argv) < 2 or argv[1] not in SUPPORTED_SHELLS:
                sys.stderr.write(f"xsf: usage: xsf init <{'|'.join(SUPPORTED_SHELLS)}>\n")
                return 1
            try:
                script = get_hook_script(argv[1])
                sys.stdout.write(script)
                sys.stdout.flush()
                return 0
            except Exception as e:
                sys.stderr.write(f"xsf: {e}\n")
                return 1

        elif sub in ("config", "ui"):
            cfg = load_config()
            if "--list" in argv or "-l" in argv:
                print_status(cfg)
                return 0
            run_interactive_tui()
            return 0

    # Repair command parsing
    parser = argparse.ArgumentParser(
        prog="xsf",
        description="xe-shell-fix (xsf): Universal, resilient shell command auto-repair assistant.",
    )
    parser.add_argument("command", nargs="?", default="", help="The failed command string to diagnose and fix")
    parser.add_argument("--shell", choices=["powershell", "pwsh", "bash", "gitbash", "zsh", "fish"], default="bash", help="Calling shell dialect")
    parser.add_argument("--stderr-file", default=None, help="Path to captured stderr text from controlled rerun")
    parser.add_argument("--offline", action="store_true", help="Force offline heuristics and rule plugins only")
    parser.add_argument("--ai", action="store_true", help="Query AI providers directly without offline rules")
    parser.add_argument("--auto", action="store_true", help="Auto-approve safe high-confidence fixes")
    parser.add_argument("--dry-run", action="store_true", help="Diagnose and print suggestion without execution")
    parser.add_argument("--no-cache", action="store_true", help="Bypass local AI query cache")

    args = parser.parse_args(argv)

    raw_cmd = (args.command or "").strip()
    if not raw_cmd:
        sys.stderr.write("xsf: no command provided to fix. Run 'xsf --help' for usage.\n")
        return 1

    stderr_content = ""
    if args.stderr_file and os.path.exists(args.stderr_file):
        try:
            stderr_content = Path(args.stderr_file).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    cmd = Command(
        raw=raw_cmd,
        shell=args.shell,
        stderr_text=stderr_content,
    )

    cfg = load_config()
    engine = Engine(cfg)

    return engine.execute_flow(
        cmd=cmd,
        auto_approve=args.auto,
        dry_run=args.dry_run,
        offline_only=args.offline,
        ai_only=args.ai,
        skip_cache=args.no_cache,
    )


def cli_entry():
    sys.exit(main())


if __name__ == "__main__":
    cli_entry()
