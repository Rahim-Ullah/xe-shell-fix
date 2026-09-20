"""
Unit tests for dynamic multi-format help parser (xsf.offline.help_parser).
"""
import unittest
from unittest.mock import patch

from xsf.core.command import Command
from xsf.offline.help_parser import extract_flags_from_text, correct_flag_typos

SAMPLE_ARGPARSE_HELP = """
usage: tool [-h] [-v] [--recursive] [--dry-run] [--output FILE]

options:
  -h, --help            show this help message and exit
  -v, --verbose         increase output verbosity
  --recursive           recursively scan subdirectories
  --dry-run             simulate execution without making changes
  -o, --output FILE     destination path
"""

SAMPLE_COBRA_HELP = """
Usage:
  myctl run [flags]

Flags:
  -d, --detach          Run container in background and print container ID
  -i, --interactive     Keep STDIN open even if not attached
  -t, --tty             Allocate a pseudo-TTY
      --restart string  Restart policy to apply when a container exits
  -h, --help            help for run
"""

SAMPLE_POSIX_HELP = """
Usage: util [options]
  -a, --all        do not ignore entries starting with .
  -l               use a long listing format
  -R, --recursive  list subdirectories recursively
"""


class TestHelpParser(unittest.TestCase):
    def test_extract_argparse_flags(self):
        flags = extract_flags_from_text(SAMPLE_ARGPARSE_HELP)
        self.assertIn("--verbose", flags)
        self.assertIn("-v", flags)
        self.assertIn("--recursive", flags)
        self.assertIn("--dry-run", flags)
        self.assertIn("--output", flags)

    def test_extract_cobra_flags(self):
        flags = extract_flags_from_text(SAMPLE_COBRA_HELP)
        self.assertIn("--detach", flags)
        self.assertIn("-d", flags)
        self.assertIn("--interactive", flags)
        self.assertIn("--restart", flags)

    def test_extract_posix_flags(self):
        flags = extract_flags_from_text(SAMPLE_POSIX_HELP)
        self.assertIn("--all", flags)
        self.assertIn("-a", flags)
        self.assertIn("-l", flags)
        self.assertIn("--recursive", flags)

    @patch("xsf.offline.help_parser.get_command_flags")
    def test_correct_flag_typo(self, mock_flags):
        # Mock available flags for `git push`
        mock_flags.return_value = ["--force", "--set-upstream", "--all", "--tags", "--dry-run", "--verbose"]
        
        cmd = Command(raw="git push origin main --froce", shell="bash")
        result = correct_flag_typos(cmd)
        self.assertIsNotNone(result)
        fixed, conf, exp = result
        self.assertEqual(fixed, "git push origin main --force")
        self.assertIn("--force", exp)


if __name__ == "__main__":
    unittest.main()
