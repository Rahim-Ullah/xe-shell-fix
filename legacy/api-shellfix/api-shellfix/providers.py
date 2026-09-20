"""
providers.py - pluggable AI backends for fixcmd_ai.py.

Only Gemini ships wired up. That's not a style choice - as of 2026 it's the
only major provider with a real, ongoing free tier that doesn't require a
card: https://ai.google.dev/gemini-api/docs/pricing. Grok's API is
promo-credit only ($25 once, expires in ~30 days; no permanent free tier),
so it's not a good fit for "free" as the user asked for it, and isn't wired
up here. If you get your own Grok/OpenRouter/etc key later, add a class
below implementing the same `fix()` interface and register it in
get_provider() - everything else in this project is provider-agnostic.

Model IDs on free tiers change often. If GeminiProvider starts failing with
a 404, check the current free-tier model list at the URL above and update
`model` in ~/.shellfix/config.toml.
"""
import json
import urllib.error
import urllib.request


class ProviderError(Exception):
    pass


SYSTEM_PROMPT = (
    "You are a terminal command doctor. You will be given a shell name, a "
    "command that failed, and optionally its exact error text. Reply with "
    "ONLY a JSON object, no markdown fences, no commentary, matching this "
    "schema exactly: "
    '{"fixed_command": string, "explanation": string (<=20 words), '
    '"confidence": number between 0 and 1, "destructive": boolean}. '
    "fixed_command must be a single, directly runnable command in the given "
    "shell's own syntax (bash, PowerShell, or cmd.exe - they are NOT "
    "interchangeable, mind the differences in path separators, quoting, "
    "and env-var syntax). Set destructive=true for anything that deletes, "
    "overwrites, force-pushes, drops data, or is otherwise hard to undo. "
    'If you cannot confidently fix it, set fixed_command to "".'
)


class Provider:
    def fix(self, raw_command: str, stderr_text: str, shell: str):
        """Returns (fixed_command: str, explanation: str, confidence: float)."""
        raise NotImplementedError


class GeminiProvider(Provider):
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if not api_key:
            raise ProviderError("no Gemini API key configured")
        self.api_key = api_key
        self.model = model

    def fix(self, raw_command, stderr_text, shell):
        user_content = f"shell: {shell}\nfailed_command: {raw_command}\n"
        if stderr_text:
            user_content += f"error_output:\n{stderr_text[:2000]}\n"

        body = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_content}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self.api_key},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", errors="ignore")[:300]
            raise ProviderError(f"Gemini API error {e.code}: {detail}")
        except urllib.error.URLError as e:
            raise ProviderError(f"network error reaching Gemini: {e.reason}")

        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
        except (KeyError, IndexError, json.JSONDecodeError):
            raise ProviderError("Gemini returned something other than the expected JSON")

        cmd = (parsed.get("fixed_command") or "").strip()
        explanation = parsed.get("explanation", "")
        try:
            confidence = float(parsed.get("confidence", 0.5))
        except (TypeError, ValueError):
            confidence = 0.5
        if parsed.get("destructive"):
            # belt-and-suspenders: our own regex denylist in safety.py is
            # authoritative for gating auto-run, but if the model itself
            # flags a command as destructive, don't let a high confidence
            # score alone imply it's safe to auto-run.
            confidence = min(confidence, 0.5)
        return cmd, explanation, confidence


def get_provider(cfg: dict) -> Provider:
    name = cfg.get("provider", "gemini")
    if name == "gemini":
        return GeminiProvider(cfg.get("api_key"), cfg.get("model", "gemini-2.5-flash"))
    raise ProviderError(
        f"unknown provider '{name}' - only 'gemini' ships built in; "
        f"add a class to providers.py that implements fix() and register it in get_provider()"
    )
