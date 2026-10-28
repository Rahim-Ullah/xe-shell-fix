"""
xsf.config - Configuration loader supporting Python 3.9 - 3.13+.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CONFIG_DIR = Path.home() / ".shellfix"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "aliases": ["xsf", "xefix", "xeeee", "fuxx"],
        "power_mode": "hybrid",        # "hybrid" | "offline" | "ai_only" | "off"
        "auto_approve_safe": False,
        "help_introspection": True,
        "quiet_failover": True,        # Suppress transient provider error noise during cascade
        "setup_completed": False,
    },
    "ai": {
        "enabled": True,
        # Default fast cloud cascade (Groq first — fastest LPU inference):
        "cascade": ["groq", "gemini", "cerebras", "openrouter"],
        "groq_api_key": "",
        "groq_model": "qwen/qwen3.8-27b",          # High-speed active model on Groq LPU
        "cerebras_api_key": "",
        "cerebras_model": "llama3.1-8b",
        "gemini_api_key": "",
        "gemini_model": "gemini-flash-latest",     # Canonical flash alias (always active, resilient)
        "openrouter_api_key": "",
        "openrouter_model": "meta-llama/llama-3.3-70b-instruct:free",
        # Opt-in paid / private providers (not in default cascade):
        "grok_api_key": "",
        "grok_model": "grok-2-latest",
        "openai_api_key": "",
        "openai_model": "gpt-4o-mini",
        "openai_base_url": "",
    },
    "local_llm": {
        "enabled": False,  # Opt-in to avoid CPU latency spikes
        "host": "http://localhost:11434",
        "model": "qwen2.5-coder:1.5b",
    },
}

PROVIDER_METADATA: Dict[str, Dict[str, str]] = {
    "groq": {
        "title": "Groq LPU (Free Tier — Ultra-Fast ~200ms)",
        "key_field": "groq_api_key",
        "model_field": "groq_model",
        "env_var": "GROQ_API_KEY",
        "prefix_hint": "gsk_",
        "portal_url": "https://console.groq.com/keys",
        "free_tier": "14,400 req/day, 30 req/min (Free, no credit card)",
    },
    "gemini": {
        "title": "Google Gemini (Free Tier — 1,500 req/day)",
        "key_field": "gemini_api_key",
        "model_field": "gemini_model",
        "env_var": "GEMINI_API_KEY",
        "prefix_hint": "AIza",
        "portal_url": "https://aistudio.google.com/app/apikey",
        "free_tier": "1,500 req/day, 15 req/min (Free via Google AI Studio)",
    },
    "openrouter": {
        "title": "OpenRouter (Free Models Tier)",
        "key_field": "openrouter_api_key",
        "model_field": "openrouter_model",
        "env_var": "OPENROUTER_API_KEY",
        "prefix_hint": "sk-or-",
        "portal_url": "https://openrouter.ai/keys",
        "free_tier": "Free ':free' models (Llama 3.3 70B, Qwen 2.5 Coder 32B)",
    },
    "cerebras": {
        "title": "Cerebras Wafer-Scale Inference",
        "key_field": "cerebras_api_key",
        "model_field": "cerebras_model",
        "env_var": "CEREBRAS_API_KEY",
        "prefix_hint": "csk-",
        "portal_url": "https://cloud.cerebras.ai/",
        "free_tier": "High-speed wafer-scale inference tier",
    },
    "grok": {
        "title": "xAI Grok (Opt-In)",
        "key_field": "grok_api_key",
        "model_field": "grok_model",
        "env_var": "GROK_API_KEY",
        "prefix_hint": "xai-",
        "portal_url": "https://console.x.ai/",
        "free_tier": "Opt-in paid / credit tier",
    },
    "openai": {
        "title": "OpenAI / Compatible Endpoint (Opt-In)",
        "key_field": "openai_api_key",
        "model_field": "openai_model",
        "env_var": "OPENAI_API_KEY",
        "prefix_hint": "sk-",
        "portal_url": "https://platform.openai.com/api-keys",
        "free_tier": "Opt-in paid / custom base_url (DeepSeek, Mistral, etc.)",
    },
}


def sanitize_api_key(raw_key: str) -> str:
    """
    Cleans user-pasted API key strings (strips surrounding quotes, 'Bearer ' prefix,
    and stray whitespace). Supports comma-separated backup keys.
    """
    if not raw_key:
        return ""
    parts = []
    for chunk in raw_key.split(","):
        cleaned = chunk.strip().strip("'\"")
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip().strip("'\"")
        if cleaned:
            parts.append(cleaned)
    return ",".join(parts)


def parse_key_list(raw_key: str) -> List[str]:
    """Splits a configured key string into individual keys (supporting primary + backup keys)."""
    sanitized = sanitize_api_key(raw_key)
    if not sanitized:
        return []
    return [k.strip() for k in sanitized.split(",") if k.strip()]


def validate_api_key(provider: str, raw_key: str) -> Tuple[bool, str, str]:
    """
    Validates and sanitizes an API key for the given provider.
    Returns: (is_valid, sanitized_key, message)
    """
    prov = provider.lower().strip()
    if prov not in PROVIDER_METADATA:
        return False, "", f"Unknown provider '{provider}'. Valid: {', '.join(PROVIDER_METADATA.keys())}"

    cleaned = sanitize_api_key(raw_key)
    if not cleaned:
        return False, "", "API key cannot be empty."

    keys = parse_key_list(cleaned)
    meta = PROVIDER_METADATA[prov]
    prefix = meta.get("prefix_hint", "")
    warnings = []

    for idx, k in enumerate(keys, 1):
        if len(k) < 12:
            return False, "", f"Key #{idx} is too short ({len(k)} chars). Please copy the full API key from {meta['portal_url']}."
        if any(ch.isspace() for ch in k):
            return False, "", f"Key #{idx} contains spaces or control characters. Check your paste."
        if prefix and not k.startswith(prefix):
            warnings.append(f"Note: {prov.capitalize()} keys usually start with '{prefix}' (saved anyway).")

    msg = f"Validated {len(keys)} key(s) for {prov.capitalize()}."
    if warnings:
        msg += " " + warnings[0]
    return True, cleaned, msg


def _simple_toml_parse(content: str) -> Dict[str, Any]:
    """Lightweight fallback TOML parser for Python 3.9/3.10 standard library."""
    result: Dict[str, Any] = {}
    current_section = result
    
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section_name = line[1:-1].strip()
            current_section = result.setdefault(section_name, {})
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()

            # Handle comments while respecting quoted strings
            if val.startswith('"'):
                end_quote = val.find('"', 1)
                if end_quote != -1:
                    val = val[:end_quote + 1]
            elif val.startswith("'"):
                end_quote = val.find("'", 1)
                if end_quote != -1:
                    val = val[:end_quote + 1]
            elif "#" in val and not val.startswith("["):
                val = val.split("#", 1)[0].strip()

            # Simple type conversions
            if val.lower() == "true":
                current_section[key] = True
            elif val.lower() == "false":
                current_section[key] = False
            elif val.isdigit():
                current_section[key] = int(val)
            elif (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                current_section[key] = val[1:-1]
            elif val.startswith("[") and val.endswith("]"):
                # comma separated items
                inner = val[1:-1].strip()
                if not inner:
                    current_section[key] = []
                else:
                    items = [it.strip().strip('"\'') for it in inner.split(",") if it.strip()]
                    current_section[key] = items
            else:
                # Try float before falling back to raw string
                try:
                    current_section[key] = float(val)
                except ValueError:
                    current_section[key] = val
    return result


def load_config() -> Dict[str, Any]:
    """Loads config with fallbacks to environment variables and defaults."""
    cfg = {
        "general": dict(DEFAULT_CONFIG["general"]),
        "ai": dict(DEFAULT_CONFIG["ai"]),
        "local_llm": dict(DEFAULT_CONFIG["local_llm"]),
    }

    if CONFIG_PATH.exists():
        try:
            try:
                import tomllib  # Python 3.11+
                with open(CONFIG_PATH, "rb") as f:
                    file_cfg = tomllib.load(f)
            except ModuleNotFoundError:
                content = CONFIG_PATH.read_text(encoding="utf-8")
                file_cfg = _simple_toml_parse(content)

            for section, vals in file_cfg.items():
                if section in cfg and isinstance(vals, dict):
                    cfg[section].update(vals)
                else:
                    cfg[section] = vals
        except Exception:
            pass
        secure_config_permissions(CONFIG_PATH)

    # Environment variable overrides
    if os.environ.get("GROQ_API_KEY"):
        cfg["ai"]["groq_api_key"] = os.environ["GROQ_API_KEY"]
    if os.environ.get("CEREBRAS_API_KEY"):
        cfg["ai"]["cerebras_api_key"] = os.environ["CEREBRAS_API_KEY"]
    if os.environ.get("GEMINI_API_KEY"):
        cfg["ai"]["gemini_api_key"] = os.environ["GEMINI_API_KEY"]
    if os.environ.get("OPENROUTER_API_KEY"):
        cfg["ai"]["openrouter_api_key"] = os.environ["OPENROUTER_API_KEY"]
    if os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY"):
        cfg["ai"]["grok_api_key"] = os.environ.get("GROK_API_KEY") or os.environ.get("XAI_API_KEY")
    if os.environ.get("OPENAI_API_KEY"):
        cfg["ai"]["openai_api_key"] = os.environ["OPENAI_API_KEY"]
    if os.environ.get("OLLAMA_HOST"):
        cfg["local_llm"]["host"] = os.environ["OLLAMA_HOST"]

    return cfg


def secure_config_permissions(target_path: Optional[Path] = None) -> None:
    """
    Enforces strict owner-only read/write permissions cross-platform.
    - POSIX (Linux/macOS): chmod 0600 on config.toml, 0700 on ~/.shellfix directory.
    - Windows: Uses icacls to disable inheritance (/inheritance:r) and grant
      exclusive Full Control (/grant:r) ONLY to the current user (%USERNAME%),
      stripping inherited ACLs that would otherwise allow BUILTIN\\Users to read plain-text API keys.
    """
    path = target_path or CONFIG_PATH
    try:
        if os.name != "nt":
            import stat
            if path.exists():
                if path.is_dir():
                    os.chmod(path, stat.S_IRWXU)
                else:
                    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
            if (target_path is None or target_path == CONFIG_PATH) and CONFIG_DIR.exists():
                os.chmod(CONFIG_DIR, stat.S_IRWXU)
        else:
            import subprocess
            username = os.environ.get("USERNAME")
            if username:
                if path.exists():
                    perm = f"{username}:(OI)(CI)(F)" if path.is_dir() else f"{username}:(F)"
                    subprocess.run(
                        ["icacls", str(path), "/inheritance:r", "/grant:r", perm],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                if (target_path is None or target_path == CONFIG_PATH) and CONFIG_DIR.exists():
                    subprocess.run(
                        ["icacls", str(CONFIG_DIR), "/inheritance:r", "/grant:r", f"{username}:(OI)(CI)(F)"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
    except Exception:
        pass



def save_config(cfg: Dict[str, Any]) -> None:
    """Saves dictionary configuration back to ~/.shellfix/config.toml with strict permissions."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "# xe-shell-fix (xsf) configuration file",
        "# Auto-generated or edited via `xsf config`",
        "",
    ]
    for section, vals in cfg.items():
        lines.append(f"[{section}]")
        if isinstance(vals, dict):
            for k, v in vals.items():
                if isinstance(v, bool):
                    lines.append(f"{k} = {'true' if v else 'false'}")
                elif isinstance(v, (int, float)):
                    lines.append(f"{k} = {v}")
                elif isinstance(v, list):
                    items_str = ", ".join(f'"{x}"' for x in v)
                    lines.append(f"{k} = [{items_str}]")
                else:
                    lines.append(f'{k} = {json.dumps(str(v))}')
        lines.append("")
    CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")
    secure_config_permissions(CONFIG_PATH)
