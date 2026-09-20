"""
xsf.ai.providers.ollama - Local Offline LLM Provider via Ollama (Tier 2, opt-in).
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT


class OllamaProvider(BaseProvider):
    name = "ollama"

    def __init__(self, host: str = "http://localhost:11434", model: str = "qwen2.5-coder:1.5b", enabled: bool = False):
        self.host = host.rstrip("/")
        self.model = model
        self.enabled = enabled

    def is_configured(self) -> bool:
        return bool(self.enabled and self.host)

    def is_alive(self) -> bool:
        """Fast ping to check if local Ollama daemon is active without waiting."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=0.8) as resp:
                return resp.status == 200
        except Exception:
            return False

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError("Local Ollama LLM is not enabled in config. Run `xsf config` to enable Tier 2")

        if not self.is_alive():
            raise ProviderError(f"Ollama daemon not reachable at {self.host}")

        user_content = f"Shell: {cmd.shell}\nFailed command: {cmd.raw}\n"
        if cmd.stderr_text:
            user_content += f"Error output:\n{cmd.stderr_text[:1500]}\n"

        prompt = f"{SYSTEM_PROMPT}\n\nUser query:\n{user_content}"
        body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.0},
        }

        url = f"{self.host}/api/generate"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            raise ProviderError(f"Ollama local generation failed: {e}")

        raw_text = data.get("response", "")
        fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
        if destructive:
            confidence = min(confidence, 0.4)

        return fixed_cmd, explanation, confidence
