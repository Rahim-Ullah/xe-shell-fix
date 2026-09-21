"""
Unit tests for fuzzy token and subcommand matching (xsf.offline.fuzzy).
"""
import unittest
from xsf.core.command import Command
from xsf.offline.fuzzy import fuzzy_match_command


class TestFuzzyMatcher(unittest.TestCase):
    def test_program_typos(self):
        cases = [
            ("gti status", "git status"),
            ("dockre ps", "docker ps"),
            ("kubctl get pods", "kubectl get pods"),
            ("cargoo build", "cargo build"),
        ]
        for typo, expected in cases:
            with self.subTest(typo=typo):
                cmd = Command(raw=typo, shell="bash")
                res = fuzzy_match_command(cmd)
                self.assertIsNotNone(res)
                fixed, conf, exp = res
                self.assertEqual(fixed, expected)

    def test_subcommand_typos(self):
        cases = [
            ("git psuh origin main", "git push origin main"),
            ("git statsu", "git status"),
            ("docker bulid .", "docker build ."),
            ("pip instaal fastapi", "pip install fastapi"),
            ("kubectl descirbe pod my-pod", "kubectl describe pod my-pod"),
            ("poetry intall", "poetry install"),
        ]
        for typo, expected in cases:
            with self.subTest(typo=typo):
                cmd = Command(raw=typo, shell="bash")
                res = fuzzy_match_command(cmd)
                self.assertIsNotNone(res)
                fixed, conf, exp = res
                self.assertEqual(fixed, expected)

    def test_tool_aliases(self):
        cases = [
            ("k get pods", "kubectl get pods"),
            ("tf plan", "terraform plan"),
            ("g status", "git status"),
        ]
        for alias_cmd, expected in cases:
            with self.subTest(alias_cmd=alias_cmd):
                cmd = Command(raw=alias_cmd, shell="bash")
                res = fuzzy_match_command(cmd)
                self.assertIsNotNone(res)
                fixed, conf, exp = res
                self.assertEqual(fixed, expected)

    def test_compound_command_subcommands(self):
        cmd = Command(raw="docker compose bulid .", shell="bash")
        res = fuzzy_match_command(cmd)
        self.assertIsNotNone(res)
        fixed, conf, exp = res
        self.assertEqual(fixed, "docker compose build .")

    def test_flag_skipping_subcommand(self):
        cmd = Command(raw="git -C /app statsu", shell="bash")
        res = fuzzy_match_command(cmd)
        self.assertIsNotNone(res)
        fixed, conf, exp = res
        self.assertEqual(fixed, "git -C /app status")

    def test_common_long_flag_dash_slips(self):
        cases = [
            ("python -version", "python --version"),
            ("docker -help", "docker --help"),
        ]
        for typo, expected in cases:
            with self.subTest(typo=typo):
                cmd = Command(raw=typo, shell="bash")
                res = fuzzy_match_command(cmd)
                self.assertIsNotNone(res)
                fixed, conf, exp = res
                self.assertEqual(fixed, expected)

    def test_safe_builtins_never_mangled(self):
        # Short commands should NEVER be "corrected" into tools
        safe_builtins = ["cp foo bar", "ps aux", "cd /tmp", "ls -la", "cat file.txt"]
        for safe in safe_builtins:
            with self.subTest(safe=safe):
                cmd = Command(raw=safe, shell="bash")
                res = fuzzy_match_command(cmd)
                self.assertIsNone(res, f"Safe command '{safe}' was wrongly mangled!")


if __name__ == "__main__":
    unittest.main()
