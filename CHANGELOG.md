# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
