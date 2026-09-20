"""
xsf.config - Configuration loader supporting Python 3.9 - 3.13+.
"""
import os
from pathlib import Path
from typing import Any, Dict, List

CONFIG_DIR = Path.home() / ".shellfix"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "general": {
        "aliases": ["xsf", "xefix", "xeeee", "fuxx"],
        "auto_approve_safe": False,
        "help_introspection": True,
    },
    "ai": {
        "enabled": True,
        # Default fast cloud cascade:
        "cascade": ["groq", "cerebras", "gemini", "openrouter"],
        "groq_api_key": "",
        "groq_model": "qwen/qwen3.8-27b",
        "cerebras_api_key": "",
        "cerebras_model": "qwen-3.8-27b",
        "gemini_api_key": "",
        "gemini_model": "gemini-3.6-flash",
        "openrouter_api_key": "",
        "openrouter_model": "meta-llama/llama-3.3-70b-instruct:free",
        # Opt-in paid / private providers:
        "grok_api_key": "",
        "grok_model": "grok-beta",
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


def save_config(cfg: Dict[str, Any]) -> None:
    """Saves dictionary configuration back to ~/.shellfix/config.toml."""
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
                    lines.append(f'{k} = "{v}"')
        lines.append("")
    CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")
    
    import stat
    if os.name != 'nt':  # POSIX only; Windows uses ACLs
        os.chmod(CONFIG_PATH, stat.S_IRUSR | stat.S_IWUSR)
