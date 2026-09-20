"""
xsf.offline.rules.python_rules - Python, venv, and pip pattern rules.
"""
from pathlib import Path
import re
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule

PYTHON_MODULE_TOOLS = {
    "venv", "pip", "pytest", "unittest", "http.server", "json.tool",
    "cProfile", "timeit", "pdb", "zipfile", "tarfile", "ensurepip",
}


class PythonMissingModuleFlagRule(Rule):
    """Detects `python venv .venv` and converts to `python -m venv .venv`."""
    name = "python_missing_m"
    priority = 10

    def match(self, cmd: Command) -> bool:
        if len(cmd.tokens) >= 2 and cmd.tokens[0].lower() in ("python", "python3", "py"):
            return cmd.tokens[1].lower() in PYTHON_MODULE_TOOLS
        return False

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        new_tokens = [cmd.tokens[0], "-m"] + cmd.tokens[1:]
        return (
            cmd.quote_join(new_tokens),
            1.0,
            f"Added missing '-m' flag for python module '{cmd.tokens[1]}'",
        )


class VenvActivationRule(Rule):
    """Detects failed venv activation commands and suggests the shell-specific syntax."""
    name = "venv_activation"
    priority = 15

    def match(self, cmd: Command) -> bool:
        raw = cmd.raw.lower()
        return "activate" in raw and ("venv" in raw or ".venv" in raw or "env" in raw)

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        shell = cmd.shell.lower()
        # Look for common venv folder names in cwd
        venv_candidates = [".venv", "venv", "env", ".env"]
        venv_dir = ".venv"
        for candidate in venv_candidates:
            if Path(candidate).is_dir():
                venv_dir = candidate
                break

        if shell == "powershell":
            fixed = f".\\{venv_dir}\\Scripts\\Activate.ps1"
            explanation = f"PowerShell activation script for '{venv_dir}'"
        elif shell == "fish":
            fixed = f"source {venv_dir}/bin/activate.fish"
            explanation = f"Fish activation script for '{venv_dir}'"
        else:  # bash, zsh, gitbash
            # On Windows Git Bash, it might be in Scripts
            if Path(f"{venv_dir}/Scripts/activate").exists():
                fixed = f"source {venv_dir}/Scripts/activate"
            else:
                fixed = f"source {venv_dir}/bin/activate"
            explanation = f"POSIX source activation for '{venv_dir}'"

        return fixed, 0.95, explanation
