"""
xsf.core.engine - Master Execution Orchestrator.

Implements the 3-Tier Resolution Pipeline:
  Tier 1a: Instant Offline Rules & Vocabulary (<5ms)
  Tier 1b: Dynamic Help Introspector (50-300ms, Cached)
  Tier 2: Local LLM (Opt-in)
  Tier 3: Cloud AI Cascade (Gemini -> OpenRouter -> Opt-in)
  ══════════════════════════════════════════════════════════
  UNIVERSAL SAFETY GATE: All output must pass safety.py
"""
import sys
from typing import Any, Dict, List, Optional, Tuple

from xsf.core.command import Command
from xsf.core.safety import SafetyGuard
from xsf.offline import run_offline_engine
from xsf.ai.router import AIRouter


def check_already_resolved(cmd: Command) -> Optional[str]:
    """
    Checks if the command failed because the target is ALREADY in the desired state.
    Examples:
      - 'rm: cannot remove ...: No such file or directory'
      - 'kill: ...: No such process'
      - 'mkdir: cannot create directory ...: File exists'
    Returns an informative message if no action is needed, else None.
    """
    if not cmd.tokens:
        return None

    prog = cmd.tokens[0].lower()
    err = (cmd.stderr_text or "").lower()

    # 1. Removal/Deletion of already nonexistent file or directory
    if prog in ("rm", "del", "delete", "unlink", "rmdir", "remove-item"):
        target = cmd.tokens[1] if len(cmd.tokens) > 1 else ""
        target_clean = target.strip('\'"')

        # Check if stderr explicitly indicated the file/path was missing
        has_err_signal = any(p in err for p in (
            "no such file or directory", "cannot remove", "cannot find the path",
            "cannot find the file", "does not exist", "not found"
        ))

        # Check if target path does not exist on disk (even when stderr was not piped)
        target_missing_on_disk = False
        if target_clean and not any(c in target_clean for c in "*?"):
            from pathlib import Path
            try:
                target_missing_on_disk = not Path(target_clean).exists()
            except Exception:
                target_missing_on_disk = False

        if has_err_signal or target_missing_on_disk:
            name_display = target_clean or "target"
            return f"Target '{name_display}' does not exist (already removed). No command needed."

    # 2. Kill of already terminated process
    if prog in ("kill", "killall", "pkill", "stop-process"):
        if any(p in err for p in ("no such process", "cannot find a process", "not found")):
            return "Target process is already terminated. No command needed."

    # 3. Directory creation where directory already exists
    if prog in ("mkdir", "md"):
        if "file exists" in err or "already exists" in err:
            target = cmd.tokens[1] if len(cmd.tokens) > 1 else "directory"
            return f"Directory '{target}' already exists. No command needed."

    return None


def is_futile_fix(cmd: Command, proposed: str) -> bool:
    """Rejects fixes that are identical to the failed command or repeat a futile action."""
    if not proposed or not proposed.strip():
        return True

    clean_raw = cmd.raw.strip()
    clean_prop = proposed.strip()
    if clean_raw == clean_prop:
        return True

    raw_tokens = [t.strip('\'"') for t in cmd.tokens]
    prop_tokens = [t.strip('\'"') for t in Command(clean_prop).tokens]
    if raw_tokens == prop_tokens:
        return True

    return False


