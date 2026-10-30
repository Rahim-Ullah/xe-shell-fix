"""
xsf.ui.config_tui - Interactive Terminal UI, Power Switch, Key Manager, and Onboarding Wizard.
"""
import os
from pathlib import Path
import sys
from typing import Any, Dict, List

from xsf.config import (
    CONFIG_PATH,
    PROVIDER_METADATA,
    load_config,
    parse_key_list,
    save_config,
    validate_api_key,
)
from xsf.ai.router import ProviderHealthTracker
from xsf.ai.providers import (
    GeminiProvider,
    GroqProvider,
    CerebrasProvider,
    OpenRouterProvider,
    GrokProvider,
    OpenAICompatProvider,
    OllamaProvider,
)

POWER_MODES = {
    "hybrid": "HYBRID (Instant Offline + Cloud AI Fallback)",
    "offline": "OFFLINE-ONLY (100% Local Heuristics, Zero Cloud Quota)",
    "ai_only": "AI-ONLY (Direct Cloud/Local LLM Diagnosis)",
    "off": "OFF (xsf Engine Paused)",
}


def mask_key(k: str) -> str:
    keys = parse_key_list(k)
    if not keys:
        return "\033[90m[Not Configured]\033[0m"
    primary = keys[0]
    masked = "********" if len(primary) <= 8 else f"{primary[:4]}...{primary[-4:]}"
    extra = f" (+{len(keys) - 1} backup)" if len(keys) > 1 else ""
    return f"{masked}{extra} \033[32m[Configured]\033[0m"


def format_power_badge(mode: str) -> str:
    m = (mode or "hybrid").lower()
    if m == "hybrid":
        return "\033[1;32m⚡ HYBRID (Offline + AI Fallback)\033[0m"
    elif m == "offline":
        return "\033[1;33m🔒 OFFLINE-ONLY (Zero Network / Zero Quota)\033[0m"
    elif m == "ai_only":
        return "\033[1;36m☁️  AI-ONLY (Direct AI Diagnosis)\033[0m"
    elif m == "off":
        return "\033[1;31m⏸️  OFF (Engine Paused)\033[0m"
    return m


def print_status(cfg: Dict[str, Any]) -> None:
    ai = cfg.get("ai", {})
    local = cfg.get("local_llm", {})
    gen = cfg.get("general", {})

    power_mode = gen.get("power_mode", "hybrid")
    if not ai.get("enabled", True) and power_mode == "hybrid":
        power_mode = "offline"

    local_status = "\033[32mEnabled\033[0m" if local.get("enabled") else "\033[90mDisabled\033[0m"
    auto_status = "\033[32mYes\033[0m" if gen.get("auto_approve_safe") else "\033[90mNo (Prompt user)\033[0m"
    help_status = "\033[32mYes\033[0m" if gen.get("help_introspection") else "\033[31mNo\033[0m"

    print("\n\033[1;36m=== xe-shell-fix (xsf) Power & Key Control Center ===\033[0m")
    print(f"  Config File             : {CONFIG_PATH}")
    print(f"  Power Switch Mode       : {format_power_badge(power_mode)}")
    print("  ----------------------------------------------------")
    for prov_id in ("groq", "gemini", "openrouter", "cerebras", "grok", "openai"):
        meta = PROVIDER_METADATA[prov_id]
        raw_k = ai.get(meta["key_field"], "")
        health = ProviderHealthTracker.describe_provider_health(prov_id, raw_k)
        label = f"{prov_id.capitalize()} Key".ljust(23)
        print(f"  {label} : {mask_key(raw_k)} | {health}")
    print("  ----------------------------------------------------")
    print(f"  Local Ollama LLM        : {local_status} ({local.get('model')})")
    print(f"  Auto-Approve Safe       : {auto_status}")
    print(f"  Help Introspection      : {help_status}")
    print(f"  Active Aliases          : {', '.join(gen.get('aliases', []))}")
    print("\033[1;36m======================================================\033[0m\n")


