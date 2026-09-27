"""
xsf.offline.rules.base - Base class for deterministic rule plugins.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from xsf.core.command import Command


class Rule(ABC):
    """
    Abstract base class for all deterministic rule plugins.

    Attributes:
        name: Unique identifier for the rule plugin.
        priority: Priority integer (lower number = higher precedence; evaluated first).
        requires_output: If False, this rule can be evaluated purely from the command string
                         without needing command stderr/output or a rerun.
    """
    name: str = "base_rule"
    priority: int = 100
    requires_output: bool = True

    @abstractmethod
    def match(self, cmd: Command) -> bool:
        """Returns True if this rule applies to the command."""
        pass

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        """
        Returns a single best fix:
            (fixed_command_str, confidence, explanation)
            or None if no fix could be determined.
        """
        if type(self).get_candidates is not Rule.get_candidates:
            candidates = self.get_candidates(cmd)
            return candidates[0] if candidates else None
        return None

    def get_candidates(self, cmd: Command) -> List[Tuple[str, float, str]]:
        """
        Returns one or more candidate replacement commands:
            [(fixed_command_str, confidence, explanation), ...]
        Defaults to wrapping get_new_command for backward compatibility.
        """
        single = self.get_new_command(cmd)
        return [single] if single else []
