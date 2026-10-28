"""
Unit tests for configuration loader and fallback parser (xsf.config).
"""
import os
import unittest
from unittest.mock import patch
from xsf.config import _simple_toml_parse, load_config


class TestConfig(unittest.TestCase):
    def test_simple_toml_parser(self):
        sample_toml = """
        # Comments
        [general]
        auto_approve_safe = true
        help_introspection = false
        aliases = ["xsf", "xefix"]

        [ai]
        gemini_model = "gemini-2.5-flash"
        """
        parsed = _simple_toml_parse(sample_toml)
        self.assertTrue(parsed["general"]["auto_approve_safe"])
        self.assertFalse(parsed["general"]["help_introspection"])
        self.assertEqual(parsed["general"]["aliases"], ["xsf", "xefix"])
        self.assertEqual(parsed["ai"]["gemini_model"], "gemini-2.5-flash")

    def test_inline_comments_and_escaping(self):
        sample = """
        [general]
        auto_approve_safe = false # disable auto
        threshold = 0.85 # confidence cutoff
        secret = "my#secret#key" # inline comment
        """
        parsed = _simple_toml_parse(sample)
        self.assertFalse(parsed["general"]["auto_approve_safe"])
        self.assertEqual(parsed["general"]["threshold"], 0.85)
        self.assertEqual(parsed["general"]["secret"], "my#secret#key")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"})
    def test_env_var_override(self):
        cfg = load_config()
        self.assertEqual(cfg["ai"]["gemini_api_key"], "test-key-123")

    def test_secure_config_permissions(self):
        from tempfile import NamedTemporaryFile
        from pathlib import Path
        from xsf.config import secure_config_permissions
        with NamedTemporaryFile(delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            # Should run without error cross-platform
            secure_config_permissions(tmp_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_sanitize_and_validate_api_key(self):
        from xsf.config import sanitize_api_key, parse_key_list, validate_api_key

        # Strips Bearer prefix, quotes, and spaces
        cleaned = sanitize_api_key('  "Bearer gsk_1234567890abcdef" , \'gsk_backup9876543210\' ')
        self.assertEqual(cleaned, "gsk_1234567890abcdef,gsk_backup9876543210")
        self.assertEqual(parse_key_list(cleaned), ["gsk_1234567890abcdef", "gsk_backup9876543210"])

        # Valid Groq key
        ok, key_str, msg = validate_api_key("groq", "gsk_1234567890abcdef")
        self.assertTrue(ok)
        self.assertEqual(key_str, "gsk_1234567890abcdef")

        # Too short key rejected
        ok_short, _, _ = validate_api_key("gemini", "short")
        self.assertFalse(ok_short)

        # Unknown provider rejected
        ok_unk, _, _ = validate_api_key("unknown_prov", "some_long_key_123456")
        self.assertFalse(ok_unk)

    @patch("xsf.ui.config_tui.save_config")
    @patch("xsf.ui.config_tui.load_config")
    def test_power_and_key_cli_handlers(self, mock_load, mock_save):
        from xsf.config import DEFAULT_CONFIG
        from xsf.ui.config_tui import handle_power_cli, handle_key_cli
        import io

        cfg = {
            "general": dict(DEFAULT_CONFIG["general"]),
            "ai": dict(DEFAULT_CONFIG["ai"]),
            "local_llm": dict(DEFAULT_CONFIG["local_llm"]),
        }
        mock_load.return_value = cfg

        with patch("sys.stdout", io.StringIO()):
            rc = handle_power_cli(["offline"])
            self.assertEqual(rc, 0)
            self.assertEqual(cfg["general"]["power_mode"], "offline")
            self.assertFalse(cfg["ai"]["enabled"])

            rc2 = handle_power_cli(["hybrid"])
            self.assertEqual(rc2, 0)
            self.assertEqual(cfg["general"]["power_mode"], "hybrid")
            self.assertTrue(cfg["ai"]["enabled"])

            rc3 = handle_key_cli(["set", "groq", "gsk_1234567890abcdef"])
            self.assertEqual(rc3, 0)
            self.assertEqual(cfg["ai"]["groq_api_key"], "gsk_1234567890abcdef")

            rc4 = handle_key_cli(["remove", "groq"])
            self.assertEqual(rc4, 0)
            self.assertEqual(cfg["ai"]["groq_api_key"], "")


if __name__ == "__main__":
    unittest.main()