def print_commands_reference() -> None:
    """Prints the complete cheat sheet of all xsf commands, flags, aliases, and subcommands."""
    print("\n\033[1;36m╔══════════════════════════════════════════════════════════════════════════╗\033[0m")
    print("\033[1;36m║                xe-shell-fix (xsf) — Complete Command Reference           ║\033[0m")
    print("\033[1;36m╚══════════════════════════════════════════════════════════════════════════╝\033[0m")

    print("\n\033[1;32m1. Automatic & Quick Repair Triggers (Run after any failed command)\033[0m")
    print("   \033[1mxsf\033[0m                      Diagnose & fix the previous failed command")
    print("   \033[1mxefix\033[0m / \033[1mxeeee\033[0m / \033[1mfuxx\033[0m     Fast ergonomic aliases for `xsf`")

    print("\n\033[1;32m2. Direct Command Repair & AI Terminal Assistant\033[0m")
    print("   \033[1mxsf \"<broken_cmd>\"\033[0m       Fix a specific command string directly")
    print("   \033[1mxsf --ai\033[0m                 Force Cloud/Local AI on the last failed command")
    print("   \033[1mxsf --ai \"<question>\"\033[0m    Ask AI a terminal question, explain a command, or generate")
    print("                            a command from plain English (e.g. `xsf --ai \"what is cd\"`)")
    print("   \033[1mxsf --offline \"<cmd>\"\033[0m    Force 100% offline heuristics (<5ms, zero network)")
    print("   \033[1mxsf --auto \"<cmd>\"\033[0m       Auto-execute safe high-confidence fixes without prompting")
    print("   \033[1mxsf --dry-run \"<cmd>\"\033[0m    Preview the suggested fix without executing it")
    print("   \033[1mxsf --no-cache \"<cmd>\"\033[0m   Bypass the 7-day local AI query cache")

    print("\n\033[1;32m3. Engine Power Switch (`xsf power`)\033[0m")
    print("   \033[1mxsf power status\033[0m         Show active Power Mode, masked keys, and live health")
    print("   \033[1mxsf power hybrid\033[0m         Default: Instant Offline (<5ms) -> Cloud AI fallback")
    print("   \033[1mxsf power offline\033[0m        100% Offline heuristics only (saves 100% API quota)")
    print("   \033[1mxsf power ai\033[0m             Force direct AI diagnosis for all commands")
    print("   \033[1mxsf power off\033[0m            Pause the xsf engine completely")
    print("   \033[1mxsf power reset\033[0m          Clear all provider rate-limit (429/402/504) cooldowns")

    print("\n\033[1;32m4. API Key & Account Manager (`xsf key`)\033[0m")
    print("   \033[1mxsf key list\033[0m             List configured provider keys and verification health")
    print("   \033[1mxsf key set <p> <key>\033[0m    Attach/switch key for <groq|gemini|openrouter|cerebras|grok|openai>")
    print("                            (Tip: pass `--test` to verify live, or comma-separate backup keys)")
    print("   \033[1mxsf key remove <p>\033[0m       Remove the stored API key for provider <p>")
    print("   \033[1mxsf key test\033[0m             Run live connectivity & auth check on all configured keys")
    print("   \033[1mxsf key guide\033[0m            Show step-by-step free API key URLs and prefix formats")

    print("\n\033[1;32m5. Setup, Settings & Shell Integration\033[0m")
    print("   \033[1mxsf setup\033[0m                Launch interactive onboarding wizard (Mode + Keys + Hook)")
    print("   \033[1mxsf config\033[0m               Open interactive Settings & Key Control Center TUI")
    print("   \033[1mxsf config --list\033[0m        Print current configuration summary non-interactively")
    print("   \033[1mxsf commands\033[0m             Display this complete command cheat sheet")
    print("   \033[1mxsf init <shell>\033[0m         Output hook script for <bash|zsh|fish|powershell|pwsh|gitbash>")
    print("   \033[1mxsf --version\033[0m            Print installed xsf version\n")


