"""
xsf.offline.rules.ssh_net_rules - Network, SSH, and connectivity error recovery.
"""
import re
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule


class SSHConnectionRefusedRule(Rule):
    """Detects SSH 'Connection refused' and provides guidance."""
    name = "ssh_connection_refused"
    priority = 20

    def match(self, cmd: Command) -> bool:
        return "Connection refused" in cmd.stderr_text and cmd.tokens and cmd.tokens[0] in ("ssh", "scp", "sftp")

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        # Can't auto-fix a refused connection, but can suggest checking sshd
        return None  # Let AI handle this — it's a server-side issue


class SSHHostKeyVerificationRule(Rule):
    """Detects SSH 'Host key verification failed' and suggests removing the offending key."""
    name = "ssh_host_key_verification"
    priority = 21

    def match(self, cmd: Command) -> bool:
        return "Host key verification failed" in cmd.stderr_text

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        # Try to extract the offending key line from ssh's verbose output
        match = re.search(r"Offending .+ key in (.+):(\d+)", cmd.stderr_text)
        if match:
            file_path = match.group(1)
            line_num = match.group(2)
            return f"sed -i '{line_num}d' {file_path}", 0.80, f"Remove offending host key at {file_path}:{line_num}"
        # Fallback: try to extract hostname and use ssh-keygen
        host_match = re.search(r"(?:ssh|scp|sftp)\s+(?:\S+@)?(\S+)", cmd.raw)
        if host_match:
            host = host_match.group(1)
            return f"ssh-keygen -R {host}", 0.80, f"Remove all keys for '{host}' from known_hosts"
        return None


class CurlConnectionFailedRule(Rule):
    """Detects curl connection failures."""
    name = "curl_connection_failed"
    priority = 22

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text
        return cmd.tokens and cmd.tokens[0] == "curl" and ("curl: (7)" in err or "curl: (6)" in err or "Failed to connect" in err)

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        if "curl: (6)" in cmd.stderr_text:
            # DNS resolution error
            return None  # Can't auto-fix DNS
        # Connection refused — try with -v for debugging
        if "-v" not in cmd.raw and "--verbose" not in cmd.raw:
            return f"{cmd.raw} -v", 0.70, "Connection failed. Adding -v for verbose debugging output."
        return None


class DNSResolutionFailedRule(Rule):
    """Detects DNS resolution failures across tools."""
    name = "dns_resolution_failed"
    priority = 23

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text
        return "Could not resolve host" in err or "Name or service not known" in err or "Temporary failure in name resolution" in err

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        return None  # Can't auto-fix DNS — let AI provide guidance


class SSLCertificateErrorRule(Rule):
    """Detects SSL/TLS certificate verification failures."""
    name = "ssl_certificate_error"
    priority = 24

    def match(self, cmd: Command) -> bool:
        err = cmd.stderr_text.lower()
        return "ssl certificate problem" in err or "certificate verify failed" in err

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        if cmd.tokens and cmd.tokens[0] == "curl":
            return f"{cmd.raw} -k", 0.70, "SSL certificate issue. Adding -k to skip verification (use with caution)."
        if cmd.tokens and cmd.tokens[0] in ("pip", "pip3"):
            return f"{cmd.raw} --trusted-host pypi.org --trusted-host files.pythonhosted.org", 0.70, "SSL issue with pip. Adding trusted hosts."
        return None
