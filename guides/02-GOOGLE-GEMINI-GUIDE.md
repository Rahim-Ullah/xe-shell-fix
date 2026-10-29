# 02 — Google Gemini Free API Key Setup Guide

**Google Gemini** provides a generous free developer tier through Google AI Studio and acts as `xsf`'s high-context reasoning engine in the cascade.

* **Cost**: 100% Free tier in Google AI Studio (no billing required for free tier)
* **Allowance**: **1,500 requests/day**, **15 requests/minute**, **1M tokens/minute**
* **Supported Key Formats**: Both Google AI Studio keys (`AIza...`) and Google Cloud / Vertex AI Express keys (`AQ....`)
* **Default Model**: `gemini-flash-latest` (automatic fallback across `gemini-2.5-flash`, `gemini-2.0-flash`, and `gemini-flash-lite-latest`)

---

## Step 1: Generate Your Free Gemini Key

1. Visit **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)**.
2. Sign in with your personal Google account.
3. Click **"Create API key"** and copy the key string (it starts with `AIza`).

---

## Step 2: Attach the Key to `xsf`

### Option A: One-Line CLI (Recommended)
```bash
xsf key set gemini AIzaSyYOUR_KEY_HERE --test
```

### Option B: Interactive Menu
```bash
xsf config
# Press [2] -> Paste your AIza... key -> Press [S] to save
```

### Option C: Multi-Account Rotation
Attach keys from multiple Google accounts separated by a comma so `xsf` automatically rotates if one hits the 15 RPM burst cap:
```bash
xsf key set gemini "AIzaSyACCOUNT_1_KEY,AIzaSyACCOUNT_2_KEY" --test
```

---

## Switching or Removing Your Gemini Key Later

* **Switch Google accounts**:
  ```bash
  xsf key set gemini AIzaSyNEW_ACCOUNT_KEY --test
  ```
* **Remove key**:
  ```bash
  xsf key remove gemini
  ```
