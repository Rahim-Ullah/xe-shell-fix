"""
Unit tests for deterministic rule plugins (xsf.offline.rules).
"""
import unittest
from xsf.core.command import Command
from xsf.offline.rules import evaluate_rules


class TestOfflineRules(unittest.TestCase):
    def test_python_missing_m(self):
        cmd = Command(raw="python venv .venv", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "python -m venv .venv")
        self.assertGreaterEqual(conf, 0.95)

    def test_git_commit_missing_m(self):
        cmd = Command(raw='git commit "initial commit"', shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertIn(fixed, ('git commit -m "initial commit"', "git commit -m 'initial commit'"))

    def test_git_branch_flag_fix(self):
        cmd = Command(raw="git branch d feature-x", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "git branch -d feature-x")

    def test_npm_missing_run(self):
        cmd = Command(raw="npm dev", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "npm run dev")

    def test_yarn_install_to_add(self):
        cmd = Command(raw="yarn install lodash", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "yarn add lodash")

    def test_cargo_shorthand(self):
        cmd = Command(raw="cargo b --release", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "cargo build --release")

    def test_docker_compose_v2(self):
        cmd = Command(raw="docker-compose up -d", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "docker compose up -d")

    def test_cd_dot_dot(self):
        cmd = Command(raw="cd..", shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "cd ..")

    def test_git_push_upstream_stderr(self):
        stderr = "fatal: The current branch feature-1 has no upstream branch.\nTo push the current branch and set the remote as upstream, use\n\n    git push --set-upstream origin feature-1\n"
        cmd = Command(raw="git push", stderr_text=stderr, shell="bash")
        result = evaluate_rules(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "git push --set-upstream origin feature-1")

    def test_expanded_shell_typos(self):
        cases = [
            ("clss", "cls"),
            ("ipconfgi /all", "ipconfig /all"),
            ("wngit search vscode", "winget search vscode"),
            ("pnmp install", "pnpm install"),
            ("rufff check .", "ruff check ."),
            ("olama run qwen", "ollama run qwen"),
        ]
        for raw, expected in cases:
            cmd = Command(raw=raw, shell="powershell")
            result = evaluate_rules(cmd)
            self.assertIsNotNone(result, f"Failed to match typo '{raw}'")
            fixed, conf, exp = result
            self.assertEqual(fixed, expected)


    def test_cross_shell_natural_commands(self):
        cases_bash = [
            ('delete "clf sign.png"', "rm 'clf sign.png'"),
            ('del file.txt', 'rm file.txt'),
            ('rename old.txt new.txt', 'mv old.txt new.txt'),
            ('copy a.txt b.txt', 'cp a.txt b.txt'),
            ('move a.txt b.txt', 'mv a.txt b.txt'),
            ('cls', 'clear'),
            ('type notes.txt', 'cat notes.txt'),
            ('md mydir', 'mkdir mydir'),
        ]
        for raw, expected in cases_bash:
            cmd = Command(raw=raw, shell="bash")
            result = evaluate_rules(cmd)
            self.assertIsNotNone(result, f"Failed on natural verb '{raw}'")
            fixed, conf, exp = result
            self.assertEqual(fixed, expected)
            self.assertGreaterEqual(conf, 0.90)

        # PowerShell natural verb
        cmd_ps = Command(raw='delete "file.txt"', shell="powershell")
        result_ps = evaluate_rules(cmd_ps)
        self.assertIsNotNone(result_ps)
        fixed_ps, conf_ps, _ = result_ps
        self.assertIn(fixed_ps, ('Remove-Item "file.txt"', "Remove-Item 'file.txt'", "Remove-Item file.txt"))

    def test_requires_output_flags(self):
        from xsf.offline.rules.shell_rules import CommonShellTyposRule, CdDotDotRule, SudoPrefixRule
        from xsf.offline.rules.package_rules import NpmMissingRunRule
        from xsf.offline.rules.stderr_rules import PortInUseRule

        self.assertFalse(CommonShellTyposRule().requires_output)
        self.assertFalse(CdDotDotRule().requires_output)
        self.assertFalse(NpmMissingRunRule().requires_output)
        self.assertTrue(SudoPrefixRule().requires_output)
        self.assertTrue(PortInUseRule().requires_output)

    def test_get_all_rule_candidates(self):
        from xsf.offline.rules import get_all_rule_candidates
        cmd = Command(raw="cdd Downloads", shell="bash")
        candidates = get_all_rule_candidates(cmd)
        self.assertGreaterEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0], "cd Downloads")

    def test_partial_fix_superseded_in_offline_candidates(self):
        from xsf.offline import get_offline_candidates
        cmd = Command(raw="giit statusu", shell="bash")
        candidates = get_offline_candidates(cmd)
        cand_commands = [c[0] for c in candidates]
        # Should contain "git status"
        self.assertIn("git status", cand_commands)
        # Should NOT contain the half-baked partial fix "git statusu"
        self.assertNotIn("git statusu", cand_commands)


if __name__ == "__main__":
    unittest.main()
