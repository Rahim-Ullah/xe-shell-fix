"""
Tests for xsf.hooks - Shell hook file validation.

Ensures all hook files exist, are non-empty, and contain critical patterns
like alias definitions, subcommand delegation, and history-skip logic.
"""
import unittest
from pathlib import Path

from xsf.hooks import HOOKS_DIR, SUPPORTED_SHELLS, get_hook_script


class TestHookFilesExist(unittest.TestCase):
    """Verify all hook template files exist and are non-empty."""

    def test_bash_hook_exists(self):
        path = HOOKS_DIR / "bash.sh"
        self.assertTrue(path.exists(), "bash.sh hook template missing")
        self.assertGreater(path.stat().st_size, 100)

    def test_zsh_hook_exists(self):
        path = HOOKS_DIR / "zsh.zsh"
        self.assertTrue(path.exists(), "zsh.zsh hook template missing")
        self.assertGreater(path.stat().st_size, 100)

    def test_fish_hook_exists(self):
        path = HOOKS_DIR / "fish.fish"
        self.assertTrue(path.exists(), "fish.fish hook template missing")
        self.assertGreater(path.stat().st_size, 100)

    def test_powershell_hook_exists(self):
        path = HOOKS_DIR / "powershell.ps1"
        self.assertTrue(path.exists(), "powershell.ps1 hook template missing")
        self.assertGreater(path.stat().st_size, 100)


class TestHookContent(unittest.TestCase):
    """Verify hook scripts contain required patterns."""

    def test_bash_has_all_aliases(self):
        content = get_hook_script("bash")
        for alias in ("xsf", "xefix", "xeeee", "fuxx"):
            self.assertIn(alias, content, f"Bash hook missing alias: {alias}")

    def test_bash_has_subcommand_delegation(self):
        content = get_hook_script("bash")
        self.assertIn("init", content)
        self.assertIn("config", content)
        self.assertIn("command xsf", content, "Bash hook must use 'command xsf' for binary lookup")

    def test_bash_has_history_skip(self):
        content = get_hook_script("bash")
        self.assertIn("fc -ln", content, "Bash hook must use 'fc' for history")
        self.assertIn("grep -vE", content, "Bash hook must filter trigger aliases from history")

    def test_powershell_has_all_functions(self):
        content = get_hook_script("powershell")
        for name in ("xsf", "xefix", "xeeee", "fuxx"):
            self.assertIn(name, content, f"PowerShell hook missing function: {name}")

    def test_powershell_has_subcommand_delegation(self):
        content = get_hook_script("powershell")
        self.assertIn("init", content)
        self.assertIn("config", content)
        self.assertIn("Get-Command", content)

    def test_zsh_has_all_aliases(self):
        content = get_hook_script("zsh")
        for alias in ("xsf", "xefix", "xeeee", "fuxx"):
            self.assertIn(alias, content, f"Zsh hook missing alias: {alias}")

    def test_fish_has_all_functions(self):
        content = get_hook_script("fish")
        for name in ("xsf", "xefix", "xeeee", "fuxx"):
            self.assertIn(name, content, f"Fish hook missing function: {name}")


class TestGetHookScript(unittest.TestCase):
    """Test get_hook_script() returns content for all supported shells."""

    def test_all_supported_shells_return_content(self):
        for shell in SUPPORTED_SHELLS:
            content = get_hook_script(shell)
            self.assertIsInstance(content, str)
            self.assertGreater(len(content), 50, f"Hook for {shell} is too short")

    def test_gitbash_maps_to_bash(self):
        bash_content = get_hook_script("bash")
        gitbash_content = get_hook_script("gitbash")
        self.assertEqual(bash_content, gitbash_content)

    def test_unsupported_shell_raises(self):
        with self.assertRaises(ValueError):
            get_hook_script("cmd")

    def test_pwsh_maps_to_powershell(self):
        ps_content = get_hook_script("powershell")
        pwsh_content = get_hook_script("pwsh")
        self.assertEqual(ps_content, pwsh_content)


if __name__ == "__main__":
    unittest.main()
