"""
xsf.core - Core models, engine, and safety logic.
"""
from typing import Any
from xsf.core.command import Command
from xsf.core.safety import SafetyGuard, is_destructive


def __getattr__(name: str) -> Any:
    if name == "Engine":
        from xsf.core.engine import Engine
        return Engine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["Command", "Engine", "SafetyGuard", "is_destructive"]
