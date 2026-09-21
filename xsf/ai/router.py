"""
xsf.ai.router - Intelligent multi-provider AI fallback router with retry and cache.

Cascade order (when all keys configured):
  Cache → Ollama (opt-in) → Groq → Cerebras → Gemini → OpenRouter → Grok* → OpenAI*
  (* = opt-in only)
"""
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from xsf.core.command import Command
from xsf.ai.cache import AICache, make_key
from xsf.ai.providers import (
    BaseProvider,
    GroqProvider,
    CerebrasProvider,
    GeminiProvider,
    OpenRouterProvider,
    GrokProvider,
    OpenAICompatProvider,
    OllamaProvider,
    ProviderError,
)

# HTTP status codes where retrying the SAME provider makes sense
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
# Status codes where we should skip to the NEXT provider immediately
_SKIP_CODES = {401, 403, 404, 400}


class AIRouter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_cfg = config.get("ai", {})
        self.local_cfg = config.get("local_llm", {})
        self.providers: Dict[str, BaseProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        # Groq (Ultra-fast LPU — FIRST in cascade, highest priority)
        self.providers["groq"] = GroqProvider(
            api_key=self.ai_cfg.get("groq_api_key", ""),
            model=self.ai_cfg.get("groq_model", "qwen/qwen3.8-27b"),
        )
        # Cerebras (Wafer-scale, very fast)
        self.providers["cerebras"] = CerebrasProvider(
            api_key=self.ai_cfg.get("cerebras_api_key", ""),
            model=self.ai_cfg.get("cerebras_model", "qwen-3.8-27b"),
        )
        # Gemini (Free, generous quota)
        self.providers["gemini"] = GeminiProvider(
            api_key=self.ai_cfg.get("gemini_api_key", ""),
            model=self.ai_cfg.get("gemini_model", "gemini-flash-latest"),
        )
        # OpenRouter (Free-tier fallback)
        self.providers["openrouter"] = OpenRouterProvider(
            api_key=self.ai_cfg.get("openrouter_api_key", ""),
            model=self.ai_cfg.get("openrouter_model", "meta-llama/llama-3.3-70b-instruct:free"),
        )
        # Grok (xAI, opt-in)
        self.providers["grok"] = GrokProvider(
            api_key=self.ai_cfg.get("grok_api_key", ""),
            model=self.ai_cfg.get("grok_model", "grok-2-latest"),
        )
        # OpenAI-compat (opt-in, supports custom base_url for DeepSeek, Mistral, etc.)
        self.providers["openai"] = OpenAICompatProvider(
            api_key=self.ai_cfg.get("openai_api_key", ""),
            model=self.ai_cfg.get("openai_model", "gpt-4o-mini"),
            base_url=self.ai_cfg.get("openai_base_url", ""),
        )
        # Ollama (Local private LLM, opt-in)
        self.providers["ollama"] = OllamaProvider(
            host=self.local_cfg.get("host", "http://localhost:11434"),
            model=self.local_cfg.get("model", "qwen2.5-coder:1.5b"),
            enabled=self.local_cfg.get("enabled", False),
        )

    def _build_cascade(self) -> List[str]:
        """
        Build the ordered provider cascade.
        - Config-specified cascade is used as the base order.
        - Groq is always inserted at position 0 if configured (fastest provider).
        - Opt-in providers (grok, openai) are appended if configured but not listed.
        """
        base: List[str] = list(self.ai_cfg.get("cascade", ["groq", "cerebras", "gemini", "openrouter"]))

        # Guarantee Groq is first if configured — it's the fastest and most reliable
        if self.providers["groq"].is_configured() and "groq" in base:
            base = ["groq"] + [x for x in base if x != "groq"]

        # Append opt-in providers if configured and not already in cascade
        for opt_in in ("grok", "openai"):
            if self.providers[opt_in].is_configured() and opt_in not in base:
                base.append(opt_in)

        return base

    def route(self, cmd: Command, skip_cache: bool = False) -> Optional[Tuple[str, float, str]]:
        """
        Routes command repair through the full provider cascade.
        Returns (fixed_command, confidence, explanation) or None if all providers fail.
        """
        if not self.ai_cfg.get("enabled", True):
            return None

        # 1. Check 7-day local query cache (fastest path — zero network)
        cache_key = make_key(cmd.raw, cmd.stderr_text, cmd.shell)
        if not skip_cache:
            cached = AICache.get(cache_key)
            if cached and cached.get("command"):
                return (
                    cached["command"],
                    float(cached.get("confidence", 0.7)),
                    f"(cached) {cached.get('explanation', '')}".strip(),
                )

        # 2. Tier 2: Local Ollama if enabled and alive (zero network cost)
        ollama = self.providers.get("ollama")
        if (
            ollama
            and isinstance(ollama, OllamaProvider)
            and ollama.is_configured()
            and ollama.is_alive()
        ):
            try:
                fixed, exp, conf = ollama.fix(cmd)
                if fixed:
                    AICache.put(cache_key, fixed, exp, conf)
                    return fixed, conf, f"[Local LLM] {exp}"
            except Exception as e:
                sys.stderr.write(f"  (ollama skipped: {e})\n")

        # 3. Tier 3: Cascade through cloud providers
        cascade = self._build_cascade()

        for provider_name in cascade:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_configured():
                continue

            result = self._try_provider(provider, provider_name, cmd)
            if result is not None:
                fixed, conf, label = result
                AICache.put(cache_key, fixed, label, conf)
                return fixed, conf, label

        return None

    def _try_provider(
        self,
        provider: BaseProvider,
        name: str,
        cmd: Command,
        max_retries: int = 1,
    ) -> Optional[Tuple[str, float, str]]:
        """
        Calls a single provider with up to max_retries retries on transient errors.
        Returns (fixed, confidence, label) or None to skip to next provider.
        """
        for attempt in range(max_retries + 1):
            try:
                fixed, exp, conf = provider.fix(cmd)
                if fixed:
                    return fixed, conf, f"[{name.capitalize()}] {exp}"
                # Provider returned empty fixed_command — it couldn't help
                return None

            except ProviderError as e:
                code = e.status_code
                if code in _SKIP_CODES:
                    # Auth/not-found errors — skip this provider immediately
                    sys.stderr.write(f"  ({name} skipped: {e})\n")
                    return None
                elif code in _RETRYABLE_CODES and attempt < max_retries:
                    # Transient error — wait and retry once
                    wait = 1.5 * (attempt + 1)
                    sys.stderr.write(f"  ({name} retrying in {wait:.1f}s: {e})\n")
                    time.sleep(wait)
                    continue
                else:
                    # All retries exhausted or unknown error — cascade to next
                    sys.stderr.write(f"  ({name} unavailable: {e})\n")
                    return None
            except Exception as e:
                sys.stderr.write(f"  ({name} error: {e})\n")
                return None

        return None
