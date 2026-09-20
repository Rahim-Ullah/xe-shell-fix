"""
xsf.ai.providers.openai_compat - Generic OpenAI-compatible API provider (OpenAI, DeepSeek, Mistral).
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT


class OpenAICompatProvider(BaseProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini", base_url: str = ""):
        self.api_key = api_key
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError("OpenAI API key is not configured. Set OPENAI_API_KEY or run `xsf config`")

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
            "response_format": {"type": "json_object"},
        }

        url = f"{self.base_url}/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key.strip()}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")[:250]
            raise ProviderError(f"API error ({e.code}): {detail}")
        except urllib.error.URLError as e:
            raise ProviderError(f"Network error connecting to API: {e.reason}")
        except Exception as e:
            raise ProviderError(f"API request failed: {e}")

        try:
            raw_text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ProviderError("API response missing message content")

        fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
        if destructive:
            confidence = min(confidence, 0.4)

        return fixed_cmd, explanation, confidence