class Engine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_router = AIRouter(config)
        self.allow_help = config.get("general", {}).get("help_introspection", True)
        self.auto_approve_safe = config.get("general", {}).get("auto_approve_safe", False)

    def find_candidates(
        self,
        cmd: Command,
        offline_only: bool = False,
        ai_only: bool = False,
        skip_cache: bool = False,
    ) -> List[Tuple[str, float, str, str]]:
        """
        Gathers all candidate fixes across tiers.
        Returns: [(fixed_command, confidence, explanation, tier_source), ...]
        """
        candidates: List[Tuple[str, float, str, str]] = []
        seen = set()

        # 1. AI-Only path (if explicitly requested)
        if ai_only:
            ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
            if ai_result and not is_futile_fix(cmd, ai_result[0]):
                fixed, conf, exp = ai_result
                return [(fixed, conf, exp, "ai")]
            return []

        # 2. Tier 1: Primary offline engine result
        primary_offline = run_offline_engine(cmd, allow_help_introspection=self.allow_help)
        if primary_offline and not is_futile_fix(cmd, primary_offline[0]):
            candidates.append((primary_offline[0], primary_offline[1], primary_offline[2], "offline"))
            seen.add(primary_offline[0].strip())

        # Collect additional offline candidates if available
        try:
            from xsf.offline import get_offline_candidates
            for item in get_offline_candidates(cmd, allow_help_introspection=self.allow_help):
                if item[0].strip() not in seen and not is_futile_fix(cmd, item[0]):
                    candidates.append((item[0], item[1], item[2], "offline"))
                    seen.add(item[0].strip())
        except Exception:
            pass

        # If high-confidence offline match exists (>= 0.85), skip AI call
        if candidates and (candidates[0][1] >= 0.85 or offline_only):
            return candidates

        if offline_only:
            return candidates

        # 3. Tier 2 / 3: AI Engine Fallback
        ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
        if ai_result and not is_futile_fix(cmd, ai_result[0]):
            fixed, conf, exp = ai_result
            if fixed.strip() not in seen:
                candidates.append((fixed, conf, exp, "ai"))
                seen.add(fixed.strip())

        return candidates

    def find_fix(
        self,
        cmd: Command,
        offline_only: bool = False,
        ai_only: bool = False,
        skip_cache: bool = False,
    ) -> Optional[Tuple[str, float, str, str]]:
        """
        Finds the best corrected command across tiers.
        Returns: (fixed_command, confidence, explanation, tier_source) or None
        """
        # 1. AI-Only path (if explicitly requested)
        if ai_only:
            ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
            if ai_result and not is_futile_fix(cmd, ai_result[0]):
                fixed, conf, exp = ai_result
                return fixed, conf, exp, "ai"
            return None

        # 2. Tier 1: Offline Engine (Rules -> Vocabulary -> Help Introspector)
        offline_result = run_offline_engine(cmd, allow_help_introspection=self.allow_help)
        if offline_result and is_futile_fix(cmd, offline_result[0]):
            offline_result = None

        if offline_result:
            fixed, conf, exp = offline_result
            # If high confidence offline match, return immediately without network call
            if conf >= 0.85 or offline_only:
                return fixed, conf, exp, "offline"

        if offline_only:
            return None

        # 3. Tier 2 / 3: AI Engine Fallback
        ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
        if ai_result and is_futile_fix(cmd, ai_result[0]):
            ai_result = None

        if ai_result:
            fixed, conf, exp = ai_result
            return fixed, conf, exp, "ai"

        # Fallback to lower confidence offline result if AI also had no fix
        if offline_result:
            fixed, conf, exp = offline_result
            return fixed, conf, exp, "offline"

        return None

    def execute_flow(
        self,
        cmd: Command,
        auto_approve: bool = False,
        dry_run: bool = False,
        offline_only: bool = False,
        ai_only: bool = False,
        skip_cache: bool = False,
    ) -> int:
        """
        Runs diagnosis, displays prompt on stderr, prompts confirmation,
        and outputs approved command to stdout.

        Confirmation strategy:
          - Single candidate: show suggestion then confirm (Enter/y=run, n=decline;
            destructive requires typing full 'yes').
          - Multi-candidate (arrow-key): selecting with Enter IS the confirmation
            for safe commands — no redundant double-confirm. Destructive commands
            still gate with an explicit 'yes' even after selection.

        Returns exit code:
          0 = fix approved and written to stdout (or already resolved)
          1 = no fix found or declined
          2 = destructive fix declined
        """
        # 1. Check if the command failed because the target is ALREADY in the desired state
        already_resolved_msg = check_already_resolved(cmd)
        if already_resolved_msg:
            sys.stderr.write(f"\n  \033[1;33m[INFO]\033[0m {already_resolved_msg}\n")
            return 0

        candidates = self.find_candidates(
            cmd,
            offline_only=offline_only,
            ai_only=ai_only,
            skip_cache=skip_cache,
        )

        if not candidates:
            sys.stderr.write("xsf: no fix found for previous command\n")
            return 1

        if len(candidates) == 1:
            chosen = candidates[0]
            fixed_cmd, confidence, explanation, source = chosen
            # Display suggestion to user on STDERR (keeping stdout clean for eval)
            sys.stderr.write("\n")
            badge = "\033[1;32m[OFFLINE]\033[0m" if source == "offline" else "\033[1;36m[AI]\033[0m"
            sys.stderr.write(f"  {badge} \033[1m{fixed_cmd}\033[0m\n")
            if explanation:
                try:
                    sys.stderr.write(f"  \033[90m\u2514\u2500 {explanation} (confidence: {int(confidence * 100)}%)\033[0m\n")
                except UnicodeEncodeError:
                    sys.stderr.write(f"  \033[90m\\-- {explanation} (confidence: {int(confidence * 100)}%)\033[0m\n")
            # Single candidate: pass through safety gate (Enter/y for safe, full "yes" for destructive)
            auto_flag = auto_approve or (self.auto_approve_safe and confidence >= 0.95)
            approved = SafetyGuard.confirm(fixed_cmd, auto_approve=auto_flag, dry_run=dry_run)
        else:
            # Multi-candidate: user navigates with arrow keys and presses Enter to select.
            # The selection itself IS confirmation for safe commands — no redundant double-prompt.
            from xsf.ui.selector import choose_candidate
            chosen = choose_candidate(candidates)
            if not chosen:
                return 1
            fixed_cmd, confidence, explanation, source = chosen

            is_destruct, destruct_reason = SafetyGuard.inspect(fixed_cmd)

            if dry_run:
                sys.stderr.write(f"  [DRY-RUN] Would execute: {fixed_cmd}\n")
                if is_destruct:
                    sys.stderr.write(f"  [WARNING] Flagged DESTRUCTIVE ({destruct_reason})\n")
                return 1

            if is_destruct:
                # Destructive: always require explicit "yes" even after arrow-key selection
                sys.stderr.write("\n")
                sys.stderr.write("  \033[1;31m[CAUTION: POTENTIALLY DESTRUCTIVE COMMAND]\033[0m\n")
                sys.stderr.write(f"  {destruct_reason}\n")
                sys.stderr.write("  To approve, type the full word \033[1m'yes'\033[0m: ")
                sys.stderr.flush()
                try:
                    ans = input().strip()
                except (EOFError, KeyboardInterrupt):
                    sys.stderr.write("\n")
                    return 2
                if ans.lower() != "yes":
                    return 2
            # Safe command: Enter-to-select already confirmed intent. Execute directly.
            sys.stdout.write(fixed_cmd + "\n")
            sys.stdout.flush()
            return 0

        if approved:
            # ONLY the approved command line is printed to STDOUT
            sys.stdout.write(fixed_cmd + "\n")
            sys.stdout.flush()
            return 0
        else:
            is_destruct, _ = SafetyGuard.inspect(fixed_cmd)
            return 2 if is_destruct else 1
