"""
xsf.offline.rules.user_rules - Dynamic loader for user and team custom rules (~/.shellfix/rules/).

Supports both:
  1. Class-based rules inheriting from xsf.offline.rules.base.Rule
  2. thefuck-compatible function-based rules implementing:
       def match(cmd) -> bool
       def get_new_command(cmd) -> str | tuple | list
       (optional: priority = 50, requires_output = True)
"""
import importlib.util
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules.base import Rule
from xsf.config import CONFIG_DIR, secure_config_permissions

DEFAULT_USER_RULES_DIR = CONFIG_DIR / "rules"


class FunctionRuleAdapter(Rule):
    """
    Adapter enabling thefuck-style function-based rules:
      def match(command) -> bool
      def get_new_command(command) -> str | tuple | list
    """

    def __init__(self, name: str, match_fn: Any, fix_fn: Any, priority: int = 50, requires_output: bool = True):
        self.name = name
        self.priority = priority
        self.requires_output = requires_output
        self._match_fn = match_fn
        self._fix_fn = fix_fn

    def match(self, cmd: Command) -> bool:
        try:
            return bool(self._match_fn(cmd))
        except Exception:
            return False

    def get_candidates(self, cmd: Command) -> List[Tuple[str, float, str]]:
        try:
            raw_result = self._fix_fn(cmd)
        except Exception:
            return []

        if not raw_result:
            return []

        # Handle list of results
        if isinstance(raw_result, list):
            candidates = []
            for item in raw_result:
                cand = self._normalize_candidate(item)
                if cand:
                    candidates.append(cand)
            return candidates

        # Handle single result
        cand = self._normalize_candidate(raw_result)
        return [cand] if cand else []

    def _normalize_candidate(self, item: Any) -> Optional[Tuple[str, float, str]]:
        if isinstance(item, tuple) and len(item) == 3:
            return str(item[0]), float(item[1]), str(item[2])
        elif isinstance(item, tuple) and len(item) == 2:
            return str(item[0]), float(item[1]), f"Custom rule '{self.name}'"
        elif isinstance(item, str):
            return item.strip(), 0.90, f"Custom rule '{self.name}'"
        return None


# Module-level cache to prevent repeated disk I/O on unchanged files
_CACHE: Dict[str, Any] = {
    "mtime": 0.0,
    "rules": [],
}


def get_user_rules_dir(custom_path: Optional[str] = None) -> Path:
    """Returns the resolved user rules directory, checking env var and custom config."""
    if custom_path:
        return Path(custom_path).expanduser().resolve()
    env_dir = os.environ.get("XSF_CUSTOM_RULES_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()
    return DEFAULT_USER_RULES_DIR


def load_user_rules(rules_dir: Optional[Path] = None, force_reload: bool = False) -> List[Rule]:
    """
    Scans rules_dir for .py files and loads custom rules with error isolation.
    Returns list of instantiated Rule objects sorted by priority.
    """
    target_dir = rules_dir or get_user_rules_dir()
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    # Check directory mtime for fast cache hit (<0.1ms)
    try:
        current_mtime = target_dir.stat().st_mtime
    except Exception:
        current_mtime = 0.0

    if not force_reload and _CACHE["rules"] and current_mtime == _CACHE["mtime"]:
        return _CACHE["rules"]

    # Secure permissions on user rules directory cross-platform
    try:
        secure_config_permissions(target_dir)
    except Exception:
        pass

    loaded_rules: List[Rule] = []

    for file_path in sorted(target_dir.glob("*.py")):
        if file_path.name.startswith(("_", ".")):
            continue

        module_name = f"xsf_user_rule_{file_path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, str(file_path))
            if not spec or not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # 1. Search for Rule subclasses
            found_class = False
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, Rule)
                    and attr is not Rule
                    and attr is not FunctionRuleAdapter
                ):
                    rule_instance = attr()
                    loaded_rules.append(rule_instance)
                    found_class = True

            # 2. Search for thefuck-style function rules
            if not found_class:
                match_fn = getattr(module, "match", None)
                fix_fn = getattr(module, "get_new_command", None) or getattr(module, "get_candidates", None)
                if callable(match_fn) and callable(fix_fn):
                    priority = getattr(module, "priority", 50)
                    requires_output = getattr(module, "requires_output", True)
                    adapter = FunctionRuleAdapter(
                        name=file_path.stem,
                        match_fn=match_fn,
                        fix_fn=fix_fn,
                        priority=priority,
                        requires_output=requires_output,
                    )
                    loaded_rules.append(adapter)

        except Exception as e:
            # Error isolation: a broken user rule must never crash xsf
            if os.environ.get("XSF_DEBUG"):
                sys.stderr.write(f"xsf: error loading custom rule '{file_path.name}': {e}\n")

    _CACHE["mtime"] = current_mtime
    _CACHE["rules"] = loaded_rules
    return loaded_rules
