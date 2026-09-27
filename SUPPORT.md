# Support

## Where to Get Help

| Need | Go to |
|---|---|
| 🐛 Found a bug | [Open a Bug Report](https://github.com/rahim-ullah/xe-shell-fix/issues/new?template=bug_report.yml) |
| 💡 Have a feature idea | [Open a Feature Request](https://github.com/rahim-ullah/xe-shell-fix/issues/new?template=feature_request.yml) |
| 🔐 Found a security vulnerability | See [`SECURITY.md`](./SECURITY.md) — **do not post publicly** |
| 📖 Usage questions | [`HOWTOUSE.md`](./HOWTOUSE.md) — complete guide from install to advanced use |
| 🤝 Want to contribute | [`CONTRIBUTING.md`](./CONTRIBUTING.md) |
| 💬 General discussion | [GitHub Discussions](https://github.com/rahim-ullah/xe-shell-fix/discussions) |

---

## Before Opening an Issue

Please check:

1. **Read `HOWTOUSE.md`** — it covers installation, shell hook setup, API key configuration, and common troubleshooting scenarios.
2. **Search existing issues** — your problem may already be reported or answered.
3. **Run `xsf --version`** — include this in your report.
4. **Try `xsf --offline`** — if it works offline but not with AI, the problem is likely your API key or provider configuration.

---

## Diagnostic Commands

```bash
# Check version
xsf --version

# Check current configuration (masks API keys)
xsf config --list

# Test offline engine only (no network)
xsf --offline "your_failed_command"

# Test with verbose dry-run (no execution)
xsf --dry-run "your_failed_command"

# Bypass AI cache and force fresh call
xsf --no-cache "your_failed_command"
```

---

> **Note:** The GitHub issue tracker is for bugs and feature requests. It is not a general support forum. For open-ended questions, use [GitHub Discussions](https://github.com/rahim-ullah/xe-shell-fix/discussions).
