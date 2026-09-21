# Contributing to xe-shell-fix (`xsf`)

Thank you for considering contributing to `xsf`! This document will help you get started.

---

## 🏗️ Development Setup

```bash
# 1. Clone the repository
git clone https://github.com/rahim-ullah/xe-shell-fix.git
cd xe-shell-fix

# 2. Create a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 4. Run tests
python -m pytest tests/ -v
```

---

## 📝 Adding a New Offline Rule Plugin

Rules are the **superpower** of `xsf`. Every new rule you add runs in <5ms and requires zero network calls.

### Step 1: Create or find the right file

Rules live in `xsf/offline/rules/`. Choose the right file based on the tool:
- `git_rules.py` — Git-related fixes
- `python_rules.py` — Python, pip, venv fixes
- `package_rules.py` — npm, yarn, cargo, go fixes
- `docker_rules.py` — Docker and container fixes
- `shell_rules.py` — Shell builtins, typos, permissions
- `stderr_rules.py` — Stderr-driven error recovery
- `env_rules.py` — Environment and installation errors
- `ssh_net_rules.py` — SSH and network errors

Or create a new file for a new tool category.

### Step 2: Subclass `Rule`

```python
from typing import Optional, Tuple
from xsf.core.command import Command
from xsf.offline.rules.base import Rule

class MyNewRule(Rule):
    """Describe what error pattern this rule catches."""
    name = "my_new_rule"
    priority = 20  # Lower = higher priority (checked first)

    def match(self, cmd: Command) -> bool:
        # Return True if this rule applies to the command
        return cmd.tokens and cmd.tokens[0] == "mytool"

    def get_new_command(self, cmd: Command) -> Optional[Tuple[str, float, str]]:
        # Return: (fixed_command, confidence, explanation)
        # Or None if you can't generate a fix
        return "mytool --correct-syntax", 0.95, "Fixed mytool syntax"
```

### Step 3: Register it

Add your rule to `xsf/offline/rules/__init__.py`:

```python
from xsf.offline.rules.my_file import MyNewRule

ALL_RULES: List[Rule] = sorted([
    # ... existing rules ...
    MyNewRule(),
], key=lambda r: r.priority)
```

### Step 4: Write tests

Add tests in `tests/test_offline_rules.py` or `tests/test_stderr_rules.py`:

```python
def test_my_new_rule(self):
    cmd = Command(raw="mytool --wrong-flag", shell="bash")
    result = evaluate_rules(cmd)
    self.assertIsNotNone(result)
    self.assertIn("--correct-syntax", result[0])
```

---

## 🤖 Adding a New AI Provider

1. Create `xsf/ai/providers/my_provider.py`
2. Subclass `BaseProvider` from `xsf.ai.providers.base`
3. Implement `is_configured()` and `fix(cmd)`
4. Register it in `xsf/ai/router.py`
5. Add config fields in `xsf/config.py`

---

## 🧪 Running Tests

```bash
# Run all tests with verbose output
python -m pytest tests/ -v --tb=short

# Run a specific test file
python -m pytest tests/test_safety.py -v

# Run a specific test
python -m pytest tests/test_safety.py::TestSafetyGuard::test_destructive_patterns_detected -v
```

---

## 📋 Pull Request Guidelines

1. **Write tests** for any new rules or functionality
2. **Run the full test suite** before submitting
3. **Follow existing code style** (type hints, docstrings, imports)
4. **Keep PRs focused** — one feature or fix per PR
5. **Update documentation** if adding new features or changing behavior

---

## 🐛 Reporting Issues

When reporting bugs, please include:
- Your OS and shell (e.g., Windows 11 + Git Bash)
- Python version (`python --version`)
- The exact command that failed
- The error output (stderr)
- What `xsf` suggested vs. what you expected

---

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
