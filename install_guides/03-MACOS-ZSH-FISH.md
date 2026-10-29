# 🍎 macOS Step-by-Step Installation Guide (Zsh & Fish)

This guide covers macOS on **Apple Silicon (M1 / M2 / M3 / M4)** and **Intel Macs** using **Zsh** (the default macOS shell) or **Fish**.

---

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository
```zsh
mkdir -p ~/tools && cd ~/tools
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix
```

### Step 2: Create a Virtual Environment & Install `xsf`
Homebrew Python (3.12+) on macOS also enforces PEP 668 (`externally-managed-environment`), so creating a `venv` is the cleanest approach:
```zsh
python3 -m venv venv
source venv/bin/activate
pip install -e .
```

### Step 3: Run the Interactive Setup Wizard
```zsh
xsf setup
```
This configures your **Power Switch** (`hybrid`, `offline`, `ai_only`), attaches your free **Groq** and **Gemini** API keys, and installs the `xsf` hook into `~/.zshrc` (or `~/.config/fish/config.fish`).

### Step 4: Reload Your Shell & Test
* **In Zsh (macOS Default)**:
  ```zsh
  source ~/.zshrc
  ```
* **In Fish**:
  ```fish
  source ~/.config/fish/config.fish
  ```

Test it:
```zsh
xsf power status
gti status
```

---

## 🛠️ Common macOS Errors & Instant Fixes

### ❌ Error 1: `error: externally-managed-environment` (Homebrew Python)
**Why it happens:**
Homebrew Python (`brew install python`) protects its global site-packages with PEP 668.

**Fix:**
Activate the virtual environment before running `pip install -e .`:
```zsh
python3 -m venv venv
source venv/bin/activate
pip install -e .
```
Or install globally via `pipx`:
```zsh
brew install pipx
pipx ensurepath
pipx install -e .
```

---

### ❌ Error 2: `xcrun: error: invalid active developer path`
**Why it happens:**
After a macOS system update, Xcode Command Line Tools (`git` and `python3`) need to be re-initialized.

**Fix:**
```zsh
xcode-select --install
```

---

### ❌ Error 3: `zsh: command not found: xsf` in New Terminal Tabs
**Why it happens:**
macOS uses **Zsh** (`~/.zshrc`) rather than Bash (`~/.bashrc`). If the hook was added to `~/.bashrc`, Zsh won't read it.

**Fix:**
Add the Zsh hook using your `venv`'s `xsf` binary so it works automatically in every new macOS Terminal / iTerm2 tab:
```zsh
echo 'eval "$('"$PWD"'/venv/bin/xsf init zsh)"' >> ~/.zshrc
source ~/.zshrc
```

---

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
