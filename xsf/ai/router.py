"""
xsf.ai.router - Intelligent multi-provider AI fallback router and cache coordinator.
"""
import sys
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


class AIRouter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ai_cfg = config.get("ai", {})
        self.local_cfg = config.get("local_llm", {})
        self.providers: Dict[str, BaseProvider] = {}
        self._init_providers()

    def _init_providers(self) -> None:
        # Groq (Ultra-fast LPU inference)
        self.providers["groq"] = GroqProvider(
            api_key=self.ai_cfg.get("groq_api_key", ""),
            model=self.ai_cfg.get("groq_model", "qwen/qwen3.8-27b"),
        )
        # Cerebras (Wafer-scale engine)
        self.providers["cerebras"] = CerebrasProvider(
            api_key=self.ai_cfg.get("cerebras_api_key", ""),
            model=self.ai_cfg.get("cerebras_model", "qwen-3.8-27b"),
        )
        # Gemini (Free)
        self.providers["gemini"] = GeminiProvider(
            api_key=self.ai_cfg.get("gemini_api_key", ""),
            model=self.ai_cfg.get("gemini_model", "gemini-3.6-flash"),
        )
        # OpenRouter (Free-tier models)
        self.providers["openrouter"] = OpenRouterProvider(
            api_key=self.ai_cfg.get("openrouter_api_key", ""),
            model=self.ai_cfg.get("openrouter_model", "meta-llama/llama-3.3-70b-instruct:free"),
        )
        # Grok (xAI, opt-in)
        self.providers["grok"] = GrokProvider(
            api_key=self.ai_cfg.get("grok_api_key", ""),
            model=self.ai_cfg.get("grok_model", "grok-beta"),
        )
        # OpenAI (opt-in)
        self.providers["openai"] = OpenAICompatProvider(
            api_key=self.ai_cfg.get("openai_api_key", ""),
            model=self.ai_cfg.get("openai_model", "gpt-4o-mini"),
            base_url=self.ai_cfg.get("openai_base_url", ""),
        )
        # Ollama (Local LLM, opt-in)
        self.providers["ollama"] = OllamaProvider(
            host=self.local_cfg.get("host", "http://localhost:11434"),
            model=self.local_cfg.get("model", "qwen2.5-coder:1.5b"),
            enabled=self.local_cfg.get("enabled", False),
        )

    def route(self, cmd: Command, skip_cache: bool = False) -> Optional[Tuple[str, float, str]]:
        if not self.ai_cfg.get("enabled", True):
            return None

        # 1. Check local query cache first
        cache_key = make_key(cmd.raw, cmd.stderr_text, cmd.shell)
        if not skip_cache:
            cached = AICache.get(cache_key)
            if cached and cached.get("command"):
                return (
                    cached["command"],
                    float(cached.get("confidence", 0.7)),
                    f"(cached) {cached.get('explanation', '')}".strip(),
                )

        # 2. Check Tier 2 Local LLM if explicitly enabled
        ollama = self.providers.get("ollama")
        if ollama and ollama.is_configured() and isinstance(ollama, OllamaProvider) and ollama.is_alive():
            try:
                fixed, exp, conf = ollama.fix(cmd)
                if fixed:
                    AICache.put(cache_key, fixed, exp, conf)
                    return fixed, conf, f"[Local LLM] {exp}"
            except Exception as e:
                sys.stderr.write(f"  (Ollama fallback bypassed: {e})\n")

        # 3. Cascade through configured Cloud AI providers
        cascade: List[str] = self.ai_cfg.get("cascade", ["gemini", "openrouter"])
        # Add any configured opt-in providers if not in cascade
        if self.providers["grok"].is_configured() and "grok" not in cascade:
            cascade.append("grok")
        if self.providers["openai"].is_configured() and "openai" not in cascade:
            cascade.append("openai")

        for provider_name in cascade:
            provider = self.providers.get(provider_name)
            if not provider or not provider.is_configured():
                continue

            try:
                fixed, exp, conf = provider.fix(cmd)
                if fixed:
                    AICache.put(cache_key, fixed, exp, conf)
                    return fixed, conf, f"[{provider_name.capitalize()}] {exp}"
            except ProviderError as e:
                sys.stderr.write(f"  ({provider_name} unavailable: {e})\n")
                continue
            except Exception as e:
                sys.stderr.write(f"  ({provider_name} error: {e})\n")
                continue

        return None
