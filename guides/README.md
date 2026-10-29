# 🔑 `xsf` API Key Guides & Power Switch Handbook

Every user of `xe-shell-fix` (`xsf`) connects **their own personal API keys** (Bring-Your-Own-Key). Your keys are stored locally on your machine at `~/.shellfix/config.toml` with strict owner-only permissions (`0600` on Linux/macOS, exclusive user ACL on Windows) and are never shared.

> 📦 **Need to install `xsf` or fix an OS installation error (like Ubuntu's `externally-managed-environment`)?**
> See the dedicated **[OS Installation & Troubleshooting Guides (`install_guides/`)](../install_guides/README.md)**.

---

## 📚 Step-by-Step Guides Index

| Guide | What It Covers | Cost & Daily Quota |
| :--- | :--- | :--- |
| **[01 — Groq LPU Setup](01-GROQ-LPU-GUIDE.md)** | Getting & attaching a `gsk_...` key for ~200ms LPU inference | **100% Free** (14,400 req/day, 30 RPM) |
| **[02 — Google Gemini Setup](02-GOOGLE-GEMINI-GUIDE.md)** | Getting & attaching an `AIza...` key from Google AI Studio | **100% Free** (1,500 req/day, 15 RPM) |
| **[03 — OpenRouter & Cerebras](03-OPENROUTER-AND-CEREBRAS-GUIDE.md)** | Free `:free` models on OpenRouter (`sk-or-...`) & Cerebras (`csk-...`) | **Free Tiers Available** |
| **[04 — Grok, OpenAI & Local Ollama](04-GROK-OPENAI-AND-LOCAL-OLLAMA.md)** | Opt-in paid keys (xAI Grok, OpenAI, DeepSeek) & 100% offline Ollama | **Opt-In / 100% Local Free** |
| **[05 — Power Switch & Key Rotation](05-POWER-SWITCH-AND-KEY-ROTATION.md)** | Switching accounts, multi-key backup rotation, cooldown guards & Power Modes | **Built-in Engine Control** |

---

## ⚡ Quick-Start Commands

```bash
# 1. Run the interactive post-install Setup Wizard (Power Mode + Keys + Shell Hook)
xsf setup

# 2. Check current Power Switch mode, attached keys, and live rate-limit health
xsf power status

# 3. Attach or switch a provider key in one command (auto-strips quotes & tests connection)
xsf key set groq gsk_YOUR_KEY_HERE --test
xsf key set gemini AIzaSyYOUR_KEY_HERE --test

# 4. Flip the Power Switch anytime
xsf power offline   # 100% Offline heuristics only (uses zero cloud quota)
xsf power hybrid    # Default: Instant Offline first -> Cloud AI fallback
xsf power ai        # Force Cloud/Local AI diagnosis directly
xsf power off       # Pause xsf completely
xsf power reset     # Clear all rate-limit cooldowns / circuit breakers
```

---

```python
__AUTHOR__ = __XE__
__PROFILE__ = __GitHub.com/Rahim-Ullah__
__ROLE__ = __DEVELOPER__
```
