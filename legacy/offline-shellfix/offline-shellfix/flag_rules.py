"""
flag_rules.py - deterministic, high-precision fixes for missing or wrong
flags. These run BEFORE the fuzzy matcher in fixcmd.py, because "the word
is spelled fine but a flag is missing" needs pattern logic, not edit
distance.

Each rule is a plain function: (raw, tokens, shell, stderr, vocab) -> None
or (fixed_command_string, confidence 0-1, short_explanation).

This is intentionally a starter set, not an exhaustive one - add your own
rules here as you hit new cases. Keep each rule narrow and cheap; a rule
that's unsure should return None rather than guess.
"""
import difflib
import json
import os
import re
from pathlib import Path

from shellutil import quote_join

STDLIB_RUNNABLE_MODULES = {
    "venv", "http.server", "json.tool", "unittest", "pip", "pdb",
    "cProfile", "profile", "timeit", "zipfile", "tarfile", "calendar",
    "ensurepip", "platform", "this", "site", "compileall", "py_compile",
}

COMMON_NPM_SCRIPTS = {"dev", "build", "start", "test", "lint", "serve", "watch", "format", "preview"}


def _rule_python_missing_m(raw, tokens, shell, stderr, vocab):
    """python venv .venv  ->  python -m venv .venv"""
    if len(tokens) < 2:
        return None
    prog = tokens[0].lower()
    if prog not in ("python", "python3", "py"):
        return None
    if tokens[1] in ("-m", "-c", "-i", "-u", "--version"):
        return None
    if tokens[1] in STDLIB_RUNNABLE_MODULES:
        fixed = [tokens[0], "-m"] + tokens[1:]
        return quote_join(fixed), 0.95, f"'{tokens[1]}' is a stdlib module - it needs -m to run as a script"
    return None


def _rule_git_commit_missing_m(raw, tokens, shell, stderr, vocab):
    """git commit "fix bug"  ->  git commit -m "fix bug" """
    if len(tokens) < 3 or tokens[0] != "git" or tokens[1] != "commit":
        return None
    if any(t in ("-m", "--message", "--amend") for t in tokens):
        return None
    fixed = ["git", "commit", "-m"] + tokens[2:]
    return quote_join(fixed), 0.9, "commit message given without -m"


def _rule_pip_missing_install(raw, tokens, shell, stderr, vocab):
    """pip fastapi  ->  pip install fastapi"""
    if len(tokens) < 2 or tokens[0] not in ("pip", "pip3"):
        return None
    known = vocab.get(tokens[0], {}).get("subcommands", [])
    if tokens[1] in known:
        return None
    # If it's a near-miss of a real pip subcommand ("instaaaaal"), that's a
    # typo, not a bare package name - let the fuzzy matcher fix the spelling
    # instead of this rule wrongly inserting "install" in front of it.
    if difflib.get_close_matches(tokens[1].lower(), known, n=1, cutoff=0.55):
        return None
    if re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*(==|>=|<=|~=)?[A-Za-z0-9.]*$", tokens[1]):
        fixed = [tokens[0], "install"] + tokens[1:]
        return quote_join(fixed), 0.7, f"'{tokens[1]}' looks like a package name, not a pip subcommand"
    return None


def _rule_npm_missing_run(raw, tokens, shell, stderr, vocab):
    """npm dev  ->  npm run dev  (checks package.json in cwd if present)"""
    if len(tokens) < 2 or tokens[0] != "npm":
        return None
    known = vocab.get("npm", {}).get("subcommands", [])
    if tokens[1] in known:
        return None
    scripts = set(COMMON_NPM_SCRIPTS)
    pkg_json = Path.cwd() / "package.json"
    if pkg_json.exists():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
            found = set(data.get("scripts", {}).keys())
            if found:
                scripts = found
        except Exception:
            pass
    if tokens[1] in scripts:
        fixed = ["npm", "run"] + tokens[1:]
        return quote_join(fixed), 0.9, f"'{tokens[1]}' is a package.json script - needs 'run'"
    return None


def _rule_venv_activate(raw, tokens, shell, stderr, vocab):
    """venv\\Scripts\\activate on PowerShell needs .\\...Activate.ps1;
    on Git Bash it needs `source ...`."""
    m = re.search(r"([\w./\\-]+)[\\/]Scripts[\\/]activate(\.\w+)?\b", raw, re.IGNORECASE)
    if not m:
        return None
    venv_dir = m.group(1)
    if shell == "powershell":
        fixed = f".\\{venv_dir}\\Scripts\\Activate.ps1"
        return fixed, 0.85, "PowerShell needs Activate.ps1, run with a leading .\\"
    if shell == "bash":
        fixed = f"source {venv_dir}/Scripts/activate"
        return fixed, 0.85, "Git Bash activates a venv with 'source'"
    return None


def _rule_stderr_permission_denied(raw, tokens, shell, stderr, vocab):
    """Only fires when --rerun captured stderr containing 'Permission denied'."""
    if not stderr or "permission denied" not in stderr.lower():
        return None
    if not tokens or not tokens[0].startswith("./"):
        return None
    return f"chmod +x {tokens[0]} && {raw}", 0.8, "script isn't marked executable yet"


def _rule_stderr_missing_dot_slash(raw, tokens, shell, stderr, vocab):
    """Only fires when --rerun captured a 'not found/not recognized' error
    and a matching file actually exists in the current folder."""
    if not stderr:
        return None
    low = stderr.lower()
    if "not recognized" not in low and "command not found" not in low:
        return None
    if not tokens:
        return None
    candidate = tokens[0]
    if candidate.startswith("./") or "/" in candidate or "\\" in candidate:
        return None
    for ext in ("", ".sh", ".py"):
        path = candidate + ext
        if os.path.exists(path):
            fixed = ["./" + candidate] + tokens[1:]
            return quote_join(fixed), 0.6, f"'{candidate}' exists here but wasn't prefixed with ./"
    return None


RULES = [
    _rule_python_missing_m,
    _rule_git_commit_missing_m,
    _rule_npm_missing_run,
    _rule_pip_missing_install,
    _rule_venv_activate,
    _rule_stderr_permission_denied,
    _rule_stderr_missing_dot_slash,
]


def apply(raw, tokens, shell, stderr_text, vocab):
    for rule in RULES:
        try:
            result = rule(raw, tokens, shell, stderr_text, vocab)
        except Exception:
            result = None
        if result:
            return result
    return None
