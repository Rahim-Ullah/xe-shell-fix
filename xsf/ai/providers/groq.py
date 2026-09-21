"""
xsf.ai.providers.groq - Ultra-fast Groq LPU Inference Provider.

Groq offers industry-leading token generation speed (~200ms latency).
Free tier: 30 RPM, 14,400 RPD on standard models.
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT

# Ordered list of active Groq models: proven accessible first
_GROQ_MODELS = [
    "qwen/qwen3.8-27b",           # Active, extremely fast, excellent code reasoning
    "llama3-8b-8192",             # High availability fallback
    "llama-3.1-8b-instant",      # Fast fallback
    "llama-3.3-70b-versatile",    # High parameter reasoning fallback
]


class GroqProvider(BaseProvider):
    name = "groq"

    def __init__(self, api_key: str = "", model: str = "qwen/qwen3.8-27b"):
        self.api_key = api_key
        self.model = model or "qwen/qwen3.8-27b"

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
            "max_tokens": 512,          # High enough to guarantee full JSON completion
            "response_format": {"type": "json_object"},
        }

        # Try primary model, fall back on model-not-found, 429, or 503
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

                fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
                if destructive:
                    confidence = min(confidence, 0.4)
                return fixed_cmd, explanation, confidence

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:300]
                if e.code in (429, 500, 502, 503, 504):
                    # Rate limit or server error — try next model
                    last_error = ProviderError(f"Groq error ({e.code}) on '{model}', trying next", e.code)
                    continue
                elif e.code == 404 or (e.code == 400 and ("model" in detail.lower() or "not found" in detail.lower())):
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
