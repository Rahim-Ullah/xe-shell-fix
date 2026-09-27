"""
Tests for xsf.core.engine - Master 3-tier cascade orchestrator.
"""
import unittest
from unittest.mock import patch, MagicMock

from xsf.core.command import Command
from xsf.core.engine import Engine
from xsf.config import DEFAULT_CONFIG


class TestEngineInit(unittest.TestCase):
    """Tests for Engine initialization."""

    def test_engine_creates_with_default_config(self):
        engine = Engine(DEFAULT_CONFIG)
        self.assertIsNotNone(engine.ai_router)
        self.assertTrue(engine.allow_help)
        self.assertFalse(engine.auto_approve_safe)

    def test_engine_respects_config_overrides(self):
        cfg = {
            "general": {"help_introspection": False, "auto_approve_safe": True},
            "ai": {"enabled": True, "cascade": ["gemini"]},
            "local_llm": {"enabled": False},
        }
        engine = Engine(cfg)
        self.assertFalse(engine.allow_help)
        self.assertTrue(engine.auto_approve_safe)


class TestEngineFindFix(unittest.TestCase):
    """Tests for Engine.find_fix() cascade logic."""

    def setUp(self):
        self.engine = Engine(DEFAULT_CONFIG)

    @patch("xsf.core.engine.run_offline_engine")
    def test_offline_high_confidence_skips_ai(self, mock_offline):
        """When offline returns conf >= 0.85, AI should NOT be called."""
        mock_offline.return_value = ("cd Downloads", 1.0, "Fixed typo")
        cmd = Command(raw="cdd Downloads", shell="bash")

        with patch.object(self.engine.ai_router, "route") as mock_ai:
            result = self.engine.find_fix(cmd)
            mock_ai.assert_not_called()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "cd Downloads")
        self.assertEqual(result[3], "offline")

    @patch("xsf.core.engine.run_offline_engine")
    def test_offline_miss_falls_to_ai(self, mock_offline):
        """When offline returns None, AI router should be called."""
        mock_offline.return_value = None
        cmd = Command(raw="some complex error", shell="bash")

        with patch.object(self.engine.ai_router, "route", return_value=("fixed cmd", 0.9, "AI fix")) as mock_ai:
            result = self.engine.find_fix(cmd)
            mock_ai.assert_called_once()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "fixed cmd")
        self.assertEqual(result[3], "ai")

    @patch("xsf.core.engine.run_offline_engine")
    def test_both_miss_returns_none(self, mock_offline):
        """When both offline and AI return None, find_fix returns None."""
        mock_offline.return_value = None
        cmd = Command(raw="totally unknown gibberish", shell="bash")

        with patch.object(self.engine.ai_router, "route", return_value=None):
            result = self.engine.find_fix(cmd)

        self.assertIsNone(result)

    @patch("xsf.core.engine.run_offline_engine")
    def test_offline_only_flag(self, mock_offline):
        """--offline flag should never call AI."""
        mock_offline.return_value = ("git status", 0.7, "Fuzzy match")
        cmd = Command(raw="gti statsu", shell="bash")

        with patch.object(self.engine.ai_router, "route") as mock_ai:
            result = self.engine.find_fix(cmd, offline_only=True)
            mock_ai.assert_not_called()

        self.assertIsNotNone(result)
        self.assertEqual(result[3], "offline")

    @patch("xsf.core.engine.run_offline_engine")
    def test_ai_only_flag(self, mock_offline):
        """--ai flag should skip offline entirely."""
        cmd = Command(raw="some command", shell="bash")

        with patch.object(self.engine.ai_router, "route", return_value=("fixed", 0.8, "explanation")) as mock_ai:
            result = self.engine.find_fix(cmd, ai_only=True)
            mock_offline.assert_not_called()
            mock_ai.assert_called_once()

        self.assertIsNotNone(result)
        self.assertEqual(result[3], "ai")

    @patch("xsf.core.engine.run_offline_engine")
    def test_low_confidence_offline_still_consults_ai(self, mock_offline):
        """When offline returns conf < 0.85, AI should also be consulted."""
        mock_offline.return_value = ("possible fix", 0.5, "Low confidence")
        cmd = Command(raw="ambiguous command", shell="bash")

        with patch.object(self.engine.ai_router, "route", return_value=("ai fix", 0.9, "Better fix")) as mock_ai:
            result = self.engine.find_fix(cmd)
            mock_ai.assert_called_once()

        # AI fix should win
        self.assertEqual(result[0], "ai fix")
        self.assertEqual(result[3], "ai")


