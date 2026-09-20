"""
xsf.offline.rules.stderr_rules - Stderr-driven error recovery rules.

These rules examine cmd.stderr_text to diagnose and fix common error patterns
from command output like 'command not found', 'ModuleNotFoundError', etc.
"""
import re
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule


class NoSuchFileOrDirRule(Rule):
    """Detects 'No such file or directory' errors and suggests mkdir for cd commands."""
    name = "no_such_file_or_directory"
    priority = 9

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text.lower()
        return "no such file or directory" in err and cmd.tokens and cmd.tokens[0] == "cd" and len(cmd.tokens) > 1

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        dir_name = cmd.tokens[1]
        return f"mkdir -p {dir_name} && cd {dir_name}", 0.85, f"Directory '{dir_name}' doesn't exist. Create and enter it."


class PythonModuleNotFoundRule(Rule):
    """Detects Python ModuleNotFoundError and suggests pip install."""
    name = "python_module_not_found"
    priority = 10

    def match(self, cmd: Command) -> bool:
        return "ModuleNotFoundError: No module named" in cmd.stderr_text

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", cmd.stderr_text)
        if match:
            module_name = match.group(1).split('.')[0]  # top-level package
            return f"pip install {module_name}", 0.85, f"Module '{module_name}' not found. Install it with pip."
        return None


class GitNotARepoRule(Rule):
    """Detects 'fatal: not a git repository' and suggests git init."""
    name = "git_not_a_repo"
    priority = 11

    def match(self, cmd: Command) -> bool:
        return "fatal: not a git repository" in cmd.stderr_text.lower()

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "git init", 0.85, "Not a git repository. Initialize one with 'git init'."


class PipExternallyManagedRule(Rule):
    """Detects pip 'externally-managed-environment' error."""
    name = "pip_externally_managed"
    priority = 12

    def match(self, cmd: Command) -> bool:
        return "externally-managed-environment" in cmd.stderr_text and cmd.tokens and cmd.tokens[0] in ("pip", "pip3")

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return f"{cmd.raw} --break-system-packages", 0.80, "Environment is externally managed. Adding --break-system-packages flag."


class NodeModuleNotFoundRule(Rule):
    """Detects Node.js 'Cannot find module' or 'MODULE_NOT_FOUND' errors."""
    name = "node_module_not_found"
    priority = 13

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text
        return ("Cannot find module" in err or "MODULE_NOT_FOUND" in err) and cmd.tokens

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return "npm install", 0.80, "Node modules missing. Run 'npm install' to install dependencies."


class PortInUseRule(Rule):
    """Detects 'Address already in use' or 'EADDRINUSE' errors."""
    name = "port_in_use"
    priority = 14

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text
        return "EADDRINUSE" in err or "Address already in use" in err

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        # Try to extract port number
        match = re.search(r"(?:port\s+|:)(\d{2,5})", cmd.stderr_text, re.IGNORECASE)
        if match:
            port = match.group(1)
            return f"lsof -i :{port}", 0.80, f"Port {port} is in use. Find the process with 'lsof -i :{port}'."
        return None


class TypeErrorMissingArgRule(Rule):
    """Detects Python TypeError for missing positional arguments."""
    name = "python_missing_arg"
    priority = 15

    def match(self, cmd: Command) -> bool:
        return "TypeError:" in cmd.stderr_text and "required positional argument" in cmd.stderr_text

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return None  # Advisory only — let AI handle complex Python errors


class FilePermissionDeniedRule(Rule):
    """Detects 'Permission denied' errors and suggests sudo (POSIX) or admin (Windows)."""
    name = "file_permission_denied"
    priority = 16

    def match(self, cmd: Command) -> bool:
        if cmd.shell in ("powershell",):
            return False
        err = cmd.stderr_text.lower()
        if not cmd.tokens:
            return False
        return ("permission denied" in err or "operation not permitted" in err) and cmd.tokens[0] != "sudo"

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return f"sudo {cmd.raw}", 0.80, "Permission denied. Retry with sudo."
