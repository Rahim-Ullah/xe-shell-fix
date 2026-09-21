"""
xsf.ai.providers.base - Abstract AI provider interface and system prompt.
"""
from abc import ABC, abstractmethod
import json
import re
from typing import Tuple

from xsf.core.command import Command

# Richer, more precise system prompt that produces better JSON consistency
SYSTEM_PROMPT = (
    "You are an expert shell command repair assistant. "
    "You will receive: a shell dialect (powershell/bash/zsh/fish/gitbash), "
    "the failed command string, and optionally its stderr output. "
    "Your ONLY output must be a single raw JSON object with NO markdown, NO code fences, NO extra text. "
    "Schema (strictly required):\n"
    '{"fixed_command": "<the corrected, directly runnable command>", '
    '"explanation": "<one concise sentence, max 20 words>", '
    '"confidence": <float 0.0-1.0>, '
    '"destructive": <true if deletes/overwrites/force-pushes/drops data, else false>}\n'
    "Rules:\n"
    "1. fixed_command must be shell-dialect-aware and directly executable — no placeholders like <value>.\n"
    "2. Preserve all original arguments, paths, and flags that are still valid.\n"
    "3. If the command is fundamentally unfixable, return empty string for fixed_command and confidence 0.0.\n"
    "4. Set destructive=true for: rm -rf, DROP TABLE, git push --force, format drives, dd if=, mkfs.\n"
    "5. Escape special characters correctly for the target shell.\n"
    "6. Never explain the JSON — output the JSON object only."
)


class ProviderError(Exception):
    """Raised when an AI provider fails, rate-limits, or encounters a network error."""

    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code  # HTTP status if available (429 = rate limit)


class BaseProvider(ABC):
    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has necessary API keys or connection settings."""
        pass

    @abstractmethod
    def fix(self, cmd: Command) -> Tuple[str, str, float]:
        """
        Queries the model and returns:
            (fixed_command: str, explanation: str, confidence: float)
        Raises ProviderError on failure.
        """
        pass

    @staticmethod
    def parse_json_response(raw_text: str) -> Tuple[str, str, float, bool]:
        """
        Safely parses model output even if:
        - Wrapped in markdown ```json blocks
        - Has leading/trailing whitespace or extra text
        - Is truncated mid-stream (partial JSON — returns empty command)
        """
        cleaned = raw_text.strip()

        # Strip markdown fences if present (some models ignore the instruction)
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        # Handle models that wrap JSON in <json>...</json> tags
        xml_match = re.search(r"<json>\s*(.*?)\s*</json>", cleaned, re.DOTALL)
        if xml_match:
            cleaned = xml_match.group(1).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Attempt to extract the first complete JSON object with brace matching
            brace_depth = 0
            start = -1
            for i, ch in enumerate(cleaned):
                if ch == "{":
                    if start == -1:
                        start = i
                    brace_depth += 1
                elif ch == "}":
                    brace_depth -= 1
                    if brace_depth == 0 and start != -1:
                        try:
                            data = json.loads(cleaned[start:i + 1])
                            break
                        except json.JSONDecodeError:
                            pass
            else:
                raise ProviderError("Model output was not valid JSON")

        fixed_cmd = (data.get("fixed_command") or "").strip()
        explanation = (data.get("explanation") or "").strip()
        try:
            confidence = min(1.0, max(0.0, float(data.get("confidence", 0.5))))
        except (ValueError, TypeError):
            confidence = 0.5
        destructive = bool(data.get("destructive", False))

        return fixed_cmd, explanation, confidence, destructive
