# 🚀 `xe-shell-fix` (`xsf`) — Future Modules & Feature Blueprints

This document catalogs high-impact, zero-bloat modules designed specifically for `xsf`'s multi-tier architecture, strict `<5ms` offline latency budget, and zero-external-dependency philosophy.

---

## 🏆 Tier A: Core Engine & Workflow Multipliers (Top 5)

### 1. Automatic Zero-Rerun Stderr Ring-Buffer & Safe Auto-Capture (`xsf/core/stderr_capture.py`)
* **The Problem**: Today, shell hooks (`fc -ln` / `Get-History`) capture the *command text* that failed, but not its `stderr` output unless `--stderr-file` or `-Rerun` is used. Yet 40%+ of `xsf`'s smartest rules (`GitPushNoUpstreamRule`, `PythonModuleNotFoundRule`, `FuzzyPathCorrectionRule`, `GitBranchFuzzyRule`, `PortInUseRule`) depend on `stderr_text`.
* **The Solution**:
  1. **Safe Auto-Rerun Engine**: When `stderr_text` is empty, check if `cmd.program` + `cmd.subcommand` is listed in `vocabulary.json`'s `safe_autorun` allowlist (or is an idempotent read-only command). If safe, automatically capture its stderr in a `0.4s` sandboxed subprocess with zero user friction.
  2. **Opt-in Shell Ring Buffer**: Lightweight shell hook option (`xsf init bash --capture-stderr`) that tees stderr of interactive commands to a per-session `/tmp/xsf_err_$PPID.log` capped at 16 KB.
* **Latency Impact**: `0ms` for static rules; `15–60ms` for safe read-only auto-capture.

---

### 2. `xsf explain` & Interactive `?` Candidate Deconstructor (`xsf/core/explainer.py`)
* **The Problem**: Developers often hesitate to press `Enter` on complex suggested commands (`find . -mtime +7 -exec ...`, `git rebase --onto`, `tar -xzvf`, `awk` pipelines) because they want to know what every flag does first.
* **The Solution**:
  1. **`?` Hotkey in Selector**: Pressing `?` inside the multi-candidate arrow-key selector (`xsf/ui/selector.py`) expands an inline token-by-token breakdown of the currently highlighted command without leaving the menu.
  2. **Standalone `xsf explain "<cmd>"`**: Breaks down any complex command into its program, subcommand, flags (extracted offline via `help_parser.py` in `<50ms`), and pipe/redirect operators, with AI fallback for multi-stage pipelines.
* **Latency Impact**: `<40ms` offline via cached `--help` parsing.

---

### 3. Proactive Natural-Language Terminal Copilot (`xsf do` / `xsf ask` — `xsf/core/nl2cmd.py`)
* **The Problem**: Currently `xsf` is reactive (run *after* a command fails). Often a user knows what they want ("find all files >100MB modified today", "kill process on port 8000", "undo last git commit but keep changes staged") and doesn't want to type a broken command first.
* **The Solution**:
  - Add `xsf do "<intent>"` (or `xsf ask "<intent>"`).
  - **Tier 1 Offline Intent Matcher**: Regex + keyword intent templates for the 60 most common developer/sysadmin tasks (`git undo`, `port kill`, `tar extract`, `disk usage`, `find large files`) in `<3ms`.
  - **Tier 2/3 AI Fallback**: Routes complex natural requests through `AIRouter` and `SafetyGuard`, then injects the approved command directly into the active shell session.

---

### 4. Archive, Compression & Cloud/Kubernetes Rule Pack (`xsf/offline/rules/archive_rules.py` & `cloud_k8s_rules.py`)
* **The Problem**: `tar`/`zip` flag ordering and `kubectl`/`docker` resource names are among the highest-frequency daily CLI errors.
* **The Solution**:
  - **`archive_rules.py`**:
    - Fixes `tar` flag order traps (`tar -zxfv app.tar.gz` where `-f` must be last before the archive name → `tar -xzvf app.tar.gz`).
    - Fixes mismatched tool/extension (`unzip archive.tar.gz` → `tar -xzf archive.tar.gz`, `tar -xzf archive.tar.bz2` → `tar -xjf archive.tar.bz2`).
  - **`cloud_k8s_rules.py`**:
    - Fuzzy-matches mistyped Kubernetes namespaces and context names directly against `~/.kube/config` (zero network calls, `<3ms`).
    - Fixes `kubectl exec my-pod bash` → `kubectl exec -it my-pod -- bash`.

