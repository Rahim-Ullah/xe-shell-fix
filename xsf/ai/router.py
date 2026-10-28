"""
xsf.ai.router - Intelligent multi-provider AI fallback router with retry, circuit-breaker,
multi-key rotation, and persistent 7-day query cache.

Cascade order (when all keys configured):
  Cache → Ollama (opt-in) → Groq → Gemini → Cerebras → OpenRouter → Grok* → OpenAI*
  (* = opt-in only)
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from xsf.config import CONFIG_DIR, parse_key_list, secure_config_permissions
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

# HTTP status codes where retrying the SAME provider/key makes sense
_RETRYABLE_CODES = {429, 500, 502, 503, 504}
# Status codes where we should skip to the NEXT key or provider immediately (auth, billing, not-found)
_SKIP_CODES = {400, 401, 402, 403, 404}

HEALTH_FILE = CONFIG_DIR / "provider_health.json"

_REDACTION_PATTERNS = [
    (re.compile(r"(?i)\b(bearer\s+)[A-Za-z0-9_\-\.]{16,}\b"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
    (re.compile(r"(?i)(aws_secret_access_key\s*=\s*)[^\s]{20,}"), r"\1[REDACTED_SECRET]"),
    (re.compile(r"\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"), "[REDACTED_GH_TOKEN]"),
    (re.compile(r"\b(glpat-|xox[baprs]-)[A-Za-z0-9_\-]{20,}\b"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(--?(?:api[-_]?key|token|secret|password|passwd|auth)\s*[=:]?\s*)(\S+)"), r"\1[REDACTED]"),
    (re.compile(r"(://[^:\s]+:)[^@\s]+(@)"), r"\1[REDACTED]\2"),
]


def redact_sensitive_data(text: str) -> str:
    """Masks secrets, tokens, passwords, and API keys to prevent cloud leakage."""
    if not text:
        return ""
    result = text
    for pattern, repl in _REDACTION_PATTERNS:
        result = pattern.sub(repl, result)
    return result


class ProviderHealthTracker:
    """
    Tracks per-provider and per-key rate limits, auth failures, and cooldown windows
    so rate-limited or exhausted keys are cleanly bypassed without lagging the terminal.
    """
    _state: Dict[str, Dict[str, Any]] = {}
    _loaded: bool = False

    @classmethod
    def _key_id(cls, provider: str, api_key: str) -> str:
        key_hash = hashlib.sha256((api_key or "").encode("utf-8")).hexdigest()[:10]
        return f"{provider}:{key_hash}"

    @classmethod
    def load(cls) -> None:
        if cls._loaded:
            return
        if HEALTH_FILE.exists():
            try:
                cls._state = json.loads(HEALTH_FILE.read_text(encoding="utf-8"))
            except Exception:
                cls._state = {}
        cls._loaded = True

    @classmethod
    def save(cls) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            HEALTH_FILE.write_text(json.dumps(cls._state, indent=2), encoding="utf-8")
            secure_config_permissions(HEALTH_FILE)
        except Exception:
            pass

    @classmethod
    def is_cooling_down(cls, provider: str, api_key: str) -> Tuple[bool, str]:
        cls.load()
        entry = cls._state.get(cls._key_id(provider, api_key))
        if not entry:
            return False, "Ready"
        until = float(entry.get("cooldown_until", 0))
        now = time.time()
        if until > now:
            remaining = int(until - now)
            reason = entry.get("status", "cooldown")
            return True, f"{reason} ({remaining}s remaining)"
        return False, entry.get("status", "Ready")

    @classmethod
    def record_success(cls, provider: str, api_key: str) -> None:
        cls.load()
        kid = cls._key_id(provider, api_key)
        cls._state[kid] = {
            "status": "healthy",
            "cooldown_until": 0,
            "last_ok": int(time.time()),
        }
        cls.save()

    @classmethod
    def record_failure(cls, provider: str, api_key: str, status_code: int, message: str = "") -> None:
        cls.load()
        kid = cls._key_id(provider, api_key)
        now = time.time()
        if status_code == 429:
            # Rate limit: 45-second circuit-breaker cooldown
            cooldown = now + 45
            status = "rate_limited"
        elif status_code == 402:
            # Payment / quota exhausted: 30-minute cooldown
            cooldown = now + 1800
            status = "quota_exhausted"
        elif status_code in (401, 403):
            # Invalid key: 15-minute cooldown (cleared immediately when user updates key)
            cooldown = now + 900
            status = "invalid_key"
        elif status_code in (500, 502, 503, 504):
            cooldown = now + 20
            status = "server_busy"
        else:
            cooldown = 0
            status = "error"

        cls._state[kid] = {
            "status": status,
            "cooldown_until": cooldown,
            "last_error": (message or "")[:120],
            "updated_at": int(now),
        }
        cls.save()

    @classmethod
    def reset(cls, provider: Optional[str] = None) -> None:
        cls.load()
        if provider is None:
            cls._state = {}
        else:
            prefix = f"{provider.lower()}:"
            cls._state = {k: v for k, v in cls._state.items() if not k.startswith(prefix)}
        cls.save()

    @classmethod
    def describe_provider_health(cls, provider: str, raw_key_config: str) -> str:
        keys = parse_key_list(raw_key_config)
        if not keys:
            return "\033[90mNot Configured\033[0m"
        active_count = 0
        cooling_notes = []
        for idx, k in enumerate(keys, 1):
            cooling, detail = cls.is_cooling_down(provider, k)
            if not cooling:
                active_count += 1
            else:
                cooling_notes.append(f"key#{idx}: {detail}")
        if active_count == len(keys):
            suffix = f" ({len(keys)} keys ready)" if len(keys) > 1 else " (Ready)"
            return f"\033[32mHealthy{suffix}\033[0m"
        elif active_count > 0:
            return f"\033[33m{active_count}/{len(keys)} Ready ({', '.join(cooling_notes)})\033[0m"
        else:
            return f"\033[31mCooling Down ({', '.join(cooling_notes)})\033[0m"


class AIRouter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_cfg = config.get("ai", {})
        self.local_cfg = config.get("local_llm", {})
        self.gen_cfg = config.get("general", {})
        self.quiet_failover = bool(self.gen_cfg.get("quiet_failover", True)) and not bool(os.environ.get("XSF_DEBUG"))
        self.providers: Dict[str, BaseProvider] = {}
        self._init_providers()

    def _log_failover(self, msg: str) -> None:
        if not self.quiet_failover:
            sys.stderr.write(msg)

    def _init_providers(self) -> None:
        # Groq (Ultra-fast LPU — FIRST in cascade, highest priority)
        self.providers["groq"] = GroqProvider(
            api_key=self.ai_cfg.get("groq_api_key", ""),
            model=self.ai_cfg.get("groq_model", "qwen/qwen3.8-27b"),
        )
        # Gemini (Free, generous 1500 RPD quota — high priority)
        self.providers["gemini"] = GeminiProvider(
            api_key=self.ai_cfg.get("gemini_api_key", ""),
            model=self.ai_cfg.get("gemini_model", "gemini-flash-latest"),
        )
        # Cerebras (Wafer-scale, fallback)
        self.providers["cerebras"] = CerebrasProvider(
            api_key=self.ai_cfg.get("cerebras_api_key", ""),
            model=self.ai_cfg.get("cerebras_model", "llama3.1-8b"),
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
        - Gemini (1500 RPD free tier) is prioritized ahead of Cerebras.
        - Opt-in providers (grok, openai) are appended if configured but not listed.
        """
        base: List[str] = list(self.ai_cfg.get("cascade", ["groq", "gemini", "cerebras", "openrouter"]))

        # Guarantee Groq is first if configured — it's the fastest and most reliable
        if self.providers["groq"].is_configured() and "groq" in base:
            base = ["groq"] + [x for x in base if x != "groq"]

        # Prioritize Gemini (1500 RPD free tier) ahead of Cerebras (unpaid tier returns 402)
        if "gemini" in base and "cerebras" in base:
            g_idx = base.index("gemini")
            c_idx = base.index("cerebras")
            if c_idx < g_idx:
                base.remove("gemini")
                base.insert(c_idx, "gemini")

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
        if self.gen_cfg.get("power_mode", "hybrid") in ("offline", "off"):
            return None

        # Security: Scrub sensitive credentials before network calls or caching
        safe_raw = redact_sensitive_data(cmd.raw)
        safe_stderr = redact_sensitive_data(cmd.stderr_text)
        safe_cmd = Command(raw=safe_raw, shell=cmd.shell, stderr_text=safe_stderr)

        # 1. Check 7-day local query cache (fastest path — zero network)
        cache_key = make_key(safe_cmd.raw, safe_cmd.stderr_text, safe_cmd.shell)
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
                fixed, exp, conf = ollama.fix(safe_cmd)
                if fixed:
                    AICache.put(cache_key, fixed, exp, conf)
                    return fixed, conf, f"[Local LLM] {exp}"
            except Exception as e:
                self._log_failover(f"  (ollama skipped: {e})\n")

        # 3. Tier 3: Cascade through cloud providers (with multi-key rotation & circuit breaker)
        cascade = self._build_cascade()

        for provider_name in cascade:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_configured():
                continue

            result = self._try_provider(provider, provider_name, safe_cmd)
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
        Calls a provider, rotating through backup keys if configured and respecting
        circuit-breaker cooldowns on 429/402/401 errors.
        """
        raw_api_key = getattr(provider, "api_key", "")
        key_list = parse_key_list(raw_api_key) if isinstance(raw_api_key, str) and raw_api_key else ["_default_"]

        for key_candidate in key_list:
            is_real_key = key_candidate != "_default_"
            if is_real_key:
                cooling, reason = ProviderHealthTracker.is_cooling_down(name, key_candidate)
                if cooling:
                    self._log_failover(f"  ({name} key cooling down [{reason}], skipping)\n")
                    continue
                provider.api_key = key_candidate

            for attempt in range(max_retries + 1):
                try:
                    fixed, exp, conf = provider.fix(cmd)
                    if is_real_key:
                        ProviderHealthTracker.record_success(name, key_candidate)
                    if fixed:
                        return fixed, conf, f"[{name.capitalize()}] {exp}"
                    return None

                except ProviderError as e:
                    code = e.status_code
                    if is_real_key and code:
                        ProviderHealthTracker.record_failure(name, key_candidate, code, str(e))

                    if code in _SKIP_CODES:
                        self._log_failover(f"  ({name} skipped [{code}]: {e})\n")
                        break  # Break inner retry loop; try next backup key or next provider
                    elif code in _RETRYABLE_CODES and attempt < max_retries and len(key_list) == 1:
                        wait = 0.8 * (attempt + 1)
                        self._log_failover(f"  ({name} retrying in {wait:.1f}s: {e})\n")
                        time.sleep(wait)
                        continue
                    else:
                        self._log_failover(f"  ({name} unavailable: {e})\n")
                        break
                except Exception as e:
                    self._log_failover(f"  ({name} error: {e})\n")
                    break

        # Restore original multi-key string on provider instance
        if isinstance(raw_api_key, str) and raw_api_key:
            provider.api_key = raw_api_key
        return None
