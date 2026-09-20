# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
