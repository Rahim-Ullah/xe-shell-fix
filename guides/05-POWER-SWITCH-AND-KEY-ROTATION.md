# 05 — Power Switch, Account Switching & Rate-Limit Protection

`xsf` includes a dedicated **Power Switch** and an automatic **Circuit-Breaker Health Tracker** so you never hit surprise rate-limit stalls or waste your personal API quotas.

---

## ⚡ 1. The `xsf power` Switch

Control how `xsf` operates at any moment:

| Command | Mode | Behavior |
| :--- | :--- | :--- |
| `xsf power hybrid` *(or `on`)* | **HYBRID** *(Default)* | Runs `<5ms` offline rules first; only calls AI when offline confidence `<85%`. |
| `xsf power offline` | **OFFLINE-ONLY** | **100% offline heuristics & `--help` parser**. Consumes **0 API tokens** and makes **0 network calls**. |
| `xsf power ai` | **AI-ONLY** | Bypasses offline heuristics and queries your AI cascade directly. |
| `xsf power off` | **OFF** | Temporarily pauses `xsf` until you run `xsf power on`. |
| `xsf power status` | **Dashboard** | Displays active Power Mode, masked keys, backup key counts, and live cooldown status. |
| `xsf power reset` | **Reset Circuit Breakers** | Immediately clears all rate-limit (`429`) and quota (`402`) cooldowns. |

---

## 🔄 2. Switching Accounts & Multi-Key Rotation

### Switching to Another Account Key
Whenever you want to switch from one account's API key to another:
```bash
xsf key set gemini AIzaSyYOUR_SECOND_ACCOUNT_KEY --test
```
`xsf` automatically:
1. Strips accidental quotes (`"..."`), spaces, or `Bearer ` prefixes.
2. Validates the key format and length.
3. Resets any rate-limit cooldowns for that provider.
4. Writes `~/.shellfix/config.toml` with strict `0600` owner-only permissions.

### Attaching Backup Keys for Automatic Rotation
You can attach **2 or more keys** per provider separated by a comma:
```bash
xsf key set groq "gsk_ACCOUNT_1_KEY,gsk_ACCOUNT_2_KEY"
```
If Account 1 hits a `429` rate limit, `xsf` places Account 1 on a 45-second cooldown and **instantly rotates to Account 2** on the very same request.

---

## 🛡️ 3. How Rate-Limit & Error Protection Works (`ProviderHealthTracker`)

To prevent terminal lag when a provider is throttled or out of credits, `xsf` tracks key health in `~/.shellfix/provider_health.json`:

* **HTTP `429` (Rate Limit)**: Key enters a **45-second cooldown**; requests immediately route to your backup key or the next provider in the cascade.
* **HTTP `402` (Credits / Billing Required)**: Key enters a **30-minute cooldown** so subsequent commands never stall on an unpaid endpoint.
* **HTTP `401` / `403` (Invalid/Revoked Key)**: Key is bypassed until you update it via `xsf key set` or run `xsf power reset`.
* **7-Day SHA-256 Query Cache**: Repeated errors are served in `0.8ms` from `~/.shellfix/ai_cache.json` without touching your API quota.
