# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-10-28

### ⚡ Engine Power Switch, BYOK Key Management & Full Security Audit

#### Added
- **Engine Power Switch (`xsf power`)**:
  - Instant CLI and TUI mode switching across `hybrid` (Offline + Cloud AI fallback), `offline` (100% local heuristics, zero network/quota usage), `ai` (direct AI diagnosis), and `off` (engine paused).
  - Live status dashboard (`xsf power status`) and one-command circuit-breaker cooldown reset (`xsf power reset`).
- **Guided Post-Install Setup Wizard (`xsf setup`)**:
  - Interactive 3-step onboarding flow configuring Power Mode, personal API keys with live connectivity verification, and automatic shell profile hook installation (`~/.bashrc`, `~/.zshrc`, `config.fish`, PowerShell `$PROFILE`).
- **Robust Key & Account Manager (`xsf key`)**:
  - Direct CLI key management (`xsf key set <provider> <key> [--test]`, `xsf key remove <provider>`, `xsf key list`, `xsf key guide`).
  - Automatic key sanitization (strips accidental surrounding quotes, whitespace, and `Bearer ` prefixes) and provider-specific format validation.
  - **Multi-Account Backup Key Rotation**: Attach comma-separated keys per provider (`xsf key set groq "key1,key2"`) for automatic failover on rate limits.
- **Persistent Circuit-Breaker & Rate-Limit Guard (`ProviderHealthTracker`)**:
  - Tracks per-key health in `~/.shellfix/provider_health.json` (with `0600` permissions), placing rate-limited (`429`), quota-exhausted (`402`), or unauthorized (`401`/`403`) keys into timed cooldowns so terminal commands never lag on throttled endpoints.
  - Quiet failover mode suppresses noisy transient error walls during provider cascades.
- **Dedicated Step-by-Step Key & Power Switch Guides (`guides/`)**:
  - Added modular guides in `guides/` covering Groq LPU, Google Gemini, OpenRouter, Cerebras, xAI Grok, OpenAI, Local Ollama, and Power Switch / Multi-Key Rotation.
- **Architectural Roadmap (`FUTURE_FEATURES.md`)**:
  - Added 10 detailed module blueprints for upcoming capabilities.

