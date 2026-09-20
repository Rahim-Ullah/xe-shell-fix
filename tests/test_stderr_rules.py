"""
Tests for new stderr-driven, environment, and SSH/network rules.
"""
import unittest
from xsf.core.command import Command


class TestStderrRules(unittest.TestCase):
    """Tests for xsf.offline.rules.stderr_rules."""

    def test_no_such_file_cd(self):
        from xsf.offline.rules.stderr_rules import NoSuchFileOrDirRule
        rule = NoSuchFileOrDirRule()
        cmd = Command(raw="cd myproject", shell="bash", stderr_text="bash: cd: myproject: No such file or directory")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIsNotNone(result)
        self.assertIn("mkdir", result[0])

    def test_no_such_file_non_cd(self):
        from xsf.offline.rules.stderr_rules import NoSuchFileOrDirRule
        rule = NoSuchFileOrDirRule()
        cmd = Command(raw="cat myfile.txt", shell="bash", stderr_text="cat: myfile.txt: No such file or directory")
        self.assertFalse(rule.match(cmd))  # Only matches cd

    def test_module_not_found(self):
        from xsf.offline.rules.stderr_rules import PythonModuleNotFoundRule
        rule = PythonModuleNotFoundRule()
        cmd = Command(raw="python app.py", shell="bash", stderr_text="ModuleNotFoundError: No module named 'flask'")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "pip install flask")

    def test_git_not_a_repo(self):
        from xsf.offline.rules.stderr_rules import GitNotARepoRule
        rule = GitNotARepoRule()
        cmd = Command(raw="git status", shell="bash", stderr_text="fatal: not a git repository (or any of the parent directories): .git")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertEqual(result[0], "git init")

    def test_pip_externally_managed(self):
        from xsf.offline.rules.stderr_rules import PipExternallyManagedRule
        rule = PipExternallyManagedRule()
        cmd = Command(raw="pip install requests", shell="bash", stderr_text="error: externally-managed-environment")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIn("--break-system-packages", result[0])

    def test_node_module_not_found(self):
        from xsf.offline.rules.stderr_rules import NodeModuleNotFoundRule
        rule = NodeModuleNotFoundRule()
        cmd = Command(raw="node app.js", shell="bash", stderr_text="Error: Cannot find module 'express'")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertEqual(result[0], "npm install")

    def test_port_in_use(self):
        from xsf.offline.rules.stderr_rules import PortInUseRule
        rule = PortInUseRule()
        cmd = Command(raw="node server.js", shell="bash", stderr_text="Error: listen EADDRINUSE: address already in use :::3000")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIsNotNone(result)
        self.assertIn("3000", result[0])

    def test_permission_denied_suggests_sudo(self):
        from xsf.offline.rules.stderr_rules import FilePermissionDeniedRule
        rule = FilePermissionDeniedRule()
        cmd = Command(raw="apt install vim", shell="bash", stderr_text="E: Could not open lock file - Permission denied")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertEqual(result[0], "sudo apt install vim")


class TestEnvRules(unittest.TestCase):
    """Tests for xsf.offline.rules.env_rules."""

    def test_python_venv_not_found(self):
        from xsf.offline.rules.env_rules import PythonVenvNotFoundRule
        rule = PythonVenvNotFoundRule()
        cmd = Command(raw="python -m venv .venv", shell="bash", stderr_text="No module named venv")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIn("python3-venv", result[0])

    def test_env_variable_not_set(self):
        from xsf.offline.rules.env_rules import EnvVariableNotSetRule
        rule = EnvVariableNotSetRule()
        cmd = Command(raw="echo $API_KEY", shell="bash", stderr_text="API_KEY: is not set")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIn("export API_KEY", result[0])


class TestSSHNetRules(unittest.TestCase):
    """Tests for xsf.offline.rules.ssh_net_rules."""

    def test_ssh_host_key_verification(self):
        from xsf.offline.rules.ssh_net_rules import SSHHostKeyVerificationRule
        rule = SSHHostKeyVerificationRule()
        cmd = Command(raw="ssh user@server.com", shell="bash", stderr_text="Host key verification failed")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIsNotNone(result)
        self.assertIn("ssh-keygen", result[0])

    def test_curl_connection_failed(self):
        from xsf.offline.rules.ssh_net_rules import CurlConnectionFailedRule
        rule = CurlConnectionFailedRule()
        cmd = Command(raw="curl http://localhost:8080", shell="bash", stderr_text="curl: (7) Failed to connect to localhost port 8080")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIsNotNone(result)
        self.assertIn("-v", result[0])

    def test_ssl_cert_error_curl(self):
        from xsf.offline.rules.ssh_net_rules import SSLCertificateErrorRule
        rule = SSLCertificateErrorRule()
        cmd = Command(raw="curl https://expired.badssl.com", shell="bash", stderr_text="curl: (60) SSL certificate problem: certificate has expired")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIn("-k", result[0])


class TestGitExpandedRules(unittest.TestCase):
    """Tests for new git rules."""

    def test_git_did_you_mean(self):
        from xsf.offline.rules.git_rules import GitDidYouMeanRule
        rule = GitDidYouMeanRule()
        cmd = Command(raw="git statsu", shell="bash",
                       stderr_text="git: 'statsu' is not a git command. Did you mean this?\n\tstatus")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIsNotNone(result)
        self.assertIn("status", result[0])

    def test_git_merge_conflict(self):
        from xsf.offline.rules.git_rules import GitMergeConflictRule
        rule = GitMergeConflictRule()
        cmd = Command(raw="git merge feature", shell="bash",
                       stderr_text="CONFLICT (content): Merge conflict in file.txt\nAutomatic merge failed")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertEqual(result[0], "git status")

    def test_git_pull_rebase(self):
        from xsf.offline.rules.git_rules import GitPullRebaseRule
        rule = GitPullRebaseRule()
        cmd = Command(raw="git pull", shell="bash",
                       stderr_text="hint: You have divergent branches and need to specify how to reconcile them.")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertEqual(result[0], "git pull --rebase")

    def test_git_stash_before_checkout(self):
        from xsf.offline.rules.git_rules import GitStashBeforeCheckoutRule
        rule = GitStashBeforeCheckoutRule()
        cmd = Command(raw="git checkout main", shell="bash",
                       stderr_text="error: Your local changes to the following files would be overwritten by checkout")
        self.assertTrue(rule.match(cmd))
        result = rule.get_new_command(cmd)
        self.assertIn("git stash", result[0])
        self.assertIn("git checkout main", result[0])


if __name__ == "__main__":
    unittest.main()
