"""
xsf.offline.rules.env_rules - Environment, dependency, and installation error recovery.
"""
import re
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule


class PythonVenvNotFoundRule(Rule):
    """Detects 'No module named venv' and suggests installing python3-venv."""
    name = "python_venv_not_found"
    priority = 15

    def match(self, cmd: Command) -> bool:
        return "No module named venv" in cmd.stderr_text

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "sudo apt install python3-venv", 0.80, "python3-venv module missing. Install it with 'apt install python3-venv'."


class NpmPermissionRule(Rule):
    """Detects npm EACCES permission errors during install."""
    name = "npm_eacces"
    priority = 16

    def match(self, cmd: Command) -> bool:
        return "EACCES" in cmd.stderr_text and cmd.tokens and cmd.tokens[0] in ("npm", "pnpm", "yarn")

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return f"sudo {cmd.raw}", 0.75, "npm permission denied (EACCES). Try with sudo or use nvm."


class EnvVariableNotSetRule(Rule):
    """Detects 'is not set' or 'undefined variable' errors in stderr."""
    name = "env_variable_not_set"
    priority = 17

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text.lower()
        return "is not set" in err or "undefined variable" in err or "unbound variable" in err

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        # Try to extract the variable name
        match = re.search(r"(?:^|\s)([A-Z][A-Z0-9_]{1,}):?\s*(?:is not set|undefined|unbound)", cmd.stderr_text, re.IGNORECASE | re.MULTILINE)
        if match:
            var_name = match.group(1)
            return f"export {var_name}=<value> && {cmd.raw}", 0.75, f"Variable '{var_name}' is not set. Export it first."
        return None


class RustCompilerNotFoundRule(Rule):
    """Detects 'rustc' or 'cargo' not found and suggests installing Rust."""
    name = "rust_not_found"
    priority = 18

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text.lower()
        return ("rustc" in err or "cargo" in err) and ("not found" in err or "is not recognized" in err)

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh", 0.80, "Rust toolchain not found. Install via rustup."