class TestEngineExecuteFlow(unittest.TestCase):
    """Tests for Engine.execute_flow() output and exit codes."""

    def setUp(self):
        self.engine = Engine(DEFAULT_CONFIG)

    @patch("xsf.core.engine.run_offline_engine")
    def test_dry_run_returns_1(self, mock_offline):
        """Dry run should print suggestion but NOT execute."""
        mock_offline.return_value = ("cd Downloads", 1.0, "Fixed typo")
        cmd = Command(raw="cdd Downloads", shell="bash")

        with patch("sys.stderr"), patch("sys.stdout"):
            exit_code = self.engine.execute_flow(cmd, dry_run=True)

        # dry_run always returns non-zero (SafetyGuard.confirm returns False)
        self.assertIn(exit_code, (1, 2))

    @patch("xsf.core.engine.run_offline_engine")
    def test_no_fix_returns_1(self, mock_offline):
        """When no fix is found, exit code should be 1."""
        mock_offline.return_value = None
        cmd = Command(raw="totally unknown", shell="bash")

        with patch.object(self.engine.ai_router, "route", return_value=None):
            with patch("sys.stderr"):
                exit_code = self.engine.execute_flow(cmd)

        self.assertEqual(exit_code, 1)

    def test_already_resolved_removal_returns_0(self):
        """When rm fails because file is already missing, execute_flow prints INFO and returns 0."""
        cmd = Command(
            raw='rm "clf sign.png"',
            stderr_text="rm: cannot remove 'clf sign.png': No such file or directory",
            shell="bash",
        )
        with patch("sys.stderr") as mock_err:
            exit_code = self.engine.execute_flow(cmd)

        self.assertEqual(exit_code, 0)

    def test_already_resolved_missing_on_disk_without_stderr(self):
        """When rm targets a nonexistent file even without captured stderr, execute_flow returns 0."""
        cmd = Command(
            raw='rm "completely_nonexistent_random_file_xyz.txt"',
            stderr_text="",
            shell="bash",
        )
        with patch("sys.stderr"):
            exit_code = self.engine.execute_flow(cmd)

        self.assertEqual(exit_code, 0)

    def test_already_resolved_process_kill(self):
        """When kill fails because process is already dead, execute_flow returns 0."""
        cmd = Command(
            raw="kill 9999",
            stderr_text="bash: kill: (9999) - No such process",
            shell="bash",
        )
        with patch("sys.stderr"):
            exit_code = self.engine.execute_flow(cmd)

        self.assertEqual(exit_code, 0)

    @patch("xsf.core.engine.run_offline_engine")
    def test_futile_identical_fix_rejected(self, mock_offline):
        """If a fix proposes the exact command that just failed, it must be rejected."""
        mock_offline.return_value = ("rm 'clf sign.png'", 0.9, "Identical")
        cmd = Command(raw="rm 'clf sign.png'", stderr_text="some error", shell="bash")

        with patch.object(self.engine.ai_router, "route", return_value=None):
            result = self.engine.find_fix(cmd)

        self.assertIsNone(result)

    @patch("xsf.core.engine.Engine.find_candidates")
    @patch("xsf.ui.selector.choose_candidate")
    def test_multi_candidate_selection_executes_safe_directly(self, mock_choose, mock_find):
        """When user selects a safe candidate via arrow keys, it executes directly without double prompt."""
        mock_find.return_value = [
            ("git status", 0.95, "Fix status", "offline"),
            ("git stash", 0.80, "Stash changes", "offline"),
        ]
        mock_choose.return_value = ("git status", 0.95, "Fix status", "offline")
        cmd = Command(raw="giit stas", shell="bash")

        with patch("sys.stdout") as mock_out:
            exit_code = self.engine.execute_flow(cmd)

        self.assertEqual(exit_code, 0)
        mock_out.write.assert_called_with("git status\n")


if __name__ == "__main__":
    unittest.main()
