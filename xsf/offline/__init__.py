"""
xsf.offline - Offline heuristics, rule plugins, dynamic help parser, and vocabulary.
"""
from typing import List, Optional, Tuple

from xsf.core.command import Command
from xsf.offline.rules import evaluate_rules, get_all_rule_candidates
from xsf.offline.fuzzy import fuzzy_match_command, VOCAB, KNOWN_SAFE_COMMANDS
from xsf.offline.help_parser import correct_flag_typos


def _is_partial_fix_superseded(candidate: str, all_candidates: List[str], original_tokens: List[str]) -> bool:
    """
    Returns True when this candidate is a partial fix — program name corrected but
    subcommand is still a typo — while a more complete fix already exists in the list.

    Example: 'git statusu' is dropped when 'git status' is also a candidate because
    CommonShellTyposRule fixed 'giit'→'git' but left 'statusu' untouched, while
    the fuzzy matcher correctly fixed both.
    """
    cand_tokens = candidate.split()
    if len(cand_tokens) < 2:
        return False

    cand_prog = cand_tokens[0].lower()
    cand_sub = cand_tokens[1].lower()

    # Only consider candidates where the program name was corrected vs the original
    orig_prog = original_tokens[0].lower() if original_tokens else ""
    if cand_prog == orig_prog:
        return False  # Program unchanged — not a partial-fix pattern

    if cand_prog not in VOCAB:
        return False

    known_subs = [s.lower() for s in VOCAB[cand_prog].get("subcommands", [])]
    if not known_subs:
        return False

    # The subcommand still looks like a typo (not in known list and not a safe command)
    if cand_sub in known_subs or cand_sub in KNOWN_SAFE_COMMANDS or cand_sub.startswith("-"):
        return False  # Subcommand is already valid — keep this candidate

    # Check whether another candidate fully fixes the same program + provides a valid subcommand
    for other in all_candidates:
        if other == candidate:
            continue
        other_toks = other.split()
        if (
            len(other_toks) >= 2
            and other_toks[0].lower() == cand_prog
            and other_toks[1].lower() in known_subs
        ):
            return True  # Better fix exists — suppress the partial one
    return False


def get_offline_candidates(cmd: Command, allow_help_introspection: bool = True) -> List[Tuple[str, float, str]]:
    """
    Tier 1 Candidate Collector:
      Collects candidate fixes across deterministic rules, fuzzy vocabulary matcher,
      and dynamic help introspection. Filters out partial program-name-only fixes
      when a more complete correction also exists (e.g. 'git statusu' suppressed
      when 'git status' is already in the list).
    """
    candidates: List[Tuple[str, float, str]] = []
    seen = set()

    # 1. Evaluate deterministic rule plugins (both built-in and user custom)
    for cand in get_all_rule_candidates(cmd):
        fixed_str = cand[0].strip()
        if fixed_str not in seen:
            candidates.append(cand)
            seen.add(fixed_str)

    # 2. Evaluate vocabulary fuzzy matcher
    fuzzy_fix = fuzzy_match_command(cmd)
    if fuzzy_fix and fuzzy_fix[0].strip() not in seen:
        candidates.append(fuzzy_fix)
        seen.add(fuzzy_fix[0].strip())

    # 3. Evaluate dynamic --help flag introspection
    if allow_help_introspection and any(t.startswith("-") for t in cmd.tokens):
        help_fix = correct_flag_typos(cmd)
        if help_fix and help_fix[0].strip() not in seen:
            candidates.append(help_fix)
            seen.add(help_fix[0].strip())

    # 4. Post-filter: drop partial fixes that are superseded by a more complete fix
    if len(candidates) > 1:
        all_cmds = [c[0].strip() for c in candidates]
        original_tokens = cmd.tokens
        candidates = [
            c for c in candidates
            if not _is_partial_fix_superseded(c[0].strip(), all_cmds, original_tokens)
        ]

    return candidates


def run_offline_engine(cmd: Command, allow_help_introspection: bool = True) -> Optional[Tuple[str, float, str]]:
    """
    Tier 1 Orchestrator:
    Returns the highest-priority/highest-confidence offline fix.
    """
    candidates = get_offline_candidates(cmd, allow_help_introspection=allow_help_introspection)
    return candidates[0] if candidates else None
