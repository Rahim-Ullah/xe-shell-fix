"""
Unit tests for FuzzyPathCorrectionRule and GitBranchFuzzyRule.
"""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from xsf.core.command import Command
from xsf.offline.rules.path_rules import FuzzyPathCorrectionRule
from xsf.offline.rules.git_rules import GitBranchFuzzyRule


class TestFuzzyPathCorrectionRule(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        # Create some sample files and directories
        (self.root / "documents").mkdir()
        (self.root / "documents" / "report.txt").write_text("hello")
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print(1)")
        (self.root / "config.json").write_text("{}")
        self.orig_cwd = os.getcwd()
        os.chdir(self.root)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        self.tmp_dir.cleanup()

    def test_single_file_typo_resolved(self):
        rule = FuzzyPathCorrectionRule()
        cmd = Command(
            raw="cat confg.json",
            stderr_text="cat: confg.json: No such file or directory",
            shell="bash",
        )
        self.assertTrue(rule.match(cmd))
        candidates = rule.get_candidates(cmd)
        self.assertTrue(len(candidates) > 0)
        fixed_cmd, conf, exp = candidates[0]
        self.assertEqual(fixed_cmd, "cat config.json")
        self.assertIn("config.json", exp)

    def test_nested_path_typo_resolved(self):
        rule = FuzzyPathCorrectionRule()
        cmd = Command(
            raw="python scr/app.py",
            stderr_text="python: can't open file 'scr/app.py': [Errno 2] No such file or directory",
            shell="bash",
        )
        self.assertTrue(rule.match(cmd))
        candidates = rule.get_candidates(cmd)
        self.assertTrue(len(candidates) > 0)
        fixed_cmd, conf, exp = candidates[0]
        self.assertEqual(fixed_cmd, "python src/app.py")

    def test_case_insensitive_matching(self):
        rule = FuzzyPathCorrectionRule()
        cmd = Command(
            raw="ls DOCUMENTS/report.txt",
            stderr_text="ls: cannot access 'DOCUMENTS/report.txt': No such file or directory",
            shell="bash",
        )
        self.assertTrue(rule.match(cmd))
        candidates = rule.get_candidates(cmd)
        self.assertTrue(len(candidates) > 0)
        fixed_cmd, conf, exp = candidates[0]
        self.assertEqual(fixed_cmd, "ls documents/report.txt")

    def test_unrelated_error_ignored(self):
        rule = FuzzyPathCorrectionRule()
        cmd = Command(
            raw="git push origin main",
            stderr_text="fatal: Authentication failed",
            shell="bash",
        )
        self.assertFalse(rule.match(cmd))


class TestGitBranchFuzzyRule(unittest.TestCase):
    @patch("xsf.offline.rules.git_rules._get_git_branches")
    def test_git_checkout_branch_typo(self, mock_branches):
        mock_branches.return_value = ["main", "feature/auth-token", "bugfix/payment-flow"]
        rule = GitBranchFuzzyRule()

        cmd = Command(
            raw="git checkout feat-auth-token",
            stderr_text="error: pathspec 'feat-auth-token' did not match any file(s) known to git",
            shell="bash",
        )
        self.assertTrue(rule.match(cmd))
        candidates = rule.get_candidates(cmd)
        self.assertTrue(len(candidates) > 0)
        fixed_cmd, conf, exp = candidates[0]
        self.assertEqual(fixed_cmd, "git checkout feature/auth-token")
        self.assertIn("feature/auth-token", exp)

    @patch("xsf.offline.rules.git_rules._get_git_branches")
    def test_git_switch_branch_typo(self, mock_branches):
        mock_branches.return_value = ["main", "staging", "development"]
        rule = GitBranchFuzzyRule()

        cmd = Command(
            raw="git switch mainn",
            stderr_text="fatal: invalid reference: mainn",
            shell="bash",
        )
        self.assertTrue(rule.match(cmd))
        candidates = rule.get_candidates(cmd)
        self.assertTrue(len(candidates) > 0)
        fixed_cmd, conf, exp = candidates[0]
        self.assertEqual(fixed_cmd, "git switch main")

    @patch("xsf.offline.rules.git_rules._get_git_branches")
    def test_non_branch_command_ignored(self, mock_branches):
        mock_branches.return_value = ["main"]
        rule = GitBranchFuzzyRule()

        cmd = Command(
            raw="git commit -m 'test'",
            stderr_text="nothing to commit",
            shell="bash",
        )
        self.assertFalse(rule.match(cmd))


if __name__ == "__main__":
    unittest.main()
