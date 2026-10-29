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
        # Extract the actual target file/dir operand, skipping option flags
        target_tokens = [t for t in cmd.tokens[1:] if not t.startswith("-") and not (prog in ("del", "rmdir") and t.startswith("/"))]
        target = target_tokens[0] if target_tokens else ""
        target_clean = target.strip('\'"')
        if not target_clean:
            return None

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
                p_target = Path(target_clean)
                if not p_target.is_absolute() and cmd.cwd:
                    p_target = Path(cmd.cwd) / p_target
                target_missing_on_disk = not p_target.exists()
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
        gen = config.get("general", {})
        self.allow_help = gen.get("help_introspection", True)
        self.auto_approve_safe = gen.get("auto_approve_safe", False)
        self.power_mode = gen.get("power_mode", "hybrid").lower()

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

        if self.power_mode == "off":
            return []
        if self.power_mode == "offline" and not ai_only:
            offline_only = True
        elif self.power_mode == "ai_only" and not offline_only:
            ai_only = True

        # 1. AI-Only path (if explicitly requested via --ai or power_mode=ai_only)
        if ai_only:
            ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
            if ai_result and ai_result[0] and ai_result[0].strip():
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
        if self.power_mode == "off":
            return None
        if self.power_mode == "offline" and not ai_only:
            offline_only = True
        elif self.power_mode == "ai_only" and not offline_only:
            ai_only = True

        # 1. AI-Only path (if explicitly requested via --ai or power_mode=ai_only)
        if ai_only:
            ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
            if ai_result and ai_result[0] and ai_result[0].strip():
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
        # 0. Check Power Switch state
        if self.power_mode == "off":
            sys.stderr.write("xsf: engine is paused (Power Switch: OFF). Run `xsf power on` to resume.\n")
            return 1

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
            sys.stderr.write("xsf: no automatic fix found for previous command\n")
            if offline_only or self.power_mode == "offline":
                sys.stderr.write("     [Hint] Offline-Only mode active. Run `xsf power hybrid` or pass `--ai` to enable AI diagnosis.\n")
            elif not self.ai_router or not any(p.is_configured() for p in self.ai_router.providers.values()):
                sys.stderr.write("     [Hint] No personal AI key attached. Run `xsf setup` or `xsf key guide` to connect free Groq/Gemini keys.\n")
            else:
                sys.stderr.write("     [Hint] Try `xsf --ai` to query AI providers directly, or `xsf power status` to check key limits.\n")
            return 1

        from xsf.ui.selector import _sanitize_terminal_string

        if len(candidates) == 1:
            chosen = candidates[0]
            fixed_cmd, confidence, explanation, source = chosen
            safe_cmd = _sanitize_terminal_string(fixed_cmd)
            safe_exp = _sanitize_terminal_string(explanation)
            # Display suggestion to user on STDERR (keeping stdout clean for eval)
            sys.stderr.write("\n")
            badge = "\033[1;32m[OFFLINE]\033[0m" if source == "offline" else "\033[1;36m[AI]\033[0m"
            sys.stderr.write(f"  {badge} \033[1m{safe_cmd}\033[0m\n")
            if safe_exp:
                try:
                    sys.stderr.write(f"  \033[90m\u2514\u2500 {safe_exp} (confidence: {int(confidence * 100)}%)\033[0m\n")
                except UnicodeEncodeError:
                    sys.stderr.write(f"  \033[90m\\-- {safe_exp} (confidence: {int(confidence * 100)}%)\033[0m\n")
            # Single candidate: pass through safety gate (Enter/y for safe, full "yes" for destructive)
            auto_flag = auto_approve or (self.auto_approve_safe and confidence >= 0.95)
            approved = SafetyGuard.confirm(fixed_cmd, auto_approve=auto_flag, dry_run=dry_run)
        else:
            # Multi-candidate handling:
            # 1. Dry-run never blocks on interactive selection
            if dry_run:
                top_cmd, top_conf, top_exp, top_src = candidates[0]
                is_destruct, destruct_reason = SafetyGuard.inspect(top_cmd)
                sys.stderr.write(f"  [DRY-RUN] Would execute: {_sanitize_terminal_string(top_cmd)}\n")
                if is_destruct:
                    sys.stderr.write(f"  [WARNING] Flagged DESTRUCTIVE ({destruct_reason})\n")
                return 2 if is_destruct else 1

            # 2. Auto-approve safe high-confidence primary candidate without blocking
            top_cmd, top_conf, top_exp, top_src = candidates[0]
            auto_flag = auto_approve or (self.auto_approve_safe and top_conf >= 0.95)
            top_is_destruct, _ = SafetyGuard.inspect(top_cmd)
            if auto_flag and not top_is_destruct:
                sys.stdout.write(top_cmd + "\n")
                sys.stdout.flush()
                return 0

            # 3. Interactive selection: user navigates with arrow keys and presses Enter to select.
            # The selection itself IS confirmation for safe commands — no redundant double-prompt.
            from xsf.ui.selector import choose_candidate
            chosen = choose_candidate(candidates)
            if not chosen:
                return 1
            fixed_cmd, confidence, explanation, source = chosen

            is_destruct, destruct_reason = SafetyGuard.inspect(fixed_cmd)

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
            if not dry_run:
                sys.stderr.write("  \033[90mExecution cancelled.\033[0m\n")
            return 2 if is_destruct else 1
