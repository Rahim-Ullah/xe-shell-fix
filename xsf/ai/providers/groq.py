"""
xsf.ai.providers.groq - Ultra-fast Groq LPU Inference Provider.

Groq offers industry-leading token generation speed (~200ms latency).
Free tier: 30 RPM, 14,400 RPD on most models.
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT

# Ordered list of Groq models to try: fastest/cheapest first
_GROQ_MODELS = [
    "llama-3.1-8b-instant",      # Fastest, very generous free limits
    "llama3-8b-8192",             # Reliable fallback
    "qwen/qwen3.8-27b",           # Good reasoning for complex errors
    "llama-3.3-70b-versatile",    # Most capable, slower
]


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self, api_key: str = "", model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError(
                "Groq API key not configured. Set GROQ_API_KEY or run `xsf config`"
            )

        user_content = f"Shell: {cmd.shell}\nFailed command: {cmd.raw}\n"
        if cmd.stderr_text:
            user_content += f"Error output:\n{cmd.stderr_text[:1500]}\n"

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.0,
            "max_tokens": 512,          # Raised from 200 — was causing truncated JSON
            "response_format": {"type": "json_object"},
            "stop": None,               # Let the model finish naturally
        }

        # Try primary model, fall back on model-not-found or rate limit
        models_to_try = [self.model] + [m for m in _GROQ_MODELS if m != self.model]

        last_error: Exception = ProviderError("No Groq models available")
        for model in models_to_try:
            body["model"] = model
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key.strip()}",
                    "User-Agent": "xsf/1.0 (xe-shell-fix; https://github.com/rahim-ullah/xe-shell-fix)",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                self.model = model  # Remember working model

                try:
                    raw_text = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError):
                    raise ProviderError("Groq response missing choices content")

                # Warn if finish_reason indicates truncation
                finish_reason = data["choices"][0].get("finish_reason", "stop")
                if finish_reason == "length":
                    # JSON was likely truncated — attempt parse anyway (brace matching)
                    pass

                fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
                if destructive:
                    confidence = min(confidence, 0.4)
                return fixed_cmd, explanation, confidence

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:300]
                if e.code == 429:
                    # Rate limited — try next model (different quotas)
                    last_error = ProviderError(f"Groq rate limit on '{model}', trying next", e.code)
                    continue
                elif e.code == 404 or (e.code == 400 and "model" in detail.lower()):
                    last_error = ProviderError(f"Groq model '{model}' unavailable, trying next", e.code)
                    continue
                elif e.code in (401, 403):
                    raise ProviderError(f"Groq API key invalid or unauthorized ({e.code})", e.code)
                else:
                    raise ProviderError(f"Groq API error ({e.code}): {detail}", e.code)
            except urllib.error.URLError as e:
                raise ProviderError(f"Network error connecting to Groq: {e.reason}")
            except ProviderError:
                raise
            except Exception as e:
                raise ProviderError(f"Groq request failed: {e}")

        raise last_error
