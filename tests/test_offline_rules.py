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


if __name__ == "__main__":
    unittest.main()