def print_key_guides() -> None:
    print("\n\033[1;36m=== Step-by-Step Free API Key Setup Guide ===\033[0m")
    print("  Attach your own personal keys so your quota is 100% yours (detailed docs in `guides/`):\n")
    for idx, (prov_id, meta) in enumerate(PROVIDER_METADATA.items(), 1):
        print(f"  \033[1m{idx}. {meta['title']}\033[0m")
        print(f"     • Portal URL : \033[4m{meta['portal_url']}\033[0m")
        print(f"     • Allowance  : {meta['free_tier']}")
        print(f"     • Key Format : Starts with '{meta['prefix_hint']}...' (Tip: separate backup keys with a comma)")
        print(f"     • Quick CLI  : \033[32mxsf key set {prov_id} YOUR_API_KEY\033[0m\n")


def _build_provider_instance(prov_id: str, api_key: str, ai_cfg: Dict[str, Any]):
    first_key = parse_key_list(api_key)[0] if parse_key_list(api_key) else ""
    if prov_id == "groq":
        return GroqProvider(first_key, ai_cfg.get("groq_model", "qwen/qwen3.8-27b"))
    elif prov_id == "gemini":
        return GeminiProvider(first_key, ai_cfg.get("gemini_model", "gemini-flash-latest"))
    elif prov_id == "cerebras":
        return CerebrasProvider(first_key, ai_cfg.get("cerebras_model", "llama3.1-8b"))
    elif prov_id == "openrouter":
        return OpenRouterProvider(first_key, ai_cfg.get("openrouter_model", "meta-llama/llama-3.3-70b-instruct:free"))
    elif prov_id == "grok":
        return GrokProvider(first_key, ai_cfg.get("grok_model", "grok-2-latest"))
    elif prov_id == "openai":
        return OpenAICompatProvider(
            first_key,
            ai_cfg.get("openai_model", "gpt-4o-mini"),
            ai_cfg.get("openai_base_url", ""),
        )
    return None


def test_connections(cfg: Dict[str, Any]) -> None:
    print("\n\033[1mTesting configured provider connections...\033[0m")
    ai = cfg.get("ai", {})
    local = cfg.get("local_llm", {})
    from xsf.core.command import Command
    from xsf.ui.spinner import StatusSpinner, flush_stdin
    dummy_cmd = Command(raw="gti status")
    any_tested = False

    for prov_id, meta in PROVIDER_METADATA.items():
        raw_k = ai.get(meta["key_field"], "")
        keys = parse_key_list(raw_k)
        if not keys:
            continue
        any_tested = True
        prov = _build_provider_instance(prov_id, raw_k, ai)
        try:
            with StatusSpinner(f"Testing {meta['title']} ({len(keys)} key(s))..."):
                prov.fix(dummy_cmd)
            ProviderHealthTracker.record_success(prov_id, keys[0])
            print(f"  - {meta['title']} ({len(keys)} key(s)): \033[32m✓ Connected & Verified\033[0m")
        except Exception as e:
            code = getattr(e, "status_code", 0) or (401 if "401" in str(e) or "403" in str(e) or "invalid" in str(e).lower() else 504 if "timed out" in str(e).lower() else 503)
            ProviderHealthTracker.record_failure(prov_id, keys[0], code, str(e))
            print(f"  - {meta['title']} ({len(keys)} key(s)): \033[31m✗ Failed ({e})\033[0m")

    if local.get("enabled"):
        any_tested = True
        print(f"  - Ollama ({local.get('host')}): ", end="", flush=True)
        prov_o = OllamaProvider(local.get("host"), local.get("model"), enabled=True)
        if prov_o.is_alive():
            print("\033[32m✓ Ollama daemon is running\033[0m")
        else:
            print("\033[31m✗ Ollama daemon not reachable\033[0m")

    flush_stdin()
    if not any_tested:
        print("  \033[90mNo AI keys configured yet. Run `xsf setup` or `xsf key set <provider> <key>`.\033[0m")


