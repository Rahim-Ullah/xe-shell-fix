"""
xsf.ai.providers.gemini - Google Gemini Free Tier Provider (zero external dependencies).

Free tier rates (gemini-2.0-flash-lite):
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
    "gemini-2.0-flash-lite",  # Fastest, most generous free quota
    "gemini-2.0-flash",        # Slightly more capable
    "gemini-1.5-flash",        # Proven stable fallback
]


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-2.0-flash-lite"):
        self.api_key = api_key
        self.model = model

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
                "maxOutputTokens": 512,       # Enough for JSON + explanation
                "responseMimeType": "application/json",
            },
        }

        # Try primary model, then automatic fallbacks on 404
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
                    # Check for safety block or empty response
                    finish_reason = (
                        data.get("candidates", [{}])[0]
                        .get("finishReason", "UNKNOWN")
                    )
                    raise ProviderError(
                        f"Gemini response empty (finishReason={finish_reason})"
                    )

                fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
                if destructive:
                    confidence = min(confidence, 0.4)
                return fixed_cmd, explanation, confidence

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:300]
                if e.code == 404:
                    last_error = ProviderError(f"Gemini model '{model}' not found, trying fallback", e.code)
                    continue  # Try next model
                elif e.code == 429:
                    raise ProviderError(f"Gemini rate limit hit (429). Try again shortly.", e.code)
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
