"""
xsf.ai.providers.gemini - Google Gemini Free Tier Provider (zero external dependencies).

Supports both:
  - Google AI Studio API keys ('AIza...')
  - Google Cloud / AI Studio ('AQ....') keys via generativelanguage.googleapis.com
"""
import json
from typing import Tuple
import urllib.error
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT

# Current stable free-tier models, ordered fastest→fallback
# gemini-flash-lite-latest has zero thinking-token overhead (~1.5-2.5s latency)
_FALLBACK_MODELS = [
    "gemini-flash-lite-latest",  # Ultra-fast low-latency tier (no thinking delay)
    "gemini-flash-latest",       # Canonical latest flash alias
    "gemini-2.5-flash",          # Generation 2.5 flash fallback
]


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-flash-lite-latest"):
        self.api_key = api_key
        # Prefer gemini-flash-lite-latest first for interactive CLI responsiveness
        if not model or model == "gemini-flash-latest":
            self.model = "gemini-flash-lite-latest"
        else:
            self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        if not self.is_configured():
            raise ProviderError(
                "Gemini API key not configured. Set GEMINI_API_KEY or run `xsf config`"
            )

        key = self.api_key.strip()
        user_content = f"Shell: {cmd.shell}\nFailed command: {cmd.raw}\n"
        if cmd.stderr_text:
            user_content += f"Error output:\n{cmd.stderr_text[:1500]}\n"

        body = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json",
            },
        }

        models_to_try = [self.model] + [m for m in _FALLBACK_MODELS if m != self.model]

        last_error: Exception = ProviderError("No Gemini models available", 503)
        for model in models_to_try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=8) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                self.model = model

                try:
                    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    finish_reason = (
                        data.get("candidates", [{}])[0]
                        .get("finishReason", "UNKNOWN")
                    )
                    last_error = ProviderError(
                        f"Gemini response empty on '{model}' (finishReason={finish_reason})",
                        502,
                    )
                    continue

                fixed_cmd, explanation, confidence, destructive = self.parse_json_response(raw_text)
                return self.finalize_prediction(fixed_cmd, explanation, confidence, destructive)

            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", errors="ignore")[:300]
                is_key_err = (
                    e.code in (401, 403)
                    or "API_KEY_INVALID" in detail
                    or "API key not valid" in detail
                    or "UNAUTHENTICATED" in detail
                )
                if is_key_err:
                    raise ProviderError(
                        f"Gemini API key rejected ({e.code}). Verify your key at https://aistudio.google.com/app/apikey",
                        401,
                    )
                if e.code in (404, 503, 429, 500, 502, 504):
                    last_error = ProviderError(
                        f"Gemini model '{model}' unavailable ({e.code}), trying fallback",
                        e.code,
                    )
                    continue
                raise ProviderError(f"Gemini API error ({e.code}): {detail}", e.code)
            except urllib.error.URLError as e:
                reason_str = str(getattr(e, "reason", e))
                if "timed out" in reason_str.lower():
                    last_error = ProviderError(f"Gemini model '{model}' timed out (8s)", 504)
                    continue
                raise ProviderError(f"Network error connecting to Gemini: {reason_str}", 503)
            except ProviderError:
                raise
            except Exception as e:
                err_str = str(e)
                if "timed out" in err_str.lower():
                    last_error = ProviderError(f"Gemini model '{model}' timed out (8s)", 504)
                    continue
                raise ProviderError(f"Gemini request failed: {err_str}", 503)

        raise last_error
