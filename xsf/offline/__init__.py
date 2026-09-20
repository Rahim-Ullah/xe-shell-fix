"""
xsf.offline - Offline heuristics, rule plugins, dynamic help parser, and vocabulary.
"""
from typing import Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules import evaluate_rules
from xsf.offline.fuzzy import fuzzy_match_command
from xsf.offline.help_parser import correct_flag_typos


def run_offline_engine(cmd: Command, allow_help_introspection: bool = True) -> Optional[Tuple[str, float, str]]:
    """
    Tier 1 Orchestrator:
      Tier 1a (<5ms):
        - Rule plugins (git, python, npm, docker, etc.)
        - Vocabulary fuzzy matcher (tool name & subcommand typos)
      Tier 1b (50-300ms, cached):
        - Dynamic --help flag introspection
    """
    # 1. Evaluate deterministic rule plugins
    rule_fix = evaluate_rules(cmd)
    if rule_fix:
        return rule_fix

    # 2. Evaluate vocabulary fuzzy matcher
    fuzzy_fix = fuzzy_match_command(cmd)
    if fuzzy_fix:
        return fuzzy_fix

    # 3. Evaluate dynamic --help flag introspection (if allowed and command has flags)
    if allow_help_introspection and any(t.startswith("-") for t in cmd.tokens):
        help_fix = correct_flag_typos(cmd)
        if help_fix:
            return help_fix

    return None
