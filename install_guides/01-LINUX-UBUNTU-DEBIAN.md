# 🐧 Linux & Ubuntu Step-by-Step Installation Guide

This guide covers **Ubuntu (20.04 / 22.04 / 24.04+)**, **Debian**, **Linux Mint**, **Kali**, **Fedora**, and **Arch Linux** using **Bash**, **Zsh**, or **Fish**.

---

## 🚀 Step-by-Step Installation (The Clean Virtual Environment Way)

Modern Linux distributions (Ubuntu 23.04+, Debian 12+, Python 3.12–3.14) enforce **PEP 668 (`externally-managed-environment`)**, which blocks running `pip install` directly against the system Python so you don't accidentally break OS packages (`apt`).

The cleanest, industry-standard way to install `xsf` on Linux is inside a local virtual environment (`venv`):

### Step 1: Clone or Open the Repository
```bash
# If you haven't cloned it yet:
mkdir -p ~/tools && cd ~/tools
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix

# Or if you already downloaded it (e.g., in ~/Downloads/xeeee_shell_fix):
cd ~/Downloads/xeeee_shell_fix
```

### Step 2: Create & Activate Your Virtual Environment
```bash
# Create the virtual environment (skip if a 'venv' folder already exists)
python3 -m venv venv

# Activate it (your prompt will now show '(venv)' at the start)
source venv/bin/activate
```

### Step 3: Install `xsf` (Note the `.` at the end!)
```bash
# Standard install (zero external runtime dependencies!)
pip install -e .

# Or with developer test tools (pytest & ruff):
pip install -e ".[dev]"
```

### Step 4: Run the Interactive Setup Wizard
```bash
xsf setup
```
`xsf setup` will:
1. Let you pick your **Engine Power Mode** (`hybrid`, `offline`, `ai_only`, or `off`).
2. Help you attach and live-test your personal free **Groq** (`gsk_...`) and **Gemini** (`AIza...`) API keys.
3. Automatically append the `xsf` hook into your `~/.bashrc` (or `~/.zshrc`).

### Step 5: Reload Your Shell & Test!
```bash
source ~/.bashrc
```

Now test it in your terminal:
```bash
# 1. Check status & Power Switch
xsf power status

# 2. Type a deliberate typo to watch the hook catch it:
gti status
```

> [!TIP]
> **Do I need to run `source venv/bin/activate` every time I open a new terminal?**
> **No!** When `xsf setup` (or `eval "$(./venv/bin/xsf init bash)"`) installs the hook into your `~/.bashrc`, it automatically records the exact path to `./venv/bin/python` inside `_XSF_INIT_PYTHON`. Every new terminal window you open will automatically use `xsf` without needing to activate `venv` manually!

---

## 🛠️ Common Linux / Ubuntu Errors & Instant Fixes

### ❌ Error 1: `error: externally-managed-environment` (PEP 668)
**What you saw:**
```text
$ pip install -e ".[dev]"
error: externally-managed-environment
× This environment is externally managed
╰─> To install Python packages system-wide, try apt install python3-xyz...
```
**Why it happens:**
You ran `pip install` using Ubuntu's global `/usr/bin/pip` without activating your virtual environment (`venv`) first.

**Fix (Choose One):**
* **Fix A — Activate `venv` first (Recommended):**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  pip install -e ".[dev]"
  ```
* **Fix B — Call the `venv` pip directly (Even without activating):**
  ```bash
  ./venv/bin/pip install -e ".[dev]"
  ```
* **Fix C — Install via `pipx` (Global isolated CLI tool):**
  ```bash
  sudo apt update && sudo apt install -y pipx
  pipx ensurepath
  pipx install -e .
  ```

---

### ❌ Error 2: `-e option requires 1 argument`
**What you saw:**
```text
$ pip install -e
Usage:   
  pip install [options] <requirement specifier> [package-index-options] ...
-e option requires 1 argument
```
**Why it happens:**
The `-e` (`--editable`) flag needs to know **where** the project folder is located. A single dot (`.`) tells `pip` "install the project in my current directory".

**Fix:**
Always include `.` or `".[dev]"` after `-e`:
```bash
pip install -e .
# or:
pip install -e ".[dev]"
```

---

### ❌ Error 3: `The virtual environment was not created successfully because ensurepip is not available`
**What you saw:**
On fresh Ubuntu/Debian installations, running `python3 -m venv venv` may fail asking you to install `python3-venv`.

**Fix:**
```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-full
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

---

### ❌ Error 4: `Cannot import 'setuptools.build_meta'` (When Installing Offline / Without Internet)
**What you saw:**
In Python 3.12–3.14, a freshly created `venv` does not bundle `setuptools` inside the virtual environment by default, so `pip` tries to download `setuptools` from PyPI during build isolation. If you are offline, that download fails.

**Fix (100% Offline Install using Ubuntu's system `setuptools`):**
```bash
PYTHONPATH=/usr/lib/python3/dist-packages ./venv/bin/pip install --no-build-isolation --no-deps -e .
```

---

### ❌ Error 5: `xsf: command not found` in a New Terminal Window
**Why it happens:**
The `xsf` shell hook hasn't been added to `~/.bashrc` (or `~/.zshrc`), or you haven't reloaded `~/.bashrc` yet.

**Fix:**
Run this once from your project folder (replacing the path if you cloned elsewhere):
```bash
# Add the hook using your venv's xsf binary (persists across all future terminals!)
grep -q "xsf init bash" ~/.bashrc || echo 'eval "$('"$PWD"'/venv/bin/xsf init bash)"' >> ~/.bashrc
source ~/.bashrc

# Make `xsf` a real binary on PATH everywhere (any folder, any shell, no reload needed).
# `xsf setup` does this automatically; run manually only if you skipped setup:
mkdir -p ~/.local/bin
for c in xsf xefix xeeee fuxx; do ln -sf "$PWD/venv/bin/$c" ~/.local/bin/$c; done
```

---

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
