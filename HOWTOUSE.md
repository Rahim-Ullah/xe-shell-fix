# xe-shell-fix (`xsf`) — Complete User & Operator Guide

<p align="center">
  <b>The Complete Handbook: From First Clone to Power User Workflows</b>
</p>

---

## 📑 Table of Contents
1. [Prerequisites & System Compatibility](#1-prerequisites--system-compatibility)
2. [Best Practices for Workspace & Cloning](#2-best-practices-for-workspace--cloning)
3. [Installation Walkthrough](#3-installation-walkthrough)
4. [Shell Hook Activation (Step-by-Step)](#4-shell-hook-activation-step-by-step)
5. [Daily Usage & Interaction Modes](#5-daily-usage--interaction-modes)
6. [Configuring AI Engines & API Keys](#6-configuring-ai-engines--api-keys)
7. [Running Local Private LLMs (Ollama)](#7-running-local-private-llms-ollama)
8. [Safety Gate & Destructive Command Guardrails](#8-safety-gate--destructive-command-guardrails)
9. [Updating, Syncing & Refreshing](#9-updating-syncing--refreshing)
10. [Clean Uninstallation](#10-clean-uninstallation)
11. [Troubleshooting & Common Pitfalls](#11-troubleshooting--common-pitfalls)

---

## 1. Prerequisites & System Compatibility

Before installing `xsf`, ensure your environment meets these baseline requirements:

| Requirement | Supported Versions | Notes |
| :--- | :--- | :--- |
| **Python** | `3.9` through `3.13+` | Python must be registered in your system `PATH`. |
| **Operating Systems** | Windows 10/11, Linux (Ubuntu, Debian, Fedora, Arch), macOS | Native Windows support without requiring WSL. |
| **Supported Shells** | PowerShell 5.1 / 7+ (`pwsh`), Git Bash (MINGW64), Bash, Zsh, Fish | `cmd.exe` is legacy and not supported. |
| **Network** | Offline or Online | Full offline heuristic engine works with **zero internet**. Cloud AI is optional. |

To verify your Python version:
```bash
python --version
# or on POSIX:
python3 --version
```

---

## 2. Best Practices for Workspace & Cloning

Keep your CLI tools organized in a dedicated directory (e.g., `~/tools/` or `C:\Users\<user>\tools\`).

```bash
# Recommended directory structure:
# Windows: C:\Users\<Username>\tools\xe-shell-fix
# POSIX:   ~/tools/xe-shell-fix

# 1. Navigate to your preferred tools folder
cd ~
mkdir -p tools && cd tools

# 2. Clone the repository
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix
```

---

## 3. Installation Walkthrough (Ubuntu / Linux, macOS & Windows)

### 🐧 Method A: Ubuntu / Debian / Linux (Recommended — Isolated Virtual Environment)
Modern Ubuntu (23.04 / 24.04+) enforces PEP 668 externally-managed environments. Installing into a dedicated `.venv` and running `xsf setup` takes 30 seconds:

```bash
# 1. Clone the repository
mkdir -p ~/tools && cd ~/tools
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix

# 2. Create a virtual environment & install xsf
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Launch the interactive Setup Wizard (attaches your keys & installs the Bash/Zsh hook!)
xsf setup
```

> [!TIP]
> Because `xsf init` pins the exact `.venv` Python interpreter inside your `~/.bashrc` / `~/.zshrc` hook (`_XSF_INIT_PYTHON`), **`xsf` will continue to work in every new terminal window even when `.venv` is not activated!**

### 🪟 Method B: Windows / Editable Install
```powershell
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix
pip install -e .
xsf setup
```

### Verifying the Installation
```bash
xsf --version
# Output: xsf 1.2.0

xsf power status
```

---

## 4. Shell Hook Activation (Step-by-Step)

`xsf` integrates directly into your shell's error-trapping mechanism. When a command fails with a non-zero exit code, `xsf` automatically intercepts the previous line and presents the corrected command.

### 🔷 PowerShell (Windows 10 / 11 / Server)
1. Open PowerShell and locate your profile:
   ```powershell
   $PROFILE
   ```
2. Open the profile in Notepad (creates it if missing):
   ```powershell
   if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
   notepad $PROFILE
   ```
3. Paste the following hook at the **very bottom** of your profile:
   ```powershell
   try { (& (Get-Command -CommandType Application xsf -ErrorAction Stop | Select-Object -First 1) init powershell | Out-String) | Invoke-Expression } catch { (& python -m xsf.cli init powershell | Out-String) | Invoke-Expression }
   ```
4. Save, close Notepad, and reload your profile:
   ```powershell
   . $PROFILE
   ```
   *(If you see an ExecutionPolicy error, run: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`)*

---

### 🟩 Git Bash (Windows MINGW64)
1. Open Git Bash and edit `~/.bashrc`:
   ```bash
   notepad ~/.bashrc
   # or: nano ~/.bashrc
   ```
2. Add this line at the bottom:
   ```bash
   eval "$(python -m xsf.cli init bash 2>/dev/null || command xsf init bash)"
   ```
3. Save and reload:
   ```bash
   source ~/.bashrc
   hash -r
   ```

---

### 🐧 Linux Bash
1. Open `~/.bashrc`:
   ```bash
   echo 'eval "$(command xsf init bash)"' >> ~/.bashrc
   source ~/.bashrc
   ```

---

### 🍏 macOS / Linux Zsh
1. Open `~/.zshrc`:
   ```zsh
   echo 'eval "$(command xsf init zsh)"' >> ~/.zshrc
   source ~/.zshrc
   ```

---

### 🐟 Fish Shell
1. Edit `~/.config/fish/config.fish`:
   ```fish
   xsf init fish | source
   ```

---

### 🧪 Immediate Verification Test
Type any deliberate typo in your terminal and press Enter:
```bash
cdd Downloads/
```
Output:
```text
xsf: cd Downloads/ [Enter to run, Ctrl+C to cancel]
```
Press **Enter** — the shell fixes your typo and changes directory!

---

## 5. Daily Usage & Interaction Modes

### A. Automatic Error Interception (Zero Overhead)
Whenever a command fails, `xsf` immediately evaluates:
1. **Tier 1a Heuristics (<5ms)**: Matches 120+ known shell typos and 90+ CLI tool rules.
2. **Tier 1b Help Introspector (50-300ms)**: Reads `--help` dynamically to fix mistyped flags (`git push --froce` -> `--force`).
3. **Tier 2/3 AI Fallback (200-800ms)**: For complex tracebacks or unknown errors.

### B. Interactive Action Keys
When a suggestion is displayed, you have 4 interactive options:
* **`[Enter]`** — Accept and execute the repaired command immediately.
* **`[c]`** — Copy / push the command directly onto your prompt line so you can edit it before running.
* **`[e]`** — Display a concise explanation of what went wrong and why the fix works.
* **`[n]` or `Ctrl+C`** — Cancel and discard the suggestion.

### C. Manual CLI Invocations
You can also run `xsf` directly on any arbitrary command string:
```bash
# Standard diagnosis and repair
xsf "git brnch -a"

# Force Cloud AI reasoning (skips offline rules)
xsf --ai "python -m venv myenv && source myenv/bin/activate"

# Pure offline mode (zero network calls, 100% private)
xsf --offline "doker ps -a"

# Auto-run mode (runs immediately without confirmation if confidence >= 0.85)
xsf --auto "gti status"

# Dry-run mode (prints the suggestion, exits with code 1 without running)
xsf --dry-run "kuebctl get pods"

# Bypass persistent 7-day AI cache
xsf --no-cache "broken command"
```

### D. Built-in Shell Trigger Aliases
`xsf` registers 4 convenient trigger aliases in your shell profile:
* `xsf` — Primary command and subcommand runner (`xsf`, `xsf setup`, `xsf power`, `xsf key`, `xsf config`).
* `xefix` — Quick alias to repair the previous failed command.
* `xeeee` — Fast single-hand ergonomic alias.
* `fuxx` — Classic expressive alias.

### E. 🌟 Superpower: Natural Language & Cross-Shell Commands ("Speak Human")

You don't always have to remember exact shell syntax or flags. If you type what you want to do in intuitive English or use commands from another operating system, `xsf` automatically understands your intent and translates it into the idiomatic command for your current shell!

#### Real-World Examples:

1. **Natural Language File Rename**:
   ```bash
   $ rename ParalleilismInTech.jpg ParallelismConcept
   bash: rename: command not found

   $ xsf
     [AI] mv ParalleilismInTech.jpg ParallelismConcept
     └── [Groq] Corrected 'rename' to 'mv' and fixed typo in source filename. (confidence: 95%)

   Execute? [Enter/y/n]: y
   ```

2. **Cross-Shell File Deletion (Windows `delete` in Git Bash/Linux)**:
   ```bash
   $ delete "clf sign.png"
   bash: delete: command not found

   $ xsf
     [OFFLINE] rm 'clf sign.png'
     └── Translated natural verb 'delete' to POSIX 'rm' (confidence: 95%)

   Execute? [Enter/y/n]: y
   ```

3. **Natural Language Search / Inspection**:
   ```bash
   $ find all png files
   bash: find: `all`: No such file or directory

   $ xsf
     [AI] find . -name "*.png"
     └── [Gemini] Translated natural query to find all PNG images in current directory. (confidence: 96%)

   Execute? [Enter/y/n]: y
   ```

4. **Common Cross-Shell Translations**:
   - `cls` in Git Bash / Linux → `clear`
   - `copy src dst` in Git Bash / Linux → `cp src dst`
   - `move src dst` in Git Bash / Linux → `mv src dst`
   - `type file.txt` in Git Bash / Linux → `cat file.txt`
   - `delete file.txt` in PowerShell → `Remove-Item file.txt`

> [!TIP]
> Both the **offline engine** (for instant <2ms translations) and the **cloud AI models** (for conversational English instructions) work in harmony. You can simply "speak human" to your terminal!

#### 🛡️ Prevention of Futile Commands ("Already Done!")
If you run a deletion or kill command on something that is already gone (e.g. `delete "file.png"` after the file was already deleted, or killing a PID that has already stopped), `xsf` recognizes that your desired state is already reached:
```text
  [INFO] Target 'file.png' does not exist (already removed). No command needed.
```
It intelligently avoids redundantly asking you to re-execute a command that would just fail again!

---


## 6. Power Switch, API Keys & Account Management

`xsf` uses a **Bring-Your-Own-Key (BYOK)** model so your personal rate limits are 100% yours, backed by a **Power Switch** and automatic **Circuit-Breaker Cooldown Guard**.

👉 **For step-by-step provider walkthroughs, see the dedicated [`guides/`](guides/README.md) folder:**
* [**01 — Groq LPU Free Key Guide (`gsk_...`)**](guides/01-GROQ-LPU-GUIDE.md)
* [**02 — Google Gemini Free Key Guide (`AIza...`)**](guides/02-GOOGLE-GEMINI-GUIDE.md)
* [**03 — OpenRouter & Cerebras Guide**](guides/03-OPENROUTER-AND-CEREBRAS-GUIDE.md)
* [**04 — Grok, OpenAI & Local Ollama Guide**](guides/04-GROK-OPENAI-AND-LOCAL-OLLAMA.md)
* [**05 — Power Switch & Multi-Key Rotation Guide**](guides/05-POWER-SWITCH-AND-KEY-ROTATION.md)

### A. First-Run Guided Setup Wizard
Run the interactive wizard to choose your Power Mode, paste your keys, test connectivity, and auto-install your shell hook:
```bash
xsf setup
```

### B. The `xsf power` Switch
Switch engine modes anytime with zero config editing:
```bash
xsf power status    # View current Power Mode, masked keys, and cooldown health
xsf power hybrid    # Default: Instant Offline (<5ms) + Cloud AI fallback
xsf power offline   # 100% Offline heuristics only (0 network calls, saves 100% quota)
xsf power ai        # Force direct AI diagnosis
xsf power off       # Pause xsf engine
xsf power reset     # Clear all provider rate-limit (429/402) cooldowns
```

### C. Fast CLI Key & Account Switching (`xsf key`)
Switch accounts, attach comma-separated backup keys, or remove keys directly from the CLI:
```bash
# Attach or switch a single key (auto-strips quotes/spaces and tests live connection)
xsf key set groq gsk_YOUR_KEY_HERE --test
xsf key set gemini AIzaSyYOUR_KEY_HERE --test

# Attach primary + backup key for automatic rotation on 429 rate limits
xsf key set groq "gsk_ACCOUNT_1,gsk_ACCOUNT_2" --test

# View step-by-step portal URLs & free quotas in terminal
xsf key guide

# Remove a key
xsf key remove groq
```

### D. Interactive Control Center (`xsf config`)
```bash
xsf config
```
Provides an interactive TUI to toggle the Power Switch (`[P]`), update or rotate keys (`[1]-[6]`), toggle Local Ollama (`[7]`), test all connections (`[9]`), and reset circuit-breaker cooldowns (`[R]`).

---

## 7. Running Local Private LLMs (Ollama)

For air-gapped corporate laptops or 100% private terminal sessions:
1. Install [Ollama](https://ollama.ai).
2. Pull a lightweight coding model:
   ```bash
   ollama run qwen2.5-coder:1.5b
   ```
3. Enable Ollama in `xsf config` (Option 8), or edit `~/.shellfix/config.toml`:
   ```toml
   [local_llm]
   enabled = true
   host = "http://localhost:11434"
   model = "qwen2.5-coder:1.5b"
   ```
`xsf` will automatically query your local Ollama daemon before making any external network requests.

---

## 8. Safety Gate & Destructive Command Guardrails

`xsf` includes a strict security boundary that prevents accidental data loss or destructive execution.

### Destructive Operations Caught
The following actions are classified as **Destructive**:
- Recursive file deletion (`rm -rf`, `rmdir /s /q`, `Remove-Item -Recurse -Force`)
- Force-pushing to Git branches (`git push --force`, `git push -f`, `git push +master`)
- Partition or drive formatting (`format c:`, `mkfs`, `dd if=`)
- Database drops (`DROP DATABASE`, `DROP TABLE`)
- Fork bombs or permission wipes (`chmod -R 777 /`)

### Enforcement Policy
1. **Auto-approve is permanently disabled** for destructive commands, even if `--auto` is passed.
2. An explicit warning badge `⚠️ DESTRUCTIVE ACTION DETECTED` is rendered.
3. The user must explicitly press `[Enter]` after reviewing the warning.

---

## 9. Updating, Syncing & Refreshing

When improvements, new offline rules, or bugfixes are pushed to GitHub:

### Step 1: Pull Latest Commits
```bash
cd ~/tools/xe-shell-fix   # Or your clone path
git pull origin main
```

### Step 2: Reinstall / Refresh Package
```bash
pip install -e .
```

### Step 3: Refresh Your Shell Cache
* In **Git Bash / Bash**:
  ```bash
  hash -r
  source ~/.bashrc
  ```
* In **PowerShell**:
  ```powershell
  . $PROFILE
  ```

### Step 4: (Optional) Reset Local AI Cache
If you want to clear cached AI responses and start fresh:
```bash
# POSIX
rm -f ~/.shellfix/ai_cache.json

# PowerShell
Remove-Item -Force ~/.shellfix/ai_cache.json
```

---

## 10. Clean Uninstallation

If you ever need to remove `xsf` completely with **zero residue**:

### Step 1: Remove Shell Hooks
* In **PowerShell**: Open `$PROFILE` and delete the `xsf init powershell` line.
* In **Git Bash / Bash**: Open `~/.bashrc` and delete `eval "$(command xsf init bash)"`.
* In **Zsh**: Open `~/.zshrc` and delete `eval "$(command xsf init zsh)"`.
* In **Fish**: Open `~/.config/fish/config.fish` and delete the `xsf init fish` line.

### Step 2: Uninstall the Python Package
```bash
pip uninstall xe-shell-fix -y
```

### Step 3: Remove Configuration & Cache Directory
```bash
# POSIX
rm -rf ~/.shellfix

# PowerShell
Remove-Item -Recurse -Force ~/.shellfix
```

---

## 11. Troubleshooting & Common Pitfalls

### Issue: `xsf: command not found` after installing
* **Cause**: Python's `Scripts` directory is not in your environment's `PATH`.
* **Solution (Windows)**:
  Find your Python scripts directory (e.g., `C:\Users\<user>\miniforge3\Scripts` or `C:\Users\<user>\AppData\Local\Programs\Python\Python311\Scripts`) and add it to your User Environment Variables.

### Issue: PowerShell execution error `cannot be loaded because running scripts is disabled`
* **Cause**: Windows default execution policy blocks unsigned scripts.
* **Solution**: Run this command once in PowerShell:
  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

### Issue: `xsf: no previous command found`
* **Cause**: The shell hook was not sourced in the active terminal session.
* **Solution**:
  1. Verify the hook line exists in your profile.
  2. Restart your terminal or run `source ~/.bashrc` / `. $PROFILE`.

### Issue: AI Provider reports `429 Rate Limit` or `503 Service Unavailable`
* **Cause**: Cloud provider temporary throttling.
* **Solution**:
  No action needed. `xsf`'s multi-provider router will automatically fail over to the next provider in your cascade (e.g. Groq -> Cerebras -> Gemini -> OpenRouter).

---

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
