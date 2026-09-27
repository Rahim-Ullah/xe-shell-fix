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
    "3. If the command failed because the target is already in the desired state (e.g. deleting a file that is already gone, stopping a process that is already dead, creating a folder that already exists) OR if repeating the command would just fail again with the same error, return empty string for fixed_command and confidence 0.0 with a clear explanation.\n"
    "4. Set destructive=true ONLY for mass-destructive actions: rm -rf, DROP TABLE/DATABASE, git push --force, format drives, dd if=, mkfs. Normal single-file removals (e.g. rm file.png) or moves are NOT destructive.\n"
    "5. Escape special characters correctly for the target shell.\n"
    "6. Never explain the JSON — output the JSON object only.\n"
    "7. Adapt paths and syntax to the specified shell (e.g. forward slashes for Git Bash/Bash/Zsh, proper escaping for PowerShell).\n"
    "8. For missing package, runtime, or command-not-found errors, suggest the exact installation, activation, or startup command.\n"
    "9. Natural Language & Cross-Shell Translation: If the user entered natural English instructions or cross-shell terms (e.g. 'delete file.png', 'rename a b', 'move a b', 'show git log', 'find all pdfs', 'extract archive.zip'), translate their intention into the target shell's idiomatic command with high confidence (0.85-0.98)."
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

    @classmethod
    def finalize_prediction(
        cls,
        fixed_cmd: str,
        explanation: str,
        confidence: float,
        destructive_hint: bool = False,
    ) -> Tuple[str, str, float]:
        """
        Authoritative post-processing on AI predictions.
        Only genuinely destructive commands (verified by safety.py) receive a confidence penalty.
        """
        from xsf.core.safety import is_destructive

        if fixed_cmd and is_destructive(fixed_cmd):
            confidence = min(confidence, 0.4)
        return fixed_cmd, explanation, confidence

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

