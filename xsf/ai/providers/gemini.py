"""
xsf.ai.providers.gemini - Google Gemini Free Tier & Vertex Express Provider (zero external dependencies).

Supports both:
  - Google AI Studio API keys ('AIza...') via generativelanguage.googleapis.com
  - Google Cloud / Vertex AI Express Mode API keys ('AQ....') via aiplatform.googleapis.com
"""
import json
from typing import List, Tuple
import urllib.error
import urllib.parse
import urllib.request

from xsf.core.command import Command
from xsf.ai.providers.base import BaseProvider, ProviderError, SYSTEM_PROMPT

# Current stable free-tier models, ordered best→fallback
_FALLBACK_MODELS = [
    "gemini-flash-latest",       # Canonical latest flash alias (AI Studio)
    "gemini-2.5-flash",          # Active generation 2.5 flash (AI Studio + Vertex Express)
    "gemini-2.0-flash",          # Ultra-stable 2.0 flash (AI Studio + Vertex Express)
    "gemini-flash-lite-latest",  # Low-latency lite alias
]

_VERTEX_EXPRESS_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
]


class GeminiProvider(BaseProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-flash-latest"):
        self.api_key = api_key
        self.model = model or "gemini-flash-latest"

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    def _build_endpoints(self, model: str, key: str) -> List[Tuple[str, dict]]:
        """
        Returns ordered (url, headers) pairs based on key prefix:
          - 'AQ.' keys (Google Cloud / Vertex AI Express Mode) try aiplatform.googleapis.com first,
            then generativelanguage.googleapis.com.
          - 'AIza' keys (Google AI Studio) use generativelanguage.googleapis.com directly.
        """
        safe_key = urllib.parse.quote(key, safe="")
        studio_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        studio_headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        }
        if key.startswith("AQ."):
            v_model = "gemini-2.5-flash" if model == "gemini-flash-latest" else model
            vertex_url = f"https://aiplatform.googleapis.com/v1/publishers/google/models/{v_model}:generateContent?key={safe_key}"
            vertex_headers = {"Content-Type": "application/json"}
            return [(vertex_url, vertex_headers), (studio_url, studio_headers)]
        return [(studio_url, studio_headers)]

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

        base_models = _VERTEX_EXPRESS_MODELS if key.startswith("AQ.") else _FALLBACK_MODELS
        models_to_try = [self.model] + [m for m in base_models if m != self.model]

        last_error: Exception = ProviderError("No Gemini models available", 503)
        for model in models_to_try:
            endpoints = self._build_endpoints(model, key)
            for idx, (url, headers) in enumerate(endpoints):
                req = urllib.request.Request(
                    url,
                    data=json.dumps(body).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=6) as resp:
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
                        # If AQ. key failed on endpoint #1, let it try endpoint #2 before raising 401
                        if idx + 1 < len(endpoints):
                            continue
                        raise ProviderError(
                            f"Gemini API key rejected ({e.code}). Verify your key at https://aistudio.google.com/app/apikey",
                            401,
                        )
                    if e.code in (404, 503, 429, 500, 502, 504):
                        last_error = ProviderError(
                            f"Gemini model '{model}' unavailable ({e.code}), trying fallback",
                            e.code,
                        )
                        break  # Try next model in fallback list
                    raise ProviderError(f"Gemini API error ({e.code}): {detail}", e.code)
                except urllib.error.URLError as e:
                    reason_str = str(getattr(e, "reason", e))
                    if "timed out" in reason_str.lower():
                        raise ProviderError(
                            "Gemini connection timed out (6s). Check internet/firewall or use Groq (`xsf key set groq <key>`).",
                            504,
                        )
                    raise ProviderError(f"Network error connecting to Gemini: {reason_str}", 503)
                except ProviderError:
                    raise
                except Exception as e:
                    err_str = str(e)
                    code = 504 if "timed out" in err_str.lower() else 503
                    raise ProviderError(f"Gemini request failed: {err_str}", code)

        raise last_error
