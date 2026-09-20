"""
Tests for xsf.core.command - Command data model, tokenization, and quoting.
"""
import unittest
from xsf.core.command import Command


class TestCommandParsing(unittest.TestCase):
    """Tests for Command tokenization across shell dialects."""

    def test_basic_posix_tokenization(self):
        cmd = Command(raw="git commit -m 'hello world'", shell="bash")
        self.assertEqual(cmd.tokens, ["git", "commit", "-m", "hello world"])

    def test_powershell_tokenization(self):
        cmd = Command(raw='git commit -m "hello world"', shell="powershell")
        self.assertEqual(cmd.tokens[0], "git")
        self.assertEqual(cmd.tokens[1], "commit")
        self.assertEqual(cmd.tokens[2], "-m")

    def test_empty_command(self):
        cmd = Command(raw="", shell="bash")
        self.assertEqual(cmd.tokens, [])
        self.assertEqual(cmd.program, "")
        self.assertEqual(cmd.subcommand, "")

    def test_single_token(self):
        cmd = Command(raw="ls", shell="bash")
        self.assertEqual(cmd.tokens, ["ls"])
        self.assertEqual(cmd.program, "ls")
        self.assertEqual(cmd.subcommand, "")

    def test_whitespace_stripping(self):
        cmd = Command(raw="  git status  ", shell="bash")
        self.assertEqual(cmd.raw, "git status")
        self.assertEqual(cmd.tokens, ["git", "status"])

    def test_program_property(self):
        cmd = Command(raw="docker compose up -d", shell="bash")
        self.assertEqual(cmd.program, "docker")

    def test_subcommand_property(self):
        cmd = Command(raw="docker compose up -d", shell="bash")
        self.assertEqual(cmd.subcommand, "compose")

    def test_malformed_quotes_fallback(self):
        """shlex.split raises ValueError on unmatched quotes; should fallback to split()."""
        cmd = Command(raw="echo 'unmatched quote", shell="bash")
        self.assertIn("echo", cmd.tokens)
        self.assertTrue(len(cmd.tokens) >= 2)

    def test_special_characters(self):
        cmd = Command(raw="echo $HOME", shell="bash")
        self.assertIn("echo", cmd.tokens)

    def test_pipe_command(self):
        cmd = Command(raw="cat file.txt | grep error", shell="bash")
        self.assertTrue(len(cmd.tokens) >= 3)


class TestCommandQuoting(unittest.TestCase):
    """Tests for quote_join across shell dialects."""

    def test_posix_quote_join(self):
        cmd = Command(raw="echo hello", shell="bash")
        result = cmd.quote_join(["echo", "hello world"])
        self.assertIn("hello world", result)

    def test_powershell_quote_join_special_chars(self):
        cmd = Command(raw="echo test", shell="powershell")
        result = cmd.quote_join(["echo", "hello world"])
        self.assertIn('"', result)  # Should be quoted

    def test_powershell_no_quoting_simple(self):
        cmd = Command(raw="git status", shell="powershell")
        result = cmd.quote_join(["git", "status"])
        self.assertEqual(result, "git status")

    def test_empty_tokens_quote_join(self):
        cmd = Command(raw="", shell="bash")
        self.assertEqual(cmd.quote_join([]), "")


class TestCommandDefaults(unittest.TestCase):
    """Tests for Command default field values."""

    def test_default_shell(self):
        cmd = Command(raw="ls")
        self.assertEqual(cmd.shell, "bash")

    def test_default_stderr(self):
        cmd = Command(raw="ls")
        self.assertEqual(cmd.stderr_text, "")

    def test_custom_stderr(self):
        cmd = Command(raw="git push", stderr_text="fatal: no upstream")
        self.assertEqual(cmd.stderr_text, "fatal: no upstream")

    def test_exit_code_default(self):
        cmd = Command(raw="ls")
        self.assertIsNone(cmd.exit_code)


if __name__ == "__main__":
    unittest.main()
