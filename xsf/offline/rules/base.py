"""
xsf.offline.rules.base - Base class for deterministic rule plugins.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple
from xsf.core.command import Command


class Rule(ABC):
    """Abstract base class for all deterministic rule plugins."""
    name: str = "base_rule"
    priority: int = 100  # Lower number = higher priority

    @abstractmethod
    def match(self, cmd: Command) -> bool:
        """Returns True if this rule applies to the command."""
        pass

    @abstractmethod
    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        """
        Returns:
            (fixed_command_str, confidence, explanation)
            or None if no fix could be determined.
        """
        pass
