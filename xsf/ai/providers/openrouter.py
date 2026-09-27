"""
xsf.ai.providers.openrouter - OpenRouter Free-Tier Models Provider.
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT


# Ordered list of high-availability free tier models on OpenRouter
_OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemini-2.0-flash-exp:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-coder-32b-instruct:free",
]


class OpenRouterProvider(BaseProvider):
    name = "openrouter"

    def __init__(self, api_key: str = "", model: str = "meta-llama/llama-3.3-70b-instruct:free"):
        self.api_key = api_key
        self.model = model or "meta-llama/llama-3.3-70b-instruct:free"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError("OpenRouter API key is not configured. Set OPENROUTER_API_KEY or run `xsf config`")

        user_content = f"Shell: {cmd.shell}\nFailed command: {cmd.raw}\n"
        if cmd.stderr_text:
            user_content += f"Error output:\n{cmd.stderr_text[:2000]}\n"

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

        url = "https://openrouter.ai/api/v1/chat/completions"

        models_to_try = [self.model] + [m for m in _OPENROUTER_MODELS if m != self.model]
        last_error: Exception = ProviderError("No OpenRouter models available")

        for model in models_to_try:
            body["model"] = model
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key.strip()}",
                    "HTTP-Referer": "https://github.com/xe-shell-fix/xsf",
                    "X-Title": "xe-shell-fix",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=14) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    break
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:250]
                last_error = ProviderError(f"OpenRouter API error ({e.code}): {detail}", e.code)
                if e.code in (400, 404, 429, 503):
                    continue
                raise last_error
            except urllib.error.URLError as e:
                raise ProviderError(f"Network error connecting to OpenRouter: {e.reason}")
            except Exception as e:
                raise ProviderError(f"OpenRouter request failed: {e}")
        else:
            raise last_error

        try:
            raw_text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ProviderError("OpenRouter response missing message content")

        fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
        return self.finalize_prediction(fixed_cmd, explanation, confidence, destructive)
