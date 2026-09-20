"""
Tests for xsf.ai.router - Multi-provider AI fallback router.
"""
import unittest
from unittest.mock import patch, MagicMock

from xsf.core.command import Command
from xsf.ai.router import AIRouter
from xsf.ai.providers.base import ProviderError
from xsf.config import DEFAULT_CONFIG


class TestAIRouterInit(unittest.TestCase):
    """Tests for AIRouter initialization."""

    def test_router_creates_all_providers(self):
        router = AIRouter(DEFAULT_CONFIG)
        self.assertIn("groq", router.providers)
        self.assertIn("cerebras", router.providers)
        self.assertIn("gemini", router.providers)
        self.assertIn("openrouter", router.providers)
        self.assertIn("grok", router.providers)
        self.assertIn("openai", router.providers)
        self.assertIn("ollama", router.providers)

    def test_providers_unconfigured_by_default(self):
        """Default config has empty keys, so providers should be unconfigured."""
        router = AIRouter(DEFAULT_CONFIG)
        self.assertFalse(router.providers["groq"].is_configured())
        self.assertFalse(router.providers["gemini"].is_configured())


class TestAIRouterRouting(unittest.TestCase):
    """Tests for AIRouter.route() cascade logic."""

    def test_disabled_ai_returns_none(self):
        cfg = dict(DEFAULT_CONFIG)
        cfg["ai"] = dict(DEFAULT_CONFIG["ai"])
        cfg["ai"]["enabled"] = False
        router = AIRouter(cfg)
        cmd = Command(raw="test", shell="bash")
        self.assertIsNone(router.route(cmd))

    @patch("xsf.ai.router.AICache")
    def test_cache_hit_returns_cached(self, mock_cache_cls):
        """If cache has a valid entry, return it without calling providers."""
        mock_cache_cls.get.return_value = {
            "command": "git status",
            "confidence": 0.95,
            "explanation": "Fixed typo",
        }
        router = AIRouter(DEFAULT_CONFIG)
        cmd = Command(raw="gti statsu", shell="bash")

        result = router.route(cmd)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "git status")
        self.assertIn("cached", result[2])

    @patch("xsf.ai.router.AICache")
    def test_skip_cache_flag(self, mock_cache_cls):
        """skip_cache=True should bypass the cache."""
        mock_cache_cls.get.return_value = {
            "command": "cached result",
            "confidence": 0.9,
            "explanation": "Cached",
        }
        router = AIRouter(DEFAULT_CONFIG)
        cmd = Command(raw="test", shell="bash")

        # With skip_cache, even though cache has data, it should try providers
        # Since no providers are configured, it will return None
        result = router.route(cmd, skip_cache=True)
        mock_cache_cls.get.assert_not_called()

    def test_no_configured_providers_returns_none(self):
        """With no API keys configured, route should return None."""
        router = AIRouter(DEFAULT_CONFIG)
        cmd = Command(raw="broken command", shell="bash")
        result = router.route(cmd, skip_cache=True)
        self.assertIsNone(result)

    @patch("xsf.ai.router.AICache")
    def test_provider_error_cascades_to_next(self, mock_cache_cls):
        """If a provider raises ProviderError, router should try the next one."""
        mock_cache_cls.get.return_value = None

        cfg = dict(DEFAULT_CONFIG)
        cfg["ai"] = dict(DEFAULT_CONFIG["ai"])
        cfg["ai"]["cascade"] = ["groq", "gemini"]

        router = AIRouter(cfg)

        # Mock groq to fail, gemini to succeed
        router.providers["groq"] = MagicMock()
        router.providers["groq"].is_configured.return_value = True
        router.providers["groq"].fix.side_effect = ProviderError("Rate limited")

        router.providers["gemini"] = MagicMock()
        router.providers["gemini"].is_configured.return_value = True
        router.providers["gemini"].fix.return_value = ("fixed cmd", "explanation", 0.9)

        cmd = Command(raw="test", shell="bash")

        with patch("sys.stderr"):
            result = router.route(cmd, skip_cache=True)

        self.assertIsNotNone(result)
        self.assertEqual(result[0], "fixed cmd")
        self.assertIn("Gemini", result[2])


class TestAIProviderBase(unittest.TestCase):
    """Tests for BaseProvider.parse_json_response()."""

    def test_parse_clean_json(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '{"fixed_command": "git status", "explanation": "Fixed typo", "confidence": 0.95, "destructive": false}'
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertEqual(cmd, "git status")
        self.assertEqual(exp, "Fixed typo")
        self.assertAlmostEqual(conf, 0.95)
        self.assertFalse(dest)

    def test_parse_markdown_wrapped_json(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '```json\n{"fixed_command": "ls -la", "explanation": "Added flags", "confidence": 0.8, "destructive": false}\n```'
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertEqual(cmd, "ls -la")
        self.assertAlmostEqual(conf, 0.8)

    def test_parse_destructive_flag(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '{"fixed_command": "rm -rf /tmp", "explanation": "Dangerous", "confidence": 0.9, "destructive": true}'
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertTrue(dest)

    def test_parse_empty_fixed_command(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '{"fixed_command": "", "explanation": "No fix", "confidence": 0.0, "destructive": false}'
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertEqual(cmd, "")

    def test_parse_missing_fields_defaults(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '{"fixed_command": "ls"}'
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertEqual(cmd, "ls")
        self.assertEqual(exp, "")
        self.assertAlmostEqual(conf, 0.5)
        self.assertFalse(dest)


if __name__ == "__main__":
    unittest.main()
