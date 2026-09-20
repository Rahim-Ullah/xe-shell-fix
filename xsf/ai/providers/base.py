"""
xsf.ai.providers.base - Abstract AI provider interface.
"""
from abc import ABC, abstractmethod
import json
import re
from typing import Tuple

from xsf.core.command import Command

SYSTEM_PROMPT = (
    "You are a terminal command repair assistant. You are given a shell dialect "
    "(powershell, bash, zsh, fish), the failed command, and optionally its error output. "
    "Respond with ONLY a raw JSON object (no markdown code blocks, no backticks, no extra text) "
    "matching this exact schema:\n"
    '{"fixed_command": string, "explanation": string (under 20 words), "confidence": number between 0.0 and 1.0, "destructive": boolean}\n'
    "Rules:\n"
    "1. fixed_command must be a single, directly runnable command tailored to the given shell syntax.\n"
    "2. If you cannot fix the command with confidence, return empty string for fixed_command.\n"
    "3. Set destructive=true if the command deletes, overwrites, drops, force-pushes, or alters system files."
)


class ProviderError(Exception):
    """Raised when an AI provider fails or encounters a network error."""
    pass


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
        """
        pass

    @staticmethod
    def parse_json_response(raw_text: str) -> Tuple[str, str, float, bool]:
        """Safely parses model output even if wrapped in markdown ```json blocks."""
        cleaned = raw_text.strip()
        # Strip markdown fences if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Fallback regex extraction
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
            else:
                raise ProviderError("Model output was not valid JSON")

        cmd = (data.get("fixed_command") or "").strip()
        explanation = (data.get("explanation") or "").strip()
        try:
            confidence = float(data.get("confidence", 0.5))
        except (ValueError, TypeError):
            confidence = 0.5
        destructive = bool(data.get("destructive", False))

        return cmd, explanation, confidence, destructive
