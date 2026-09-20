# xe-shell-fix (`xsf`)

<p align="center">
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Python-Dark.svg" width="60" height="60" alt="Python" />
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Powershell-Dark.svg" width="60" height="60" alt="PowerShell" />
  <img src="https://raw.githubusercontent.com/tandpfun/skill-icons/main/icons/Bash-Dark.svg" width="60" height="60" alt="Bash" />
</p>

<h3 align="center">
  The High-Performance, Multi-Tier Shell Command Auto-Repair Assistant
</h3>

<p align="center">
  Diagnoses, auto-corrects, and executes mistyped or failing terminal commands in <b>PowerShell</b>, <b>Git Bash</b>, <b>Bash</b>, <b>Zsh</b>, and <b>Fish</b>.
</p>

---

## 📑 Table of Contents
- [Executive Overview](#-executive-overview)
- [How Much Gemini Supports (Rate Limits & Quota)](#-how-much-gemini-supports-rate-limits--quota)
- [The 3-Tier Multi-Provider Engine](#-the-3-tier-multi-provider-engine)
- [Installation Options](#-installation-options)
- [One-Line Shell Activation](#-one-line-shell-activation)
- [Usage & Aliases](#-usage--aliases)
- [Interactive Config Manager (`xsf config`)](#-interactive-config-manager-xsf-config)
- [Universal Safety Gate](#-universal-safety-gate)
- [Updating & Refreshing](#-updating--refreshing)
- [Uninstalling](#-uninstalling)
- [Troubleshooting FAQ](#-troubleshooting-faq)
- [Developer & Extensibility Guide](#-developer--extensibility-guide)
- [Directory Layout](#-directory-layout)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🌟 Executive Overview

`xe-shell-fix` (`xsf`) bridges the gap between static rule-based tools (like *thefuck*) and modern cloud AI assistants. It solves the three classic problems of terminal command repair:

1. **Latency**: Instant offline heuristics solve 90% of daily typos (`cdd`, `lss`, `gti`, `python venv`) in **<5ms** with zero network calls.
2. **Intelligence**: Complex tracebacks, syntax mismatches, and multi-token errors cascade to ultra-fast inference engines (**Groq LPU** at ~200ms, **Google Gemini 3.6 Flash**, and **Cerebras**).
3. **Safety**: A universal regex denylist sits between the engine and your shell. Destructive actions (`rm -rf`, `DROP TABLE`, `git push --force`) can **never** execute without explicit confirmation.

---

## 📊 How Much Gemini Supports (Rate Limits & Quota)

The **Gemini Free Tier** (`gemini-3.6-flash`) is one of the most generous developer free tiers available today:

| Metric | Free Tier Allowance | What It Means for You |
| :--- | :--- | :--- |
| **Requests Per Minute (RPM)** | **15 RPM** | You can repair up to 15 complex commands in 60 seconds without throttling. |
| **Requests Per Day (RPD)** | **1,500 RPD** | Up to 1,500 AI repairs per day for free (no credit card required). |
| **Tokens Per Minute (TPM)** | **1,000,000 TPM** | Easily fits long compiler error logs, Docker build failures, and Python tracebacks. |
| **Local Cache TTL** | **7-Day Persistent Cache** | Retyping the same broken command costs **0 quota** and responds in **0ms**! |

If you ever exceed Gemini rate limits, `xsf` automatically falls back to **Groq**, **Cerebras**, or **OpenRouter** without interrupting your workflow.

---

## ⚡ The 3-Tier Multi-Provider Engine

```
                          Failed Terminal Command
                                     │
                                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Tier 1a: Instant Heuristics (<5ms, Zero Network, 100% Private)   │
   │  - 60+ Tool Vocabulary (git, docker, kubectl, cargo, python...)  │
   │  - Shell Built-ins Typos (cdd -> cd, lss -> ls, claer -> clear)   │
   │  - Modular Rule Plugins (venv, -m flags, git push -u, docker v2) │
   └─────────────────────────────────┬────────────────────────────────┘
                                     │ (No confident rule match)
                                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Tier 1b: Dynamic Help Introspector (50–300ms, Cached)             │
   │  - Parses `<cmd> --help` on the fly for valid flags              │
   │  - Supports Argparse, Cobra/Go, and POSIX help formats           │
   │  - Fixes unknown flags (e.g., `git push --froce` -> `--force`)   │
   └─────────────────────────────────┬────────────────────────────────┘
                                     │ (No flag match & AI enabled)
                                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Tier 2: Local Private LLM (Opt-in Plugin)                        │
   │  - Local Ollama daemon (e.g., `qwen2.5-coder:1.5b`)              │
   │  - 100% Offline semantic reasoning                              │
   └─────────────────────────────────┬────────────────────────────────┘
                                     │ (Disabled or unavailable)
                                     ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │ Tier 3: Ultra-Fast Multi-Provider Cloud AI Cascade                │
   │  1. Groq LPU (~200ms ultra-fast LPU inference: qwen/qwen3.8-27b) │
   │  2. Cerebras (Wafer-scale high-throughput inference)             │
   │  3. Google Gemini Free Tier (gemini-3.6-flash, 1500 RPD free)    │
   │  4. OpenRouter Free Models (:free models)                        │
   │  5. Opt-in Keys (Grok / OpenAI / Anthropic / Custom endpoints)   │
   └─────────────────────────────────┬────────────────────────────────┘
                                     │
                                     ▼
   ════════════════════════════════════════════════════════════════════
   ║                   UNIVERSAL SAFETY GATE (safety.py)              ║
   ║         - Regex denylist protects filesystem, disks & git        ║
   ║         - Safe commands: [Enter] or [y]                          ║
   ║         - Destructive commands: STRICTLY requires typing 'yes'   ║
   ════════════════════════════════════════════════════════════════════
                                     │
                                     ▼
                      Shell Hook `eval` in Caller Session
                 (Changes `cd`, variables, and aliases persist!)
```

---

## 📦 Installation Options

### Option A: Standard Editable Install (From Source)
```bash
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix
pip install -e .
```

### Option B: Global Install via `pipx`
```bash
pipx install .
```

---

## 🚀 One-Line Shell Activation

Add the hook to your shell's startup file:

### PowerShell (`$PROFILE`)
```powershell
(& (Get-Command -CommandType Application xsf) init powershell | Out-String) | Invoke-Expression
```

### Git Bash / Bash (`~/.bashrc`)
```bash
eval "$(command xsf init bash)"
```

### Zsh (`~/.zshrc`)
```zsh
eval "$(command xsf init zsh)"
```

### Fish (`~/.config/fish/config.fish`)
```fish
command xsf init fish | source
```

---

## 💻 Usage & Aliases

Four trigger aliases are registered automatically:
- **`xefix`**: Standard fix alias.
- **`xeeee`**: Expressive trigger.
- **`fuxx`**: Modern alternative to *thefuck*.
- **`xsf`**: Official tool command.

### Examples in Action:

```bash
# Example 1: Shell builtin typo
$ cdd Downloads/
bash: cdd: command not found

$ xefix
  [OFFLINE] cd Downloads/
  └── Corrected shell typo 'cdd' to 'cd' (confidence: 100%)
Execute? [Enter/y/n]: <Enter>
# You are now in ~/Downloads!

# Example 2: Missing Python module flag
$ python venv .venv
$ xeeee
  [OFFLINE] python -m venv .venv
  └── Added missing '-m' flag for python module 'venv' (confidence: 100%)

# Example 3: Subcommand and tool typos
$ gti statsu
$ fuxx
  [OFFLINE] git status
  └── Corrected typo: 'gti' → 'git', 'statsu' → 'status' (confidence: 66%)

# Example 4: Complex AI error analysis (Groq LPU / Gemini)
$ python -c "imprt json; json.dump({})"
$ xefix
  [AI] python -c 'import json; json.dump({}, open("/dev/null", "w"))'
  └── [Groq] Fixed typo 'imprt' to 'import' and added required file argument. (confidence: 95%)
```

---

## ⚙️ Interactive Config Manager (`xsf config`)

Run the terminal UI to view status, attach keys, or test provider connectivity:

```bash
xsf config
```

```
=== xe-shell-fix (xsf) Current Configuration ===
  AI Enabled              : Yes
  Groq API Key (Fast LPU) : gsk_...tQU9 [Configured] (qwen/qwen3.8-27b)
  Cerebras Key (Wafer)    : csk-...xk6v [Configured] (qwen-3.8-27b)
  Gemini API Key (Free)   : AQ.A...vRGQ [Configured] (gemini-3.6-flash)
  OpenRouter Key (Free)   : [Not Configured]
  Grok Key (xAI Opt-In)   : [Not Configured]
  OpenAI Key (Opt-In)     : [Not Configured]
  Local Ollama LLM        : Disabled (Default) (qwen2.5-coder:1.5b)
  Auto-Approve Safe       : No (Prompt user)
  Help Introspection      : Yes
  Active Aliases          : xsf, xefix, xeeee, fuxx
================================================
```

Non-interactive inspection:
```bash
xsf config --list
```

---

## 🛡️ Universal Safety Gate

Safety is treated as an architectural invariant. All candidates from all tiers must pass through `xsf.core.safety`:

- **Destructive Patterns Caught**:
  - Filesystem: `rm -rf`, `rmdir /s`, `del /s /f /q`, `Remove-Item -Recurse -Force`
  - Disks: `mkfs`, `dd if=`, `fdisk`, `diskpart`, `> /dev/sd*`
  - Git: `git push --force`, `git reset --hard`, `git clean -fd`
  - Databases: `DROP DATABASE`, `DROP TABLE`, `TRUNCATE`
- **Enforcement**:
  - Safe commands: Single press of `Enter` or `y`.
  - Destructive commands: **Requires typing the full word `yes`**. Enter or `y` alone will refuse execution.

---

## 🛠️ Developer & Extensibility Guide

### Adding a New Offline Rule Plugin
Rules live in `xsf/offline/rules/`. Subclass `Rule`:

```python
from xsf.core.command import Command
from xsf.offline.rules.base import Rule

class CustomRule(Rule):
    name = "custom_rule"
    priority = 20

    def match(self, cmd: Command) -> bool:
        return cmd.tokens and cmd.tokens[0] == "mytool"

    def get_new_command(self, cmd: Command):
        return "mytool --correct-syntax", 0.95, "Fixed mytool syntax"
```

Register it in `xsf/offline/rules/__init__.py`.

### Running Tests
```bash
python -m pytest tests/ -v
```

---

## 📁 Directory Layout

```
xe-shell-fix/
├── .gitignore                         # Standard Python ignores
├── LICENSE                            # MIT License
├── README.md                          # Full engineering documentation
├── CONTRIBUTING.md                    # Contributor guide & rule plugin howto
├── CHANGELOG.md                       # Version history
├── pyproject.toml                     # PEP 621 packaging & console scripts
├── xsf/
│   ├── __init__.py                    # Package metadata & version
│   ├── cli.py                         # CLI entrypoint (xsf, xefix, xeeee, fuxx)
│   ├── config.py                      # Config parser (~/.shellfix/config.toml)
│   ├── core/
│   │   ├── command.py                 # Command data model & shell quoting
│   │   ├── engine.py                  # Master 3-tier cascade orchestrator
│   │   └── safety.py                  # Universal safety gate & denylist
│   ├── offline/
│   │   ├── fuzzy.py                   # Levenshtein typo matcher
│   │   ├── help_parser.py             # Multi-format --help flag introspector
│   │   ├── vocabulary.json            # 80+ CLI tools database
│   │   └── rules/                     # Modular rule plugins
│   │       ├── base.py                # Rule ABC
│   │       ├── shell_rules.py         # 120+ shell typos & permission fixes
│   │       ├── git_rules.py           # 9 git-specific rules
│   │       ├── python_rules.py        # Python/venv rules
│   │       ├── package_rules.py       # npm/yarn/cargo/go rules
│   │       ├── docker_rules.py        # Docker rules
│   │       ├── stderr_rules.py        # Stderr-driven recovery (8 rules)
│   │       ├── env_rules.py           # Environment error recovery
│   │       └── ssh_net_rules.py       # SSH & network error fixes
│   ├── ai/
│   │   ├── cache.py                   # SHA256 query cache (7-day TTL)
│   │   ├── router.py                  # Multi-provider fallback controller
│   │   └── providers/
│   │       ├── gemini.py              # Google Gemini 3.6 Flash (Free)
│   │       ├── groq.py                # Groq LPU ultra-fast inference
│   │       ├── cerebras.py            # Cerebras wafer-scale provider
│   │       ├── openrouter.py          # OpenRouter free models
│   │       ├── grok.py                # xAI Grok provider (opt-in)
│   │       ├── openai_compat.py       # OpenAI / Custom endpoints (opt-in)
│   │       └── ollama.py              # Local private LLM provider (opt-in)
│   ├── hooks/
│   │   ├── powershell.ps1             # PowerShell 5.1 & pwsh 7+ hook
│   │   ├── bash.sh                    # Bash & Git Bash hook
│   │   ├── zsh.zsh                    # Zsh hook (with subcommand delegation)
│   │   └── fish.fish                  # Fish hook (with subcommand delegation)
│   └── ui/
│       ├── config_tui.py              # Interactive Terminal config manager
│       └── selector.py                # Color diff renderer
├── tests/                             # Full automated test suite (94 tests)
└── legacy/                            # Archived early prototypes
```

---

## 🔄 Updating & Refreshing

When a new version of `xsf` is released, updating is a one-liner:

```bash
# Pull the latest code
git pull origin main

# Re-install (editable install auto-refreshes, but run this to be safe)
pip install -e .
```

**Shell hooks do not need to be updated** — they call the `xsf` binary which is already updated. Just restart your terminal session or re-source your profile:

```bash
# Git Bash / Bash
source ~/.bashrc

# Zsh
source ~/.zshrc

# Fish
source ~/.config/fish/config.fish

# PowerShell
. $PROFILE
```

**Refresh the AI response cache** if you change your AI provider or model:

```bash
xsf config
# Choose option: "Clear AI Cache"
```

**Refresh the help introspection cache** if a tool updates its flags:

```bash
# The cache is stored at ~/.shellfix/help_cache.json — just delete it:
rm ~/.shellfix/help_cache.json
```

---

## 🗑️ Uninstalling

### Step 1: Remove the package

```bash
pip uninstall xe-shell-fix
```

### Step 2: Remove shell hooks

**Git Bash / Bash** — edit `~/.bashrc` and remove the line:
```bash
eval "$(command xsf init bash)"
```

**Zsh** — edit `~/.zshrc` and remove the line:
```bash
eval "$(command xsf init zsh)"
```

**Fish** — edit `~/.config/fish/config.fish` and remove:
```fish
command xsf init fish | source
```

**PowerShell** — edit your `$PROFILE` and remove:
```powershell
(& (Get-Command -CommandType Application xsf) init powershell | Out-String) | Invoke-Expression
```

### Step 3: Remove config & cache (optional)

```bash
rm -rf ~/.shellfix/
```

---

## ❓ Troubleshooting FAQ

### `xsf: command not found` after install

Make sure the Python Scripts directory is in your PATH:

```bash
# Find where xsf was installed
pip show xe-shell-fix | grep Location

# Add Scripts to PATH (Git Bash / Bash)
export PATH="$PATH:/path/to/Python/Scripts"

# Or use: python -m xsf.cli as a fallback
```

### `xsf: no previous command found`

This means the history lookup found no prior command. Make sure:
1. A command actually **ran and failed** before calling `xefix`
2. You're not in a fresh shell session with no history
3. Your shell's history is enabled (`set -o history` in bash)

### AI fallback always says "No AI providers configured"

Run `xsf config` to check and attach your API keys. They can also be set as environment variables:

```bash
export GEMINI_API_KEY="your-key"
export GROQ_API_KEY="your-key"
```

### PowerShell hook fails with `System.Object[]` error

Make sure your `$PROFILE` uses the exact command:
```powershell
(& (Get-Command -CommandType Application xsf) init powershell | Out-String) | Invoke-Expression
```
The `| Out-String` is critical — without it, PowerShell returns an array object.

### `cdd Downloads/` is fixed but changes don't persist

This is expected if you run `xsf "cdd Downloads/"` directly. The hook must be active in your shell. Make sure:
1. The `eval "$(command xsf init bash)"` line is at the **bottom** of `~/.bashrc`
2. You've sourced `~/.bashrc` after adding it

### Gemini API key shows as invalid

Ensure your key starts with the correct prefix and has no trailing spaces. Test connectivity:
```bash
xsf config
# Choose: "Test All Provider Connections"
```

---

## 🤝 Contributing

We welcome rule plugins, AI provider integrations, and documentation improvements!
See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide.

Quick rule plugin example:
```python
from xsf.offline.rules.base import Rule
from xsf.core.command import Command

class MyRule(Rule):
    name = "my_rule"
    priority = 20

    def match(self, cmd: Command) -> bool:
        return cmd.tokens and cmd.tokens[0] == "mytool"

    def get_new_command(self, cmd: Command):
        return "mytool --correct-syntax", 0.95, "Fixed mytool syntax"
```

---

## 📄 License

MIT License. Copyright (c) 2026 xe-shell-fix developers.

