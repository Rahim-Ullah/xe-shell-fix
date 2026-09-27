"""
Unit tests for user custom rules loader (xsf.offline.rules.user_rules).
"""
from pathlib import Path
import tempfile
import unittest

from xsf.core.command import Command
from xsf.offline.rules.base import Rule
from xsf.offline.rules.user_rules import load_user_rules, FunctionRuleAdapter


class TestUserRulesLoader(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.rules_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_empty_rules_dir(self):
        rules = load_user_rules(rules_dir=self.rules_dir, force_reload=True)
        self.assertEqual(rules, [])

    def test_class_based_user_rule(self):
        rule_code = """
from xsf.offline.rules.base import Rule

class CustomGreetRule(Rule):
    name = "custom_greet"
    priority = 2
    requires_output = False

    def match(self, cmd):
        return cmd.raw.strip() == "helo"

    def get_new_command(self, cmd):
        return "hello", 1.0, "Fixed typo helo -> hello"
"""
        rule_file = self.rules_dir / "greet_rule.py"
        rule_file.write_text(rule_code, encoding="utf-8")

        rules = load_user_rules(rules_dir=self.rules_dir, force_reload=True)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, "custom_greet")
        self.assertEqual(rules[0].priority, 2)
        self.assertFalse(rules[0].requires_output)

        cmd = Command(raw="helo")
        self.assertTrue(rules[0].match(cmd))
        fixed, conf, exp = rules[0].get_new_command(cmd)
        self.assertEqual(fixed, "hello")

    def test_thefuck_function_based_rule(self):
        # A standard thefuck-style rule with match() and get_new_command() functions
        rule_code = """
def match(command):
    return command.raw.startswith("kctx")

def get_new_command(command):
    return command.raw.replace("kctx", "kubectx")

priority = 10
requires_output = False
"""
        rule_file = self.rules_dir / "kubectx.py"
        rule_file.write_text(rule_code, encoding="utf-8")

        rules = load_user_rules(rules_dir=self.rules_dir, force_reload=True)
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].name, "kubectx")
        self.assertEqual(rules[0].priority, 10)
        self.assertFalse(rules[0].requires_output)

        cmd = Command(raw="kctx prod")
        self.assertTrue(rules[0].match(cmd))
        candidates = rules[0].get_candidates(cmd)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0], "kubectx prod")

    def test_broken_user_rule_isolation(self):
        # Syntax error in user rule should not crash the engine
        broken_code = "this is total invalid python syntax !!!!"
        rule_file = self.rules_dir / "broken.py"
        rule_file.write_text(broken_code, encoding="utf-8")

        rules = load_user_rules(rules_dir=self.rules_dir, force_reload=True)
        self.assertEqual(rules, [])


if __name__ == "__main__":
    unittest.main()
