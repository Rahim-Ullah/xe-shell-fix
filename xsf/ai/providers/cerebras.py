"""
xsf.ai.providers.cerebras - Wafer-Scale Cerebras Inference Provider.
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT


class CerebrasProvider(BaseProvider):
    name = "cerebras"

    def __init__(self, api_key: str = "", model: str = "qwen-3.8-27b"):
        self.api_key = api_key
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError("Cerebras API key is not configured. Set CEREBRAS_API_KEY or run `xsf config`")

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

        url = "https://api.cerebras.ai/v1/chat/completions"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key.strip()}",
                "User-Agent": "xsf/1.0 (xe-shell-fix)",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")[:250]
            raise ProviderError(f"Cerebras API error ({e.code}): {detail}", e.code)
        except urllib.error.URLError as e:
            raise ProviderError(f"Network error connecting to Cerebras: {e.reason}")
        except Exception as e:
            raise ProviderError(f"Cerebras request failed: {e}")

        try:
            raw_text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ProviderError("Cerebras response missing choices content")

        fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
        if destructive:
            confidence = min(confidence, 0.4)

        return fixed_cmd, explanation, confidence
