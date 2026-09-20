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
from typing import Any, Dict, Optional, Tuple

from xsf.core.command import Command
from xsf.core.safety import SafetyGuard
from xsf.offline import run_offline_engine
from xsf.ai.router import AIRouter


class Engine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_router = AIRouter(config)
        self.allow_help = config.get("general", {}).get("help_introspection", True)
        self.auto_approve_safe = config.get("general", {}).get("auto_approve_safe", False)

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
            if ai_result:
                fixed, conf, exp = ai_result
                return fixed, conf, exp, "ai"
            return None

        # 2. Tier 1: Offline Engine (Rules -> Vocabulary -> Help Introspector)
        offline_result = run_offline_engine(cmd, allow_help_introspection=self.allow_help)
        if offline_result:
            fixed, conf, exp = offline_result
            # If high confidence offline match, return immediately without network call
            if conf >= 0.85 or offline_only:
                return fixed, conf, exp, "offline"

        if offline_only:
            return None

        # 3. Tier 2 / 3: AI Engine Fallback
        ai_result = self.ai_router.route(cmd, skip_cache=skip_cache)
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
        Returns exit code:
          0 = fix approved and written to stdout
          1 = no fix found or declined
          2 = destructive fix declined
        """
        result = self.find_fix(
            cmd,
            offline_only=offline_only,
            ai_only=ai_only,
            skip_cache=skip_cache,
        )

        if not result:
            sys.stderr.write("xsf: no fix found for previous command\n")
            return 1

        fixed_cmd, confidence, explanation, source = result

        # Display suggestion to user on STDERR (keeping stdout clean for eval)
        sys.stderr.write("\n")
        badge = "\033[1;32m[OFFLINE]\033[0m" if source == "offline" else "\033[1;36m[AI]\033[0m"
        sys.stderr.write(f"  {badge} \033[1m{fixed_cmd}\033[0m\n")
        if explanation:
            sys.stderr.write(f"  \033[90m\u2514\u2500 {explanation} (confidence: {int(confidence * 100)}%)\033[0m\n")

        # UNIVERSAL SAFETY GATE: Enforce confirmation on every suggestion
        auto_flag = auto_approve or (self.auto_approve_safe and confidence >= 0.95)
        approved = SafetyGuard.confirm(fixed_cmd, auto_approve=auto_flag, dry_run=dry_run)

        if approved:
            # ONLY the approved command line is printed to STDOUT
            sys.stdout.write(fixed_cmd + "\n")
            sys.stdout.flush()
            return 0
        else:
            is_destruct, _ = SafetyGuard.inspect(fixed_cmd)
            return 2 if is_destruct else 1