#### Security & Audit Fixes
- **Chained/Piped Command Inspection in Safety Gate (`safety.py`)**:
  - Split commands across shell operators (`&&`, `||`, `;`, `|`, `&`, `\n`, `$(`, `` ` ``) so `_has_rm_danger()` catches recursive/root deletions anywhere in a command chain (e.g. `cd /tmp && rm -rf /`, `sudo -u root rm -rf /`, `env FOO=bar rm -rf /`, `timeout 5 rm -rf /`).
  - Added `find ... -delete` and `find ... -exec rm` to `DESTRUCTIVE_PATTERNS`.
- **Universal Terminal Escape Sanitization (`engine.py` & `safety.py`)**:
  - Stripped raw ANSI/OSC escape sequences from single-candidate outputs, dry-run previews, and destructive warning prompts.
- **Cross-Platform PowerShell Tokenization & `pwsh` Escaping (`command.py`)**:
  - Preserved Windows backslashes across all OS hosts when `shell` is `powershell`/`pwsh` and applied `$` subexpression escaping to `pwsh`.
- **Rule & Hook Hardening**:
  - Removed real CLI tools (`tac`, `hg`) from `COMMON_SHELL_TYPOS` and added uppercase command normalization (`GIT status` → `git status`).
  - Promoted `ChmodExecutableRule` priority ahead of generic `FilePermissionDeniedRule`, propagated `cmd.cwd` across all filesystem/Git rules, and fixed in-place file edit cache invalidation in `user_rules.py`.

---

## [1.1.2] - 2026-10-04

### 🛡️ Comprehensive Cyber Security Hardening & Offline Feature Expansion

#### Security Remediations
- **Subprocess & Path Traversal Isolation (`help_parser.py`)**:
  - Enforced strict rejection of binary names with path separators (`/` or `\`) or relative scripts (`./script`).
  - Guarded against Windows current-working-directory (CWD) binary hijacking; binaries are resolved strictly against system PATH.
  - Hardened flag cache permissions with `secure_config_permissions(CACHE_FILE)`.
- **Safety Gate Hardening (`safety.py`)**:
  - Unwrapped execution prefixes (`sudo`, `doas`, `env`, `command`, `nohup`) before inspecting tokens for destructive actions (`sudo rm -rf /` and `/bin/rm -rf /` can no longer bypass safety prompts).
  - Classified all recursive directory deletions (`rm -r`, `rm -R`, `--recursive`) as destructive, with or without force flags.
  - Fixed `git clean` flag ordering regex to catch both `-df`, `-fd`, and `-xdf`.
  - Added Windows `rd /s /q`, container mass wipes (`docker system prune -a`, `docker rm -f`), and disk wipes (`wipefs`, `shred`, `dd of=... if=...`).
- **PowerShell Hook & Quoting Security (`command.py` & `powershell.ps1`)**:
  - Escaped dollar signs (`$`) as `` `$ `` in PowerShell double-quoted tokens, preventing subexpression execution inside `Invoke-Expression`.
  - Handled multi-line string joining cleanly in PowerShell hooks and wrapped temporary stderr files in `try...finally` with `Remove-Item` cleanup.
- **Sensitive Credential Redaction (`ai/router.py`)**:
  - Implemented automated secret scrubbing (`redact_sensitive_data`) masking Bearer tokens, API keys, AWS credentials, and URI passwords before cloud dispatch or local caching.
- **Config & TOML Parser Hardening (`config.py`)**:
  - Stripped inline comments while preserving quoted strings in fallback TOML parser, preventing boolean misparsing.
  - Applied JSON string escaping to prevent TOML serialization injection in `save_config`.
  - Ensured `~/.shellfix` directory is secured with `0700` alongside configuration files.
- **CLI Flag Interception Fix (`cli.py`)**:
  - Resolved `-v`/`--version` interception bug that previously hijacked failed commands containing `-v` (e.g. `grep -v`, `curl -v`).
  - Validated and capped `--stderr-file` size to 1MB to prevent memory exhaustion.
- **Terminal UI Sanitization (`ui/selector.py`)**:
  - Stripped raw ANSI and OSC escape sequences from candidate strings and descriptions before terminal rendering.

#### New Offline Features
- **Fuzzy Path & Case-Insensitive Path Auto-Correction (`path_rules.py`)**:
  - Automatically heals misspelled or mis-cased file and directory paths in commands (`cat`, `python`, `ls`, `vim`, `git add`) by inspecting real filesystem entries via `difflib` and case-insensitive matching (<2ms execution).
- **Git Branch Fuzzy Auto-Resolver (`git_rules.py`)**:
  - Resolves mistyped Git branch names in `git checkout`, `git switch`, `git merge`, and `git rebase` against local Git references (`.git/refs/heads` and `.git/packed-refs`).

#### Humanized User Experience
- **Informative & Actionable Diagnostics**:
  - Transformed silent or generic fallback failures into clear, informative diagnostic hints (explaining offline mode, suggesting `xsf config` for free AI keys, or providing issue tracker links).
  - Added explicit cancellation notices when a command is declined.
  - Fixed false-positive abort in `check_already_resolved` for flagged commands (`rm -rf ...`).

---

## [1.1.1] - 2026-09-22

### 📚 Documentation Architecture & Engine Hardening

#### Added & Improved
- **Comprehensive User & Operator Manual (`HOWTOUSE.md`)**:
  - Full end-to-end documentation from git cloning to daily operations, interactive keys, and complete uninstallation.
  - Shell-by-shell profile configuration guides for PowerShell, Git Bash, Bash, Zsh, and Fish.
  - Dedicated configuration tutorials for Gemini, Groq, Cerebras, OpenRouter, and local Ollama instances.
- **Architectural Refocusing (`README.md`)**:
  - Re-anchored `README.md` around engineering principles, multi-tier engine mechanics, performance benchmarks, and security invariants.
  - Clear cross-references between `README.md`, `HOWTOUSE.md`, and `CONTRIBUTING.md`.
- **Natural Language & Cross-Shell Intent Engine**:
  - Added deterministic `CrossShellNaturalCommandsRule` offline plugin (<2ms execution) mapping English verbs (`delete`, `rename`, `move`, `copy`, `cls`, `type`, `md`, `rd`) to idiomatic target shell commands.
  - Enriched AI `SYSTEM_PROMPT` with explicit intent translation for conversational instructions (`show git log`, `find all pdfs`, etc.).
  - Calibrated AI confidence gating: single-file operations (e.g. `rm "file.png"`, `mv`) preserve high confidence (95%+) and are no longer falsely throttled to 40%.
- **Futile & Already-Resolved Command Prevention**:
  - Automatically recognizes when a command failed because the target is ALREADY in the desired state (e.g. removing a nonexistent/already deleted file, killing an already dead process).
  - Emits an instant notice (`[INFO] Target does not exist (already removed). No command needed.`) and avoids prompting the user to re-run redundant or failing commands.
  - Rejects any fix candidate that is functionally identical to the failed command.
- **AI Engine Hardening**:
  - Enhanced system prompt with shell dialect path rules and explicit missing-package installation suggestions.
  - Added multi-model automatic fallback chains to `CerebrasProvider` and `OpenRouterProvider` for maximum uptime.
- **Developer Attribution**:
  - Standardized the 3-line developer signature across all major markdown documents.

---

## [1.1.0] - 2026-09-22

### 🚀 Resilience & Vocabulary Supercharge

#### Added & Improved
- **Multi-Model Resilient AI Cascades**:
  - **Gemini**: Added automatic model fallback across `gemini-flash-latest`, `gemini-3.6-flash`, `gemini-flash-lite-latest` on 503 high-demand spikes and 404 retired models.
  - **Groq**: Configured `qwen/qwen3.8-27b` as high-throughput primary with seamless fallback across `llama3-8b-8192` and `llama-3.1-8b-instant`.
  - **xAI Grok & Cerebras**: Standardized `max_tokens: 512` and structured JSON response formats to prevent truncated JSON parsing errors.
- **Enhanced Offline Heuristics & Vocabulary**:
  - **Tool Aliases**: Direct translation for shorthand aliases (`k` → `kubectl`, `tf` → `terraform`, `g` → `git`).
  - **Compound Command Awareness**: Multi-depth subcommand matching for compound tools (e.g. `docker compose bulid` → `docker compose build`).
  - **Leading Flag-Skipping**: Intelligent subcommand detection past global flags (e.g. `git -C /path statsu` → `git -C /path status`).
  - **Flag Auto-Healing**: Corrects single-dash slips on standard long options (`python -version` → `python --version`, `docker -help` → `docker --help`).
  - **10+ Modern Toolchains Added**: `claude`, `aider`, `vllm`, `huggingface-cli`, `dbt`, `duckdb`, `k3d`, `act`, `cloudflared`, `alembic`, `drizzle-kit`.
- **Test Suite**: Expanded to 100 passing unit tests (100% pass rate).

---

## [1.0.0] - 2026-09-20

### 🎉 Initial Production Release

#### Added
- **3-Tier Resolution Pipeline**: Instant offline heuristics → Local LLM (opt-in) → Cloud AI cascade
- **30+ Deterministic Rule Plugins** covering:
  - Shell builtin typos (120+ entries: `cdd→cd`, `gti→git`, `pyhton→python`, etc.)
  - Git workflows (push upstream, commit -m, branch -d, detached HEAD, merge conflicts, did-you-mean)
  - Python (missing -m flag, venv activation, ModuleNotFoundError)
  - Package managers (npm missing `run`, yarn install→add, cargo shorthands, go run bare)
  - Docker (docker-compose v1→v2, missing -it)
  - Stderr-driven recovery (permission denied, pip externally-managed, port in use)
  - Network/SSH errors (host key verification, SSL certificates)
  - Environment issues (venv not found, env variables, Rust not installed)
- **Dynamic --help Flag Introspector**: Corrects flag typos by parsing `<cmd> --help` output with multi-format support (Argparse, Cobra, POSIX)
- **60+ Tool Vocabulary Database** with subcommand fuzzy matching
- **Multi-Provider Cloud AI Cascade**: Groq LPU → Cerebras → Gemini 3.6 Flash → OpenRouter → opt-in (Grok, OpenAI)
- **Local Ollama LLM Support** (opt-in Tier 2)
- **Universal Safety Gate**: Regex denylist for destructive operations with mandatory `yes` confirmation
- **Shell Hooks** for PowerShell, Git Bash, Bash, Zsh, and Fish
- **Interactive Config TUI** (`xsf config`) for managing API keys and providers
- **4 Trigger Aliases**: `xsf`, `xefix`, `xeeee`, `fuxx`
- **7-Day AI Response Cache** to save quota and latency
- **Zero External Dependencies**: Standard library only (Python 3.9+)
- **45+ Automated Tests** covering safety, rules, fuzzy matching, help parsing, engine orchestration, AI routing, and shell hooks

#### Security
- Hardened safety gate to catch `rm --force`, `git push +master`, `format C:`, and `--no-preserve-root`
- Config file permissions set to 0600 on POSIX systems
- Zsh and Fish hooks now properly delegate subcommands to prevent eval injection

---

## [Unreleased]

_Nothing yet._
