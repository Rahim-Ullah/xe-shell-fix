# 🪟 Windows 10 / 11 Step-by-Step Installation Guide (PowerShell & Git Bash)

This guide covers native Windows installations across **Windows PowerShell 5.1**, **PowerShell 7+ (`pwsh`)**, and **Git Bash (MINGW64)** — no WSL required.

---

## 🚀 Step-by-Step Installation

### Step 1: Clone the Repository
Open **PowerShell** or **Git Bash** and run:
```powershell
cd $HOME
mkdir -Force tools
cd tools
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix
```

### Step 2: Create a Virtual Environment & Install `xsf`
#### In PowerShell:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -e .
```

#### In Git Bash (MINGW64):
```bash
python -m venv venv
source venv/Scripts/activate
pip install -e .
```
*(Or if you prefer installing into your global Windows user Python without a venv, simply run `pip install -e .`)*

### Step 3: Run the Interactive Setup Wizard
```powershell
xsf setup
```
This configures your **Engine Power Switch** (`hybrid` / `offline` / `ai_only`), attaches your free **Groq** and **Gemini** API keys, and installs the shell hook into your PowerShell `$PROFILE` or Git Bash `~/.bashrc`.

### Step 4: Reload Your Shell Profile
* **In PowerShell**:
  ```powershell
  . $PROFILE
  ```
* **In Git Bash**:
  ```bash
  source ~/.bashrc
  ```

### Step 5: Verify & Test!
```powershell
xsf power status
gti status
```

---

## 🛠️ Common Windows Errors & Instant Fixes

### ❌ Error 1: `File ... cannot be loaded because running scripts is disabled on this system`
**What you saw:**
```text
. : File C:\Users\You\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1 cannot be loaded because running scripts is disabled on this system. (PSSecurityException)
```
**Why it happens:**
Windows PowerShell defaults to a `Restricted` execution policy on new machines, which blocks both `Activate.ps1` and your `$PROFILE` script from running.

**Fix:**
Run this command once in PowerShell (no Administrator privileges required):
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```
Then reload your profile:
```powershell
. $PROFILE
```

---

### ❌ Error 2: `-e option requires 1 argument`
**Why it happens:**
Running `pip install -e` without the trailing dot (`.`) omits the target project directory.

**Fix:**
Always include the trailing dot (`.`):
```powershell
pip install -e .
# Or with test tools:
pip install -e ".[dev]"
```

---

### ❌ Error 3: `xsf : The term 'xsf' is not recognized as the name of a cmdlet...`
**Why it happens:**
Either:
1. You installed `xsf` inside `venv` and opened a new PowerShell window before installing the `$PROFILE` hook, OR
2. Your global Python `Scripts` directory (e.g. `C:\Users\<User>\AppData\Local\Programs\Python\Python312\Scripts`) is not in your Windows `PATH`.

**Fix (Works whether `Scripts` is on `PATH` or inside `venv`):**
Add the hook to your PowerShell `$PROFILE` pointing to your Python executable:
```powershell
if (!(Test-Path -Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force }
notepad $PROFILE
```
Paste this line at the bottom of Notepad, save, and run `. $PROFILE`:
```powershell
try { (& (Get-Command -CommandType Application xsf -ErrorAction Stop | Select-Object -First 1) init powershell | Out-String) | Invoke-Expression } catch { (& python -m xsf.cli init powershell | Out-String) | Invoke-Expression }
```

---

### ❌ Error 4: `Python was not found; run without arguments to install from the Microsoft Store`
**Why it happens:**
Windows 10/11 includes dummy `python.exe` and `python3.exe` shortcuts in `%LOCALAPPDATA%\Microsoft\WindowsApps` that redirect to the Microsoft Store instead of your real Python installation.

**Fix:**
1. Press the **Windows Key** and type **Manage app execution aliases**.
2. Turn **OFF** the toggles for `App Installer (python.exe)` and `App Installer (python3.exe)`.
3. Restart your terminal.

---

### ❌ Error 5: Git Bash Does Not Load `~/.bashrc` When Opening a New Window
**Why it happens:**
Git Bash on Windows launches as a login shell (`--login`), which reads `~/.bash_profile` first and sometimes skips `~/.bashrc` if `~/.bash_profile` doesn't source it.

**Fix:**
Run this once in Git Bash so `~/.bash_profile` always loads `~/.bashrc`:
```bash
echo '[ -f ~/.bashrc ] && . ~/.bashrc' >> ~/.bash_profile
source ~/.bash_profile
```

---

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
