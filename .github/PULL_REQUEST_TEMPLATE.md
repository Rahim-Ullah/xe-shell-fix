## Description

<!-- Briefly describe what this PR does and why. -->

## Type of Change

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 🔥 New offline rule / vocabulary entry
- [ ] 🤖 New AI provider
- [ ] 🔐 Security fix
- [ ] 🔨 Refactor (no functional change)
- [ ] 📖 Documentation update
- [ ] 🧪 Tests only

---

## Testing

- [ ] I ran `python -m pytest tests/ -v` and all tests pass
- [ ] I added new tests that cover the changes I made
- [ ] I verified the fix/feature manually in a shell (specify which shell/OS below)

**Tested on:**
- OS: <!-- e.g. Windows 11, Ubuntu 24.04, macOS 15 -->
- Shell: <!-- e.g. Git Bash (MINGW64), PowerShell 7.4, Zsh -->
- Python: <!-- e.g. 3.11.9 -->

---

## Security Checklist

> xe-shell-fix executes shell commands on behalf of users. All contributors **must** review the items below before submitting.

- [ ] My changes do not weaken or bypass the safety confirmation gate in `xsf/core/safety.py` or `xsf/core/engine.py`
- [ ] My changes do not enable silent execution of any command without explicit user approval
- [ ] I have NOT committed any API keys, tokens, passwords, or secrets
- [ ] If my changes touch shell hooks (`xsf/hooks/`), I verified that `eval` is not reachable without user confirmation
- [ ] If my changes touch AI providers (`xsf/ai/`), the request payload contains only command + stderr (no credentials, no filesystem data)
- [ ] If my changes involve subprocesses, I used `subprocess.run(list_of_args)` — NOT `shell=True`

---

## Documentation

- [ ] I updated docstrings / inline comments where relevant
- [ ] If this adds a new feature, `README.md` or `HOWTOUSE.md` has been updated
- [ ] If this adds a new offline rule, `CHANGELOG.md` has been updated

---

## Related Issues

Closes #<!-- issue number if applicable -->
