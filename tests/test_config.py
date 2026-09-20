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

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-123"})
    def test_env_var_override(self):
        cfg = load_config()
        self.assertEqual(cfg["ai"]["gemini_api_key"], "test-key-123")


if __name__ == "__main__":
    unittest.main()