def _prompt_and_set_key(cfg: Dict[str, Any], prov_id: str) -> None:
    meta = PROVIDER_METADATA[prov_id]
    current_raw = cfg["ai"].get(meta["key_field"], "")
    print(f"\n\033[1;36m--- Configure {meta['title']} ---\033[0m")
    print(f"  1. Get your key at : \033[4m{meta['portal_url']}\033[0m")
    print(f"  2. Tier details    : {meta['free_tier']}")
    print(f"  3. Current status  : {mask_key(current_raw)}")
    print("  (Tip: Paste 1 key, or multiple comma-separated keys for automatic account rotation. Leave blank to cancel, or type 'clear' to remove.)")
    try:
        raw_in = input(f"\n  Paste {prov_id.capitalize()} API Key(s): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Cancelled.")
        return

    if not raw_in:
        print("  Unchanged.")
        return

    if raw_in.lower() in ("clear", "none", "delete", "remove"):
        cfg["ai"][meta["key_field"]] = ""
        ProviderHealthTracker.reset(prov_id)
        print(f"  \033[33mRemoved {prov_id.capitalize()} key.\033[0m")
        return

    ok, cleaned, msg = validate_api_key(prov_id, raw_in)
    if not ok:
        print(f"  \033[31m✗ {msg}\033[0m")
        return

    cfg["ai"][meta["key_field"]] = cleaned
    ProviderHealthTracker.reset(prov_id)
    print(f"  \033[32m✓ {msg}\033[0m")


def handle_power_cli(args: List[str]) -> int:
    """
    CLI handler for `xsf power [hybrid|on|offline|ai|off|status|reset]`.
    """
    cfg = load_config()
    action = args[0].lower() if args else "status"

    if action == "status":
        print_status(cfg)
        return 0
    elif action == "reset":
        ProviderHealthTracker.reset()
        print("\033[32m✓ All AI provider rate-limit cooldowns and circuit breakers have been reset.\033[0m")
        return 0
    elif action in ("on", "hybrid"):
        cfg["general"]["power_mode"] = "hybrid"
        cfg["ai"]["enabled"] = True
        save_config(cfg)
        print(f"\033[32m✓ Power Switch set to: {format_power_badge('hybrid')}\033[0m")
        return 0
    elif action == "offline":
        cfg["general"]["power_mode"] = "offline"
        cfg["ai"]["enabled"] = False
        save_config(cfg)
        print(f"\033[33m✓ Power Switch set to: {format_power_badge('offline')}\033[0m")
        return 0
    elif action in ("ai", "ai_only", "ai-only"):
        cfg["general"]["power_mode"] = "ai_only"
        cfg["ai"]["enabled"] = True
        save_config(cfg)
        print(f"\033[36m✓ Power Switch set to: {format_power_badge('ai_only')}\033[0m")
        return 0
    elif action == "off":
        cfg["general"]["power_mode"] = "off"
        save_config(cfg)
        print(f"\033[31m✓ Power Switch set to: {format_power_badge('off')}\033[0m")
        return 0
    else:
        sys.stderr.write("xsf: usage: xsf power <on|hybrid|offline|ai|off|status|reset>\n")
        return 1


