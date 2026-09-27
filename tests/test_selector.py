"""
Unit tests for interactive multi-candidate selector (xsf.ui.selector).
"""
import io
import unittest
from unittest.mock import patch

from xsf.ui.selector import choose_candidate, render_diff


class TestSelector(unittest.TestCase):
    def test_empty_candidates_returns_none(self):
        self.assertIsNone(choose_candidate([]))

    def test_single_candidate_returns_immediately(self):
        cand = ("git status", 1.0, "Typo fix", "offline")
        result = choose_candidate([cand])
        self.assertEqual(result, cand)

    def test_multi_candidate_non_tty_default_enter(self):
        cands = [
            ("git push -u origin main", 1.0, "Set upstream", "offline"),
            ("git push --force origin main", 0.8, "Force push", "ai"),
        ]
        # Simulate Enter (empty string) in non-interactive mode
        with patch("sys.stdin", io.StringIO("\n")), patch("sys.stderr", io.StringIO()):
            chosen = choose_candidate(cands)
            self.assertEqual(chosen, cands[0])

    def test_multi_candidate_non_tty_select_number(self):
        cands = [
            ("git push -u origin main", 1.0, "Set upstream", "offline"),
            ("git push --force origin main", 0.8, "Force push", "ai"),
        ]
        # Simulate selecting "2"
        with patch("sys.stdin", io.StringIO("2\n")), patch("sys.stderr", io.StringIO()):
            chosen = choose_candidate(cands)
            self.assertEqual(chosen, cands[1])

    def test_multi_candidate_non_tty_cancel(self):
        cands = [
            ("git push -u origin main", 1.0, "Set upstream", "offline"),
            ("git push --force origin main", 0.8, "Force push", "ai"),
        ]
        # Simulate cancel "n"
        with patch("sys.stdin", io.StringIO("n\n")), patch("sys.stderr", io.StringIO()):
            chosen = choose_candidate(cands)
            self.assertIsNone(chosen)

    def test_render_diff(self):
        old_tokens = ["gti", "push"]
        new_tokens = ["git", "push"]
        diff = render_diff(old_tokens, new_tokens)
        self.assertIn("gti", diff)
        self.assertIn("git", diff)
        self.assertIn("push", diff)


if __name__ == "__main__":
    unittest.main()
