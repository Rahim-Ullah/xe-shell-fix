"""
xsf.core.command - Canonical Command data representation.
"""
from dataclasses import dataclass, field
import os
import shlex
import sys
from typing import List, Optional


@dataclass
class Command:
    raw: str
    tokens: List[str] = field(default_factory=list)
    shell: str = "bash"  # powershell, bash, zsh, fish
    stderr_text: str = ""
    exit_code: Optional[int] = None
    cwd: str = field(default_factory=lambda: os.getcwd())

    def __post_init__(self):
        self.raw = self.raw.strip()
        if not self.tokens and self.raw:
            self.tokens = self._tokenize(self.raw, self.shell)

    @staticmethod
    def _tokenize(cmd_str: str, shell: str) -> List[str]:
        is_posix = shell in ("bash", "zsh", "fish") or (os.name != "nt")
        try:
            return shlex.split(cmd_str, posix=is_posix)
        except ValueError:
            return cmd_str.split()

    @property
    def program(self) -> str:
        return self.tokens[0] if self.tokens else ""

    @property
    def subcommand(self) -> str:
        return self.tokens[1] if len(self.tokens) > 1 else ""

    def quote_join(self, tokens: Optional[List[str]] = None) -> str:
        toks = tokens if tokens is not None else self.tokens
        if not toks:
            return ""
        
        # PowerShell and POSIX handle quotes differently
        if self.shell == "powershell":
            res = []
            for t in toks:
                if any(c in t for c in " \t$`()|;&<>"):
                    escaped = t.replace("`", "``").replace('"', '`"')
                    res.append(f'"{escaped}"')
                else:
                    res.append(t)
            return " ".join(res)
        else:
            return shlex.join(toks)