def handle_key_cli(args: List[str]) -> int:
    """
    CLI handler for `xsf key [list | set <provider> <key> [--test] | remove <provider> | test | guide]`.
    """
    cfg = load_config()
    sub = args[0].lower() if args else "list"

    if sub in ("list", "status"):
        print_status(cfg)
        return 0
    elif sub in ("guide", "guides", "help"):
        print_key_guides()
        return 0
    elif sub == "test":
        test_connections(cfg)
        return 0
    elif sub == "set":
        if len(args) < 3:
            sys.stderr.write(f"xsf: usage: xsf key set <{'|'.join(PROVIDER_METADATA.keys())}> <api_key> [--test]\n")
            return 1
        prov = args[1].lower()
        raw_key = args[2]
        ok, cleaned, msg = validate_api_key(prov, raw_key)
        if not ok:
            sys.stderr.write(f"xsf: {msg}\n")
            return 1
        meta = PROVIDER_METADATA[prov]
        cfg["ai"][meta["key_field"]] = cleaned
        cfg["general"]["setup_completed"] = True
        ProviderHealthTracker.reset(prov)
        save_config(cfg)
        print(f"\033[32m✓ {msg} Saved to {CONFIG_PATH}\033[0m")
        if "--test" in args:
            test_connections(cfg)
        return 0
    elif sub in ("remove", "rm", "clear", "delete"):
        if len(args) < 2 or args[1].lower() not in PROVIDER_METADATA:
            sys.stderr.write(f"xsf: usage: xsf key remove <{'|'.join(PROVIDER_METADATA.keys())}>\n")
            return 1
        prov = args[1].lower()
        meta = PROVIDER_METADATA[prov]
        cfg["ai"][meta["key_field"]] = ""
        ProviderHealthTracker.reset(prov)
        save_config(cfg)
        print(f"\033[33m✓ Removed API key for {prov.capitalize()}.\033[0m")
        return 0
    else:
        sys.stderr.write("xsf: usage: xsf key <list|set|remove|test|guide>\n")
        return 1


