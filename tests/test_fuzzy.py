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
