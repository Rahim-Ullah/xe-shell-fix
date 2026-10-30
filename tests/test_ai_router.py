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

    @patch("xsf.ai.router.AICache")
    @patch("xsf.ai.router.ProviderHealthTracker.save")
    def test_multi_key_rotation_on_rate_limit(self, _mock_save, mock_cache_cls):
        """If primary key returns 429, router rotates to backup key on the same provider."""
        from xsf.ai.router import ProviderHealthTracker
        ProviderHealthTracker.reset()
        mock_cache_cls.get.return_value = None

        cfg = {
            "general": dict(DEFAULT_CONFIG["general"]),
            "ai": dict(DEFAULT_CONFIG["ai"]),
            "local_llm": dict(DEFAULT_CONFIG["local_llm"]),
        }
        cfg["ai"]["groq_api_key"] = "gsk_key_one_12345,gsk_key_two_67890"
        router = AIRouter(cfg)

        prov = router.providers["groq"]
        call_keys = []

        def fake_fix(cmd):
            call_keys.append(prov.api_key)
            if prov.api_key == "gsk_key_one_12345":
                raise ProviderError("Rate limit exceeded", 429)
            return ("git status", "Fixed via backup key", 0.95)

        prov.fix = fake_fix
        res = router.route(Command(raw="gti statsu"), skip_cache=True)
        self.assertIsNotNone(res)
        self.assertEqual(res[0], "git status")
        self.assertEqual(call_keys, ["gsk_key_one_12345", "gsk_key_two_67890"])
        # Key one should now be in cooldown, key two should be healthy
        cooling1, _ = ProviderHealthTracker.is_cooling_down("groq", "gsk_key_one_12345")
        cooling2, _ = ProviderHealthTracker.is_cooling_down("groq", "gsk_key_two_67890")
        self.assertTrue(cooling1)
        self.assertFalse(cooling2)
        ProviderHealthTracker.reset()


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
        self.assertAlmostEqual(conf, 0.0)
        self.assertFalse(dest)

    def test_parse_missing_fields_defaults(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '{"fixed_command": "ls"}'
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertEqual(cmd, "ls")
        self.assertEqual(exp, "")
        self.assertAlmostEqual(conf, 0.5)
        self.assertFalse(dest)

    def test_parse_question_answer_overrides_summary(self):
        from xsf.ai.providers.base import BaseProvider
        raw = ('{"fixed_command": "cd ~/Downloads", "explanation": "Changes directory", "confidence": 0.95, '
               '"destructive": false, "answer": "cd changes the current directory.\\ncd ..  - go up one level"}')
        cmd, exp, conf, dest = BaseProvider.parse_json_response(raw)
        self.assertEqual(cmd, "cd ~/Downloads")
        self.assertIn("cd ..  - go up one level", exp)
        self.assertEqual(exp.splitlines()[0], "cd changes the current directory.")

    def test_parse_empty_answer_keeps_explanation(self):
        from xsf.ai.providers.base import BaseProvider
        raw = '{"fixed_command": "git status", "explanation": "Fixed typo", "confidence": 0.9, "answer": ""}'
        _, exp, _, _ = BaseProvider.parse_json_response(raw)
        self.assertEqual(exp, "Fixed typo")

    def test_redact_sensitive_data(self):
        from xsf.ai.router import redact_sensitive_data
        sample_bearer = "curl -H 'Authorization: Bearer abcdef1234567890xyz' https://api.com"
        self.assertIn("[REDACTED_TOKEN]", redact_sensitive_data(sample_bearer))
        self.assertNotIn("abcdef1234567890xyz", redact_sensitive_data(sample_bearer))

        sample_uri = "psql postgresql://admin:secretpassword123@db.internal:5432/main"
        self.assertIn("postgresql://admin:[REDACTED]@db.internal:5432/main", redact_sensitive_data(sample_uri))

        sample_gh = "git clone https://ghp_012345678901234567890123456789012345@github.com/org/repo"
        self.assertIn("[REDACTED_GH_TOKEN]", redact_sensitive_data(sample_gh))


if __name__ == "__main__":
    unittest.main()