def _install_shell_hook_interactive() -> None:
    """Offers to automatically install the xsf shell hook into the user's shell RC file."""
    shell_env = os.environ.get("SHELL", "").lower()
    if os.name == "nt" and not shell_env:
        default_shell = "powershell"
    elif "zsh" in shell_env:
        default_shell = "zsh"
    elif "fish" in shell_env:
        default_shell = "fish"
    else:
        default_shell = "bash"

    print("\n\033[1;36m=== Step 3: Automatic Shell Hook Activation ===\033[0m")
    print(f"  Detected default shell: \033[1m{default_shell}\033[0m")
    try:
        ans = input(f"  Automatically add `xsf` hook to your {default_shell} profile? [Y/n]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if ans and not ans.startswith("y"):
        print("  Skipped automatic profile edit. You can run `xsf init <shell>` anytime.")
        return

    home = Path.home()
    py_exe = sys.executable.replace("\\", "/")
    if default_shell == "zsh":
        rc_path = home / ".zshrc"
        hook_line = f'eval "$(\\"{py_exe}\\" -m xsf.cli init zsh 2>/dev/null || python3 -m xsf.cli init zsh 2>/dev/null || command xsf init zsh)"'
    elif default_shell == "fish":
        rc_path = home / ".config" / "fish" / "config.fish"
        hook_line = f'"{py_exe}" -m xsf.cli init fish | source'
    elif default_shell == "powershell":
        rc_path = home / "Documents" / "PowerShell" / "Microsoft.PowerShell_profile.ps1"
        hook_line = f'try {{ (& "{py_exe}" -m xsf.cli init powershell | Out-String) | Invoke-Expression }} catch {{ try {{ (& (Get-Command -CommandType Application xsf -ErrorAction Stop | Select-Object -First 1) init powershell | Out-String) | Invoke-Expression }} catch {{ (& python -m xsf.cli init powershell | Out-String) | Invoke-Expression }} }}'
    else:
        rc_path = home / ".bashrc"
        hook_line = f'eval "$(\\"{py_exe}\\" -m xsf.cli init bash 2>/dev/null || python3 -m xsf.cli init bash 2>/dev/null || command xsf init bash)"'

    try:
        rc_path.parent.mkdir(parents=True, exist_ok=True)
        existing = rc_path.read_text(encoding="utf-8", errors="ignore") if rc_path.exists() else ""
        if "xsf init" in existing or "xsf.cli init" in existing:
            print(f"  \033[32m✓ Hook already present in {rc_path}\033[0m")
        else:
            with open(rc_path, "a", encoding="utf-8") as f:
                f.write(f"\n# xe-shell-fix (xsf) shell hook\n{hook_line}\n")
            print(f"  \033[32m✓ Added hook to {rc_path}\033[0m")
            print(f"  \033[1mRun `source {rc_path}` (or restart your terminal) to activate!\033[0m")
    except Exception as e:
        print(f"  \033[33mCould not auto-update {rc_path} ({e}). Add manually: {hook_line}\033[0m")

    # Ensure binary symlinks in ~/.local/bin if available on POSIX
    if os.name != "nt":
        local_bin = home / ".local" / "bin"
        try:
            if local_bin.exists() or (home / ".local").exists():
                local_bin.mkdir(parents=True, exist_ok=True)
                bin_dir = Path(sys.executable).parent
                for alias in ("xsf", "xefix", "xeeee", "fuxx"):
                    src = bin_dir / alias
                    dst = local_bin / alias
                    if src.exists() and (not dst.exists() or dst.is_symlink()):
                        dst.unlink(missing_ok=True)
                        dst.symlink_to(src)
        except OSError:
            pass


def run_setup_wizard() -> int:
    """
    Guided first-run / post-install interactive setup wizard (`xsf setup`).
    """
    cfg = load_config()
    print("\n\033[1;36m╔══════════════════════════════════════════════════════════════╗\033[0m")
    print("\033[1;36m║      Welcome to xe-shell-fix (xsf) — Setup & Key Wizard     ║\033[0m")
    print("\033[1;36m╚══════════════════════════════════════════════════════════════╝\033[0m")
    print("  Configure your Power Switch and attach your own free AI keys")
    print("  so your rate limits stay 100% dedicated to you.\n")

    print("\033[1;36m=== Step 1: Choose Your Engine Power Mode ===\033[0m")
    print("  [1] ⚡ HYBRID (Recommended) — Instant <5ms Offline Heuristics + Free Cloud AI Fallback")
    print("  [2] 🔒 OFFLINE-ONLY        — 100% Offline Rules & Vocabulary (Zero Network / No Keys Needed)")
    print("  [3] 💻 LOCAL OLLAMA        — Offline Heuristics + Local Ollama Daemon (100% Private)")

    try:
        mode_choice = input("\n  Select mode [1-3, Enter=1]: ").strip() or "1"
    except (EOFError, KeyboardInterrupt):
        print("\nSetup cancelled.")
        return 1

    if mode_choice == "2":
        cfg["general"]["power_mode"] = "offline"
        cfg["ai"]["enabled"] = False
        print("  \033[33m✓ Selected OFFLINE-ONLY mode.\033[0m")
    elif mode_choice == "3":
        cfg["general"]["power_mode"] = "hybrid"
        cfg["local_llm"]["enabled"] = True
        print("  \033[32m✓ Enabled Local Ollama LLM tier.\033[0m")
    else:
        cfg["general"]["power_mode"] = "hybrid"
        cfg["ai"]["enabled"] = True
        print("  \033[32m✓ Selected HYBRID mode.\033[0m")

        print("\n\033[1;36m=== Step 2: Attach Your Personal Free AI Keys ===\033[0m")
        print("  Press Enter on any provider you want to skip. You can switch keys anytime via `xsf config` or `xsf key`.")
        for prov_id in ("groq", "gemini", "openrouter", "cerebras"):
            _prompt_and_set_key(cfg, prov_id)

    cfg["general"]["setup_completed"] = True
    save_config(cfg)
    print(f"\n\033[32m✓ Configuration saved with strict owner-only permissions to {CONFIG_PATH}\033[0m")

    if cfg["ai"].get("enabled"):
        test_connections(cfg)

    _install_shell_hook_interactive()
    print("\n\033[1;32m🎉 Setup complete! Type `xsf power status` or `xsf config` anytime.\033[0m\n")
    return 0


def run_interactive_tui() -> None:
    cfg = load_config()
    power_cycle = ["hybrid", "offline", "ai_only", "off"]

    while True:
        print_status(cfg)
        print("\033[1mSelect an action:\033[0m")
        print("  [P] Toggle Power Switch Mode (Hybrid → Offline-Only → AI-Only → Off)")
        print("  [1] Set / Switch Groq API Key       (Free Tier, ~200ms LPU)")
        print("  [2] Set / Switch Gemini API Key     (Free Tier, 1,500 req/day)")
        print("  [3] Set / Switch OpenRouter API Key (Free Models Tier)")
        print("  [4] Set / Switch Cerebras API Key   (Wafer-Scale Inference)")
        print("  [5] Set / Switch Grok API Key       (xAI Opt-In)")
        print("  [6] Set / Switch OpenAI API Key     (OpenAI / Custom Endpoint)")
        print("  [7] Toggle Local Ollama LLM")
        print("  [8] Toggle Auto-Approve for Safe Commands")
        print("  [9] Test All Configured Keys & Connections")
        print("  [R] Reset Rate-Limit Cooldowns / Circuit Breakers")
        print("  [C] View All xsf Commands & Cheat Sheet (`xsf commands`)")
        print("  [G] View Step-by-Step Free API Key Setup Guide")
        print("  [W] Run Full Guided Setup Wizard (`xsf setup`)")
        print("  [S] Save and Exit")
        print("  [Q] Quit without saving")
        print()

        try:
            choice = input("\033[1mEnter choice [P, 1-9, R, C, G, W, S, Q]: \033[0m").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if choice == "q":
            print("Exiting without changes.")
            break
        elif choice == "s":
            cfg["general"]["setup_completed"] = True
            save_config(cfg)
            print(f"\033[32m✓ Configuration saved to {CONFIG_PATH}\033[0m")
            break
        elif choice == "p":
            curr = cfg["general"].get("power_mode", "hybrid")
            nxt = power_cycle[(power_cycle.index(curr) + 1) % len(power_cycle)] if curr in power_cycle else "hybrid"
            cfg["general"]["power_mode"] = nxt
            cfg["ai"]["enabled"] = (nxt != "offline" and nxt != "off")
            print(f"  Power Switch Mode → {format_power_badge(nxt)}")
        elif choice == "1":
            _prompt_and_set_key(cfg, "groq")
        elif choice == "2":
            _prompt_and_set_key(cfg, "gemini")
        elif choice == "3":
            _prompt_and_set_key(cfg, "openrouter")
        elif choice == "4":
            _prompt_and_set_key(cfg, "cerebras")
        elif choice == "5":
            _prompt_and_set_key(cfg, "grok")
        elif choice == "6":
            _prompt_and_set_key(cfg, "openai")
        elif choice == "7":
            current = cfg["local_llm"].get("enabled", False)
            cfg["local_llm"]["enabled"] = not current
            state_str = "\033[32mENABLED\033[0m" if not current else "\033[31mDISABLED\033[0m"
            print(f"  Local Ollama LLM is now {state_str}")
        elif choice == "8":
            current = cfg["general"].get("auto_approve_safe", False)
            cfg["general"]["auto_approve_safe"] = not current
            state_str = "\033[32mENABLED\033[0m" if not current else "\033[31mDISABLED\033[0m"
            print(f"  Auto-approve safe commands is now {state_str}")
        elif choice == "9":
            test_connections(cfg)
            try:
                input("\nPress Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                break
        elif choice == "r":
            ProviderHealthTracker.reset()
            print("  \033[32m✓ Reset all provider rate-limit cooldowns.\033[0m")
        elif choice == "c":
            print_commands_reference()
            try:
                input("Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                break
        elif choice == "g":
            print_key_guides()
            try:
                input("Press Enter to continue...")
            except (EOFError, KeyboardInterrupt):
                break
        elif choice == "w":
            save_config(cfg)
            run_setup_wizard()
            cfg = load_config()
