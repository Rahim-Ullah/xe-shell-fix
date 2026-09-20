"""
xsf.hooks - Shell initialization generator.
"""
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent

SUPPORTED_SHELLS = ("powershell", "pwsh", "bash", "zsh", "fish", "gitbash")


def get_hook_script(shell_name: str) -> str:
    """Returns the hook script content for the requested shell dialect."""
    s = shell_name.lower()
    if s in ("powershell", "pwsh"):
        target = HOOKS_DIR / "powershell.ps1"
    elif s in ("bash", "gitbash"):
        target = HOOKS_DIR / "bash.sh"
    elif s == "zsh":
        target = HOOKS_DIR / "zsh.zsh"
    elif s == "fish":
        target = HOOKS_DIR / "fish.fish"
    else:
        raise ValueError(f"Unsupported shell '{shell_name}'. Supported: {', '.join(SUPPORTED_SHELLS)}")

    if not target.exists():
        raise FileNotFoundError(f"Hook template not found for {shell_name}")

    return target.read_text(encoding="utf-8")
