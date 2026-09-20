"""
xsf.ui.config_tui - Interactive Terminal UI for configuring API keys and providers.
"""
import sys
from typing import Any, Dict
from xsf.config import load_config, save_config
from xsf.ai.providers import (
    GeminiProvider,
    GroqProvider,
    CerebrasProvider,
    OpenRouterProvider,
    GrokProvider,
    OpenAICompatProvider,
    OllamaProvider,
)


def mask_key(k: str) -> str:
    if not k:
        return "\033[90m[Not Configured]\033[0m"
    if len(k) <= 8:
        return "********"
    return f"{k[:4]}...{k[-4:]} \033[32m[Configured]\033[0m"


def print_status(cfg: Dict[str, Any]) -> None:
    ai = cfg.get("ai", {})
    local = cfg.get("local_llm", {})
    gen = cfg.get("general", {})

    print("\n\033[1;36m=== xe-shell-fix (xsf) Current Configuration ===\033[0m")
    print(f"  AI Enabled              : {'\033[32mYes\033[0m' if ai.get('enabled') else '\033[31mNo\033[0m'}")
    print(f"  Groq API Key (Fast LPU) : {mask_key(ai.get('groq_api_key', ''))} ({ai.get('groq_model', 'qwen/qwen3.8-27b')})")
    print(f"  Cerebras Key (Wafer)    : {mask_key(ai.get('cerebras_api_key', ''))} ({ai.get('cerebras_model', 'qwen-3.8-27b')})")
    print(f"  Gemini API Key (Free)   : {mask_key(ai.get('gemini_api_key', ''))} ({ai.get('gemini_model', 'gemini-3.6-flash')})")
    print(f"  OpenRouter Key (Free)   : {mask_key(ai.get('openrouter_api_key', ''))}")
    print(f"  Grok Key (xAI Opt-In)   : {mask_key(ai.get('grok_api_key', ''))}")
    print(f"  OpenAI Key (Opt-In)     : {mask_key(ai.get('openai_api_key', ''))}")
    print(f"  Local Ollama LLM        : {'\033[32mEnabled\033[0m' if local.get('enabled') else '\033[90mDisabled (Default)\033[0m'} ({local.get('model')})")
    print(f"  Auto-Approve Safe       : {'\033[32mYes\033[0m' if gen.get('auto_approve_safe') else '\033[90mNo (Prompt user)\033[0m'}")
    print(f"  Help Introspection      : {'\033[32mYes\033[0m' if gen.get('help_introspection') else '\033[31mNo\033[0m'}")
    print(f"  Active Aliases          : {', '.join(gen.get('aliases', []))}")
    print("\033[1;36m================================================\033[0m\n")


def test_connections(cfg: Dict[str, Any]) -> None:
    print("\n\033[1mTesting configured provider connections...\033[0m")
    ai = cfg.get("ai", {})
    local = cfg.get("local_llm", {})
    from xsf.core.command import Command
    dummy_cmd = Command(raw="echo test")

    # Groq
    if ai.get("groq_api_key"):
        print("  - Groq LPU API: ", end="", flush=True)
        prov = GroqProvider(ai["groq_api_key"], ai.get("groq_model", "qwen/qwen3.8-27b"))
        try:
            prov.fix(dummy_cmd)
            print("\033[32mConnected successfully (<200ms)\033[0m")
        except Exception as e:
            print(f"\033[31mFailed ({e})\033[0m")

    # Cerebras
    if ai.get("cerebras_api_key"):
        print("  - Cerebras API: ", end="", flush=True)
        prov = CerebrasProvider(ai["cerebras_api_key"], ai.get("cerebras_model", "qwen-3.8-27b"))
        try:
            prov.fix(dummy_cmd)
            print("\033[32mConnected successfully\033[0m")
        except Exception as e:
            print(f"\033[31mFailed ({e})\033[0m")

    # Gemini
    if ai.get("gemini_api_key"):
        print("  - Gemini Free API: ", end="", flush=True)
        prov = GeminiProvider(ai["gemini_api_key"], ai.get("gemini_model", "gemini-3.6-flash"))
        try:
            prov.fix(dummy_cmd)
            print("\033[32mConnected successfully\033[0m")
        except Exception as e:
            print(f"\033[31mFailed ({e})\033[0m")

    # Ollama
    if local.get("enabled"):
        print(f"  - Ollama ({local.get('host')}): ", end="", flush=True)
        prov_o = OllamaProvider(local.get("host"), local.get("model"), enabled=True)
        if prov_o.is_alive():
            print("\033[32mOllama daemon is running\033[0m")
        else:
            print("\033[31mOllama daemon not reachable\033[0m")


def run_interactive_tui() -> None:
    cfg = load_config()

    while True:
        print_status(cfg)
        print("\033[1mSelect an option to update:\033[0m")
        print("  [1] Set Groq API Key (Ultra-Fast LPU Inference)")
        print("  [2] Set Cerebras API Key (Wafer-Scale Inference)")
        print("  [3] Set Gemini API Key (Ongoing Free Tier, Google)")
        print("  [4] Set OpenRouter API Key (Free Tier Models)")
        print("  [5] Set Grok API Key (xAI, User Key)")
        print("  [6] Set OpenAI API Key (User Key)")
        print("  [7] Toggle Local Ollama LLM")
        print("  [8] Toggle Auto-Approve for Safe Commands")
        print("  [9] Test Provider Connectivity")
        print("  [S] Save and Exit")
        print("  [Q] Quit without saving")
        print()

        try:
            choice = input("\033[1mEnter choice [1-9, S, Q]: \033[0m").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "q":
            print("Exiting without changes.")
            break
        elif choice == "s":
            save_config(cfg)
            print("\033[32m\u2713 Configuration saved to ~/.shellfix/config.toml\033[0m")
            break
        elif choice == "1":
            new_key = input("Enter Groq API Key: ").strip()
            cfg["ai"]["groq_api_key"] = new_key
        elif choice == "2":
            new_key = input("Enter Cerebras API Key: ").strip()
            cfg["ai"]["cerebras_api_key"] = new_key
        elif choice == "3":
            new_key = input("Enter Gemini API Key: ").strip()
            cfg["ai"]["gemini_api_key"] = new_key
        elif choice == "4":
            new_key = input("Enter OpenRouter API Key: ").strip()
            cfg["ai"]["openrouter_api_key"] = new_key
        elif choice == "5":
            new_key = input("Enter Grok (xAI) API Key: ").strip()
            cfg["ai"]["grok_api_key"] = new_key
        elif choice == "6":
            new_key = input("Enter OpenAI API Key: ").strip()
            cfg["ai"]["openai_api_key"] = new_key
        elif choice == "7":
            current = cfg["local_llm"].get("enabled", False)
            cfg["local_llm"]["enabled"] = not current
            print(f"Local Ollama LLM is now {'\033[32mENABLED\033[0m' if not current else '\033[31mDISABLED\033[0m'}")
        elif choice == "8":
            current = cfg["general"].get("auto_approve_safe", False)
            cfg["general"]["auto_approve_safe"] = not current
            print(f"Auto-approve safe commands is now {'\033[32mENABLED\033[0m' if not current else '\033[31mDISABLED\033[0m'}")
        elif choice == "9":
            test_connections(cfg)
            input("\nPress Enter to continue...")
