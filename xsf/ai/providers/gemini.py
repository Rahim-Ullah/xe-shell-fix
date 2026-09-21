"""
xsf.ai.providers.gemini - Google Gemini Free Tier Provider (zero external dependencies).

Free tier rates:
  - 30 RPM, 1500 RPD, 1,000,000 TPM
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT

# Current stable free-tier models, ordered best→fallback
_FALLBACK_MODELS = [
    "gemini-flash-latest",      # Canonical latest flash alias (always active)
    "gemini-3.6-flash",         # Modern generation flash
    "gemini-flash-lite-latest", # Ultra-fast low-latency tier
    "gemini-3.5-flash-lite",    # Stable fallback lite
]


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-flash-latest"):
        self.api_key = api_key
        self.model = model or "gemini-flash-latest"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError(
                "Gemini API key not configured. Set GEMINI_API_KEY or run `xsf config`"
            )

        user_content = f"Shell: {cmd.shell}\nFailed command: {cmd.raw}\n"
        if cmd.stderr_text:
            user_content += f"Error output:\n{cmd.stderr_text[:1500]}\n"

        body = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 512,       # Generous room for full JSON output
                "responseMimeType": "application/json",
            },
        }

        # Try primary model, then automatic fallbacks on 404, 503, 429
        models_to_try = [self.model] + [m for m in _FALLBACK_MODELS if m != self.model]

        last_error: Exception = ProviderError("No Gemini models available")
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key.strip(),
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                # Update working model for future calls in this session
                self.model = model

                try:
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    finish_reason = (
                        data.get("candidates", [{}])[0]
                        .get("finishReason", "UNKNOWN")
                    )
                    last_error = ProviderError(
                        f"Gemini response empty on '{model}' (finishReason={finish_reason})"
                    )
                    continue

                fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
                if destructive:
                    confidence = min(confidence, 0.4)
                return fixed_cmd, explanation, confidence

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:300]
                # 404 = Model retired/not found, 503 = Temporary capacity spike, 429 = Per-model quota limit
                if e.code in (404, 503, 429, 500, 502, 504):
                    last_error = ProviderError(f"Gemini model '{model}' unavailable ({e.code}), trying fallback", e.code)
                    continue  # Try next model in fallback list
                elif e.code in (401, 403):
                    raise ProviderError(f"Gemini API key invalid or unauthorized ({e.code})", e.code)
                else:
                    raise ProviderError(f"Gemini API error ({e.code}): {detail}", e.code)
            except urllib.error.URLError as e:
                raise ProviderError(f"Network error connecting to Gemini: {e.reason}")
            except ProviderError:
                raise
            except Exception as e:
                raise ProviderError(f"Gemini request failed: {e}")

        raise last_error