---

### 5. `xsf doctor` — Self-Diagnostics, Permission Auditor & Benchmark Suite (`xsf/core/doctor.py`)
* **The Problem**: When a user sets up `xsf` across multiple machines (Ubuntu, WSL, macOS, Windows PowerShell), they want a single command to verify everything is wired optimally.
* **The Solution**:
  - `xsf doctor` inspects:
    1. Shell hook presence in `~/.bashrc`, `~/.zshrc`, `config.fish`, or `$PROFILE`.
    2. Strict `0600`/`0700` permissions on `~/.shellfix/config.toml`, `ai_cache.json`, `provider_health.json`, and `rules/`.
    3. Offline heuristic benchmark (verifying 100 sample commands run in `<5ms`).
    4. AI Provider key health, cooldown status, and live round-trip latency (`ms`).

---

## 🧠 Tier B: Next-Gen Power Features (5 Additional High-Value Proposals)

### 6. Project-Context-Aware Script & Task Healer (`xsf/offline/rules/project_context_rules.py`)
* **The Idea**: Inspect the current working directory (`cmd.cwd`) for `package.json`, `pyproject.toml`, `Makefile`, `Cargo.toml`, or `docker-compose.yml` in `<2ms`:
  - If a user runs `npm run startt` or `pnpm test:unitt`, parse `scripts` inside `./package.json` and fuzzy-match the exact project script name (`npm run start`, `pnpm run test:unit`)!
  - If a user runs `make biuld`, parse target names from `./Makefile` and suggest `make build`!
  - If a user runs `pytest` inside a Poetry/uv/venv project where `pytest` isn't global, automatically suggest `poetry run pytest` / `uv run pytest` / `.venv/bin/pytest`!

---

### 7. Personal Mistake Memory & Adaptive Learning Engine (`xsf/offline/memory.py`)
* **The Idea**: Every developer has unique, recurring muscle-memory typos or project-specific command fixes.
* **How It Works**:
  - Whenever a user accepts a fix (from either AI or multi-candidate selection), record `(shell, normalized_failed_cmd) -> approved_fixed_cmd` in `~/.shellfix/learned_fixes.json`.
  - Next time the user makes the exact same mistake, **Tier 0 (Personal Memory)** resolves it in **`<0.5ms` offline** with `99%` confidence — even if it originally required a Cloud AI call!
  - Includes `xsf memory list` and `xsf memory clear`.

---

### 8. Pipeline & Multi-Command Chain Healer (`xsf/core/pipeline_healer.py`)
* **The Idea**: Real terminal commands often chain multiple tools (`git status | grpe modified | awk '{print $2}'` or `cd build && cmkae .. && mkae -j4`).
* **How It Works**:
  - Currently, offline rules inspect `cmd.tokens[0]`. If the typo is in the *second* or *third* command of a pipe/chain (`grpe`, `cmkae`, `mkae`), offline rules miss it and fall back to AI.
  - A dedicated `PipelineHealer` splits `|` / `&&` / `;` segments, runs Tier 1a offline heuristics on *each* segment independently, and reassembles the healed pipeline in `<4ms` offline!

---

### 9. Interactive Command Edit-Before-Run (`[e]` Hotkey in Prompt / Selector)
* **The Idea**: Sometimes a suggested fix is 95% right, and the user just wants to tweak one filename or flag before executing.
* **How It Works**:
  - Pressing `e` or `Tab` in the confirmation prompt / selector opens an inline editable pre-filled input prompt (`readline` on POSIX, `msvcrt` on Windows) with the suggested command already typed in, allowing instant cursor editing before pressing `Enter` to run (with `SafetyGuard` re-verifying the edited command!).

---

### 10. Secret Leak Prevention Gate Before Execution (`xsf/core/secret_guard.py`)
* **The Idea**: Developers sometimes accidentally paste an API key, `.env` line, or private token directly into the terminal as a command, or run `git add .` when `.env` / `id_rsa` is untracked and unignored.
* **How It Works**:
  - Detects when the failed command itself was an accidentally pasted secret/token (e.g. `sk-proj-...: command not found`) and warns the user to clear their shell history (`history -d`) instead of sending it anywhere.
  - Warns if `git add .` or `git commit -a` is about to stage a file matching `.env`, `*.pem`, or `id_rsa`.

---

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
