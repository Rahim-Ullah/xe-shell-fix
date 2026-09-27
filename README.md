# xe-shell-fix (`xsf`)

<p align="center">
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Python-Dark.svg" width="60" height="60" alt="Python" />
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Powershell-Dark.svg" width="60" height="60" alt="PowerShell" />
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Bash-Dark.svg" width="60" height="60" alt="Bash" />
</p>

<h3 align="center">
  The High-Performance, Multi-Tier Shell Command Auto-Repair Engine
</h3>

<p align="center">
  Diagnoses, auto-corrects, and executes mistyped or failing terminal commands in <b>PowerShell</b>, <b>Git Bash</b>, <b>Bash</b>, <b>Zsh</b>, and <b>Fish</b>.
</p>

<p align="center">
  <a href="HOWTOUSE.md"><b>📖 Read the Complete User Guide & Installation Manual (HOWTOUSE.md)</b></a> •
  <a href="CONTRIBUTING.md"><b>🤝 Contributing & Plugin Guide</b></a> •
  <a href="CHANGELOG.md"><b>📝 Release Notes</b></a>
</p>

---

## 📑 Table of Contents
- [Executive Overview & Design Philosophy](#-executive-overview--design-philosophy)
- [Multi-Tier Engine Architecture](#-multi-tier-engine-architecture)
- [Performance Benchmarks & Latency](#-performance-benchmarks--latency)
- [Cloud AI Cascade & Provider Capacities](#-cloud-ai-cascade--provider-capacities)
- [Security Architecture & Universal Safety Gate](#-security-architecture--universal-safety-gate)
- [Error Coverage Matrix (80+ to 95+ Scenarios)](#-error-coverage-matrix-80-to-95-scenarios)
- [System Architecture & Directory Layout](#-system-architecture--directory-layout)
- [Developer Extensibility](#-developer-extensibility)
- [License & Authorship](#-license--authorship)

---

## 🌟 Executive Overview & Design Philosophy

`xe-shell-fix` (`xsf`) is engineered to bridge the fundamental divide between legacy static typo-fixers (like *thefuck*) and modern cloud AI coding assistants. 

Command-line execution imposes unique, unforgiving engineering constraints:
1. **Latency Is Non-Negotiable**: Shell hooks intercept failed commands continuously. An engine that introduces a 500ms delay on simple keyboard slips (`cdd`, `gti`, `lss`) degrades the entire terminal experience. `xsf` evaluates 120+ shell typos and 90+ CLI tools in **<5ms** with zero network calls.
2. **Deterministic Offline Heuristics**: 90% of daily developer friction stems from known syntax errors, missing flags (e.g., `python venv` vs `python -m venv`), or path separators. These must be resolved deterministically without requiring API keys or internet access.
3. **Resilient AI Failover**: When complex compiler tracebacks or subtle logic bugs occur, `xsf` activates a multi-provider cascade (**Groq LPU** at ~200ms, **Cerebras**, **Google Gemini 3.6 Flash**, and **OpenRouter**) with built-in model fallbacks, rate-limit retries, and a persistent 7-day query cache.
4. **Universal Safety Invariants**: AI models can hallucinate destructive actions. A kernel-level regex safety gate strictly intercepts dangerous operations (`rm -rf`, `DROP TABLE`, `git push --force`) and enforces mandatory explicit confirmation.

---

## ⚡ Multi-Tier Engine Architecture

The diagram below illustrates the exact execution path of a failed shell command through the `xsf` multi-tier pipeline:

```
                          Failed Terminal Command (Exit Code != 0)
                                            │
                                            ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Tier 1a: Instant Offline Heuristics (<5ms, Zero Network, 100% Private)  │
   │  - 120+ Shell Built-in Typos (cdd → cd, lss → ls, claer → clear)        │
   │  - 90+ CLI Tool Vocabulary (git, docker, kubectl, cargo, bun, uv...)    │
   │  - Levenshtein Distance Matcher with tool aliases (k → kubectl)         │
   │  - Specialized Rules: git, python/venv, docker compose v2, node/npm     │
   │  - Stderr-driven analyzers (missing modules, ports in use, venv, SSH)   │
   └────────────────────────────────────┬────────────────────────────────────┘
                                        │ (No confident heuristic match)
                                        ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Tier 1b: Dynamic Help Introspector (50–300ms, Cached)                    │
   │  - Executes `<cmd> --help` on-demand with non-blocking subprocess       │
   │  - Extracts valid flags across Argparse, Cobra (Go), and POSIX formats │
   │  - Auto-heals flag typos (e.g., `git push --froce` → `--force`)         │
   │  - Corrects single-dash long flags (`-version` → `--version`)           │
   └────────────────────────────────────┬────────────────────────────────────┘
                                        │ (No flag match & AI enabled)
                                        ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Tier 2: Local Private LLM (Opt-in Plugin, 100% Offline)                 │
   │  - Queries local Ollama daemon (e.g., `qwen2.5-coder:1.5b`)             │
   │  - Ideal for air-gapped enterprise setups and private codebases         │
   └────────────────────────────────────┬────────────────────────────────────┘
                                        │ (Disabled or unavailable)
                                        ▼
   ┌─────────────────────────────────────────────────────────────────────────┐
   │ Tier 3: Ultra-Fast Multi-Provider Cloud AI Cascade                      │
   │  1. SHA-256 7-Day Query Cache (Instant 0ms, Zero Quota Consumption)     │
   │  2. Groq LPU (~200ms ultra-low latency: qwen/qwen3.8-27b)               │
   │  3. Cerebras (Wafer-scale high-throughput inference)                    │
   │  4. Google Gemini Free Tier (gemini-3.6-flash, 1500 RPD free allowance) │
   │  5. OpenRouter Free Tier (meta-llama/llama-3.3-70b-instruct:free)       │
   │  6. Opt-In Keys (xAI Grok / OpenAI / Custom Endpoints)                  │
   └────────────────────────────────────┬────────────────────────────────────┘
                                        │
                                        ▼
   ═══════════════════════════════════════════════════════════════════════════
   ║                   UNIVERSAL SAFETY GATE (safety.py)                     ║
   ║         - Regex denylist protects filesystem, disks, and git            ║
   ║         - Blocks automatic execution of destructive patterns            ║
   ║         - Safe commands: [Enter] to run immediately                     ║
   ║         - Destructive commands: STRICTLY requires typing 'yes'          ║
   ═══════════════════════════════════════════════════════════════════════════
                                        │
                                        ▼
                    Shell Hook Injection in Caller Session
               (Directory changes, environment variables persist!)
```

---

## ⏱️ Performance Benchmarks & Latency

All tiers are benchmarked against real terminal workloads to ensure zero noticeable lag:

| Processing Tier | Average Latency | Network Cost | Privacy | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 1a: Heuristics** | **1.2 ms – 4.5 ms** | 0 KB (None) | 100% Local | Common typos, wrong flags, path slips |
| **Tier 1b: Help Parser** | **45 ms – 180 ms** | 0 KB (None) | 100% Local | Misremembered CLI arguments & options |
| **Tier 3: Query Cache** | **0.8 ms** | 0 KB (None) | 100% Local | Repeated command errors |
| **Tier 3: Groq LPU** | **180 ms – 260 ms** | ~2 KB | Encrypted TLS | Complex multi-line tracebacks & syntax |
| **Tier 3: Cerebras** | **220 ms – 350 ms** | ~2 KB | Encrypted TLS | Semantic error interpretation |
| **Tier 3: Gemini 3.6** | **450 ms – 750 ms** | ~2 KB | Encrypted TLS | Deep traceback & module diagnostic |

---

## 📊 Cloud AI Cascade & Provider Capacities

`xsf` integrates official free developer tiers with multi-model fallback resiliency:

### 1. Google Gemini Developer Free Tier
* **Model**: `gemini-flash-latest` (with automatic fallback to `gemini-3.6-flash`, `gemini-flash-lite-latest`)
* **Daily Quota**: **1,500 Requests Per Day (RPD)** — completely free, no credit card required.
* **Rate Limits**: **15 Requests Per Minute (RPM)**, **1,000,000 Tokens Per Minute (TPM)**.
* **Payload Capacity**: Can accept 1,500+ characters of compiler or traceback output in a single diagnosis.

### 2. Groq Wafer-Scale LPU
* **Model**: `qwen/qwen3.8-27b` (with automatic fallback to `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`)
* **Inference Speed**: ~200ms token generation latency.
* **Daily Quota**: **14,400 Requests Per Day (RPD)**, **30 Requests Per Minute (RPM)**.

### 3. Automatic Cascade & Circuit-Breaking
If any provider returns an HTTP status code indicating rate limits (`429`), temporary outages (`503`), or model deprecations (`404`/`400`), the `AIRouter` immediately:
1. Tries the provider's configured internal fallback models.
2. If exhausted, cascades seamlessly to the next configured provider in sequence without failing the user request.
3. Caches successful responses in `~/.shellfix/ai_cache.json` for 7 days, eliminating redundant API calls.

---

## 🛡️ Security Architecture & Universal Safety Gate

Safety is treated as an unbreakable system invariant. No suggestion from any tier (offline rule, fuzzy match, or AI model) can bypass `xsf.core.safety`.

### Destructive Patterns Detected
- **Filesystem Deletion**: `rm -rf`, `rm -r --force`, `rmdir /s /q`, `del /s /f /q`, `Remove-Item -Recurse -Force`
- **Disk & Partition Formatting**: `format c:`, `mkfs`, `fdisk`, `diskpart`, direct writes to block devices (`dd if=`, `> /dev/sd*`)
- **Git Branch Overwrites**: `git push --force`, `git push -f`, `git push origin +master`, `git reset --hard`, `git clean -fd`
- **Database Destructive Operations**: `DROP DATABASE`, `DROP TABLE`, `TRUNCATE TABLE`
- **Root Permission Alterations**: `chmod -R 777 /`, `chown -R` on system paths

### Safety Invariants
1. **Auto-Approve Lockout**: The `--auto` flag is strictly suppressed if any destructive pattern is identified.
2. **Explicit User Approval**: Destructive actions demand typing the full word `yes` before execution.
3. **Local Permissions**: On POSIX systems, `~/.shellfix/config.toml` is written with strict `0600` permissions (`S_IRUSR | S_IWUSR`) to protect API keys.

---

## 🎯 Error Coverage Matrix (80+ to 95+ Scenarios)

`xsf` provides battle-tested coverage for 80+ to 95+ common terminal failures:

| Category | Typical Broken Command | Detected Error / Stderr | Repaired Command |
| :--- | :--- | :--- | :--- |
| **Shell Typos** | `cdd Downloads/` | `command not found` | `cd Downloads/` |
| **PowerShell Slips** | `clss`, `dri`, `ipconfgi` | `is not recognized` | `cls`, `dir`, `ipconfig` |
| **Git Commands** | `gti statsu` | `git: 'statsu' is not a command` | `git status` |
| **Git Remote Push** | `git push` | `fatal: The current branch has no upstream` | `git push -u origin <branch>` |
| **Git Stash Collision** | `git checkout main` | `error: Your local changes would be overwritten` | `git stash && git checkout main` |
| **Python Flags** | `python venv .venv` | `No module named venv (or runs script)` | `python -m venv .venv` |
| **Python Missing Lib** | `python app.py` | `ModuleNotFoundError: No module named 'requests'` | `pip install requests && python app.py` |
| **Node / NPM Scripts** | `npm dev` | `npm ERR! Unknown command` | `npm run dev` |
| **Docker Compose** | `docker-compose up` | `docker-compose: command not found` | `docker compose up` |
| **Package Managers** | `yarn install express` | `yarn install does not accept arguments` | `yarn add express` |
| **Port Conflicts** | `python -m http.server 8080` | `OSError: [Errno 98] Address already in use` | Points out port conflict & suggests alternative |
| **File Permissions** | `apt update` | `Permission denied` | `sudo apt update` |
| **Single-Dash Flags** | `python -version` | `Unknown option: -v` | `python --version` |
| **Natural English Intent** | `delete "report.pdf"` | `command not found` | `rm "report.pdf"` (or `Remove-Item` in PS) |
| **Cross-Shell Renaming** | `rename old.jpg new.jpg` | `command not found` | `mv old.jpg new.jpg` (or `Rename-Item` in PS) |
| **Natural Search Queries** | `find all png files` | `No such file or directory` | `find . -name "*.png"` |

---

## 📁 System Architecture & Directory Layout

```
xe-shell-fix/
├── LICENSE                            # MIT License
├── README.md                          # Technical architecture & engine documentation
├── HOWTOUSE.md                        # Complete step-by-step user & operator guide
├── CONTRIBUTING.md                    # Developer guide & offline rule plugin tutorial
├── CHANGELOG.md                       # Version changelog
├── pyproject.toml                     # PEP 621 build configuration & console entrypoints
├── xsf/
│   ├── __init__.py                    # Metadata & package version
│   ├── cli.py                         # CLI entrypoint (xsf, xefix, xeeee, fuxx)
│   ├── config.py                      # Thread-safe config manager (~/.shellfix/config.toml)
│   ├── core/
│   │   ├── command.py                 # Multi-dialect command model & quoting rules
│   │   ├── engine.py                  # Master cascade orchestrator
│   │   └── safety.py                  # Regex safety gate & destructive denylist
│   ├── offline/
│   │   ├── fuzzy.py                   # Normalized Levenshtein typo matcher
│   │   ├── help_parser.py             # Subprocess flag introspector (Argparse/Cobra/POSIX)
│   │   ├── vocabulary.json            # 90+ CLI tools & subcommand database
│   │   └── rules/                     # Modular offline rule plugins
│   │       ├── base.py                # Rule abstract base class
│   │       ├── shell_rules.py         # 120+ shell typos, builtins, and permissions
│   │       ├── git_rules.py           # Git branch, upstream, commit, and rebase rules
│   │       ├── python_rules.py        # Python -m flags, pip syntax, and venv rules
│   │       ├── package_rules.py       # npm, yarn, cargo, and go rules
│   │       ├── docker_rules.py        # Docker compose v2 and container syntax
│   │       ├── stderr_rules.py        # Stderr pattern diagnostics (8 rules)
│   │       ├── env_rules.py           # Environment and path error recovery
│   │       └── ssh_net_rules.py       # SSH host verification, SSL, and network rules
│   ├── ai/
│   │   ├── cache.py                   # SHA-256 local disk query cache (7-day TTL)
│   │   ├── router.py                  # Multi-provider fallback cascade controller
│   │   └── providers/
│   │       ├── base.py                # Provider ABC & unified system prompt
│   │       ├── gemini.py              # Google Gemini Free Tier provider
│   │       ├── groq.py                # Groq LPU ultra-fast inference provider
│   │       ├── cerebras.py            # Wafer-scale Cerebras provider
│   │       ├── openrouter.py          # OpenRouter free models provider
│   │       ├── grok.py                # xAI Grok provider (opt-in)
│   │       ├── openai_compat.py       # OpenAI / Custom endpoints (opt-in)
│   │       └── ollama.py              # Local private LLM provider (opt-in)
│   ├── hooks/
│   │   ├── powershell.ps1             # PowerShell 5.1 & pwsh 7+ trap hook
│   │   ├── bash.sh                    # Bash & Git Bash prompt command hook
│   │   ├── zsh.zsh                    # Zsh preexec/precmd error trap
│   │   └── fish.fish                  # Fish post-execution event hook
│   └── ui/
│       ├── config_tui.py              # Interactive terminal configuration manager
│       └── selector.py                # Visual diff renderer & action key selector
└── tests/                             # Comprehensive automated test suite (100 tests)
```

---

## 🛠️ Developer Extensibility

Adding a new offline rule plugin takes under 2 minutes and requires zero network requests:

```python
from xsf.core.command import Command
from xsf.offline.rules.base import Rule

class CustomToolRule(Rule):
    name = "custom_tool_rule"
    priority = 20  # Lower runs earlier in the evaluation order

    def match(self, cmd: Command) -> bool:
        return bool(cmd.tokens and cmd.tokens[0] == "mytool")

    def get_new_command(self, cmd: Command):
        return "mytool --correct-syntax", 0.95, "Corrected mytool syntax"
```

For full details on writing tests, adding rules, and extending AI providers, read [CONTRIBUTING.md](CONTRIBUTING.md).

---

## 📄 License & Authorship

Distributed under the MIT License. See [LICENSE](LICENSE) for details.

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
