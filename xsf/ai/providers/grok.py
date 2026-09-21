"""
xsf.ai.providers.grok - xAI Grok Provider (opt-in, requires user key).
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT

_GROK_MODELS = [
    "grok-2-latest",
    "grok-2-1212",
    "grok-beta",
]


class GrokProvider(BaseProvider):
    name = "grok"

    def __init__(self, api_key: str = "", model: str = "grok-2-latest"):
        self.api_key = api_key
        self.model = model or "grok-2-latest"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError("Grok API key is not configured. Set GROK_API_KEY or run `xsf config`")

        user_content = f"Shell: {cmd.shell}\nFailed command: {cmd.raw}\n"
        if cmd.stderr_text:
            user_content += f"Error output:\n{cmd.stderr_text[:1500]}\n"

        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.0,
            "max_tokens": 512,
            "response_format": {"type": "json_object"},
        }

        models_to_try = [self.model] + [m for m in _GROK_MODELS if m != self.model]
        last_error: Exception = ProviderError("No Grok models available")

        for model in models_to_try:
            body["model"] = model
            req = urllib.request.Request(
                "https://api.x.ai/v1/chat/completions",
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key.strip()}",
                    "User-Agent": "xsf/1.0 (xe-shell-fix)",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                self.model = model

                try:
                    raw_text = data["choices"][0]["message"]["content"]
                except (KeyError, IndexError):
                    raise ProviderError("Grok response missing choices content")

                fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
                if destructive:
                    confidence = min(confidence, 0.4)
                return fixed_cmd, explanation, confidence

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:250]
                if e.code in (404, 429, 500, 502, 503, 504):
                    last_error = ProviderError(f"xAI Grok error ({e.code}) on '{model}', trying fallback", e.code)
                    continue
                elif e.code in (401, 403):
                    raise ProviderError(f"xAI Grok API key invalid or unauthorized ({e.code})", e.code)
                else:
                    raise ProviderError(f"xAI Grok error ({e.code}): {detail}", e.code)
            except urllib.error.URLError as e:
                raise ProviderError(f"Network error connecting to xAI: {e.reason}")
            except ProviderError:
                raise
            except Exception as e:
                raise ProviderError(f"Grok request failed: {e}")

        raise last_error
