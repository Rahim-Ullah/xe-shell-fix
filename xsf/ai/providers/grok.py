"""
xsf.ai.providers.grok - xAI Grok Provider (opt-in, requires user key).
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT


class GrokProvider(BaseProvider):
    name = "grok"

    def __init__(self, api_key: str = "", model: str = "grok-beta"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError("Grok API key is not configured. Set GROK_API_KEY or run `xsf config`")

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
        }

        url = "https://api.x.ai/v1/chat/completions"
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
            raise ProviderError(f"xAI Grok error ({e.code}): {detail}")
        except urllib.error.URLError as e:
            raise ProviderError(f"Network error connecting to xAI: {e.reason}")
        except Exception as e:
            raise ProviderError(f"Grok request failed: {e}")

        try:
            raw_text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ProviderError("Grok response missing choices content")

        fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
        if destructive:
            confidence = min(confidence, 0.4)

        return fixed_cmd, explanation, confidence
