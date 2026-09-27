# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 1.1.x (latest) | ✅ Active |
| < 1.1.0 | ❌ No longer supported |

---

## ⚠️ Why Security Matters for xe-shell-fix

xe-shell-fix (`xsf`) is not a typical calculator or web viewer. Its execution model is:

```
failed command
    ↓
offline heuristics / AI provider
    ↓
candidate command (untrusted input)
    ↓
safety policy engine (confirmation gate)
    ↓
shell execution (user privileges)
```

A vulnerability here can directly result in **arbitrary shell command execution**. Therefore, security issues in xsf are treated with the highest severity.

---

## Reporting a Vulnerability

**Do NOT open a public GitHub Issue for security vulnerabilities.**

Instead, use one of these private channels:

1. **GitHub Security Advisories** _(preferred)_  
   Go to [`Security → Advisories → New draft advisory`](https://github.com/rahim-ullah/xe-shell-fix/security/advisories/new)  
   This is end-to-end encrypted between you and the maintainer.

2. **Direct contact**  
   If GitHub Advisories are unavailable, contact the maintainer through the GitHub profile:  
   [github.com/Rahim-Ullah](https://github.com/Rahim-Ullah)

---

## What to Include in Your Report

Please provide:

- **xe-shell-fix version** (`xsf --version`)
- **Operating system and shell** (e.g., Windows 11 + Git Bash, Ubuntu 24.04 + Zsh)
- **Python version** (`python --version`)
- **Description of the vulnerability** — what the bug is and what it allows an attacker to do
- **Proof-of-concept or reproduction steps** — the minimum steps to trigger the issue
- **Impact assessment** — what data or privilege could be affected
- **Suggested fix** (optional but appreciated)

---

## What to NEVER Include in a Public Report

- API keys or tokens you or others use with xsf
- Content of `~/.shellfix/config.toml` or `~/.shellfix/ai_cache.json`
- Information about your system that isn't required to reproduce the bug

---

## Security Architecture — Key Boundaries

Understanding these boundaries helps you write a good report:

### 1. Command Execution
- xsf does NOT automatically execute any command without user confirmation.
- Every suggested command (from offline rules OR AI providers) passes through `SafetyGuard.confirm()` before being written to stdout for shell `eval`.
- Destructive commands (regex-detected) always require typing the full word `yes`.
- **Bypass of this confirmation flow is a Critical severity vulnerability.**

### 2. Safety Gate Limitations
- The safety gate uses pattern matching (regex). It cannot mathematically guarantee detection of every dangerous command.
- Shell aliasing, encoding, indirect execution, and subprocesses can circumvent pattern-based filters.
- The correct security model is: **AI output is always treated as untrusted input requiring explicit user approval.**

### 3. AI Providers
- API keys are stored in `~/.shellfix/config.toml` with restricted permissions (0600 on POSIX, icacls on Windows).
- The AI request payload contains only: shell dialect, failed command string, and stderr text (truncated at 1500 chars).
- API keys are never sent to or stored in any third-party other than the configured provider's API endpoint.

### 4. Configuration & Credentials
- `~/.shellfix/config.toml` is locked to owner read/write only.
- `~/.shellfix/ai_cache.json` is also locked to owner read/write only.
- Environment variable overrides (`GROQ_API_KEY`, `GEMINI_API_KEY`, etc.) are supported for CI/CD use cases.

### 5. User-Defined Rules
- Custom rule files from `~/.shellfix/rules/*.py` are loaded and executed with full user privileges.
- **Never install rule files from untrusted sources.** This is a documented security boundary.
- The rule loader isolates errors per file so a broken rule cannot crash the entire system.

### 6. Subprocess Usage
- Shell hooks use `eval` on xsf's stdout output. The stdout output is the approved fixed command.
- `help_parser.py` runs `cmd_name --help` as a subprocess to detect flag typos. This uses `subprocess.run()` with a list argument (no shell=True injection risk).

---

## Coordinated Disclosure

Once a vulnerability is reported:

1. The maintainer will acknowledge within **5 business days**.
2. We will work together to verify and reproduce the issue.
3. A fix will be prepared privately and a release published.
4. A GitHub Security Advisory will be published after the fix is released, crediting the reporter (unless they prefer anonymity).

We ask that you give us a **reasonable disclosure window** (suggested: 90 days) before making the vulnerability public.

---

## Scope — In Scope

- Bypass of the safety confirmation gate
- Command injection via any input path (command string, stderr text, rule files)
- Unauthorized command execution without user interaction
- Credential/API key leakage to unauthorized parties
- Privilege escalation through shell hooks
- Insecure file permissions on config or cache files
- AI provider request spoofing or response injection

## Scope — Out of Scope

- Vulnerabilities in third-party AI provider services (Groq, Gemini, etc.) themselves
- Social engineering attacks not involving xsf code
- Issues in the user's own custom rules (user-maintained)
- Known limitations documented in this policy (e.g., regex-based safety gate is not exhaustive)
