# 01 — Groq LPU Free API Key Setup Guide

**Groq** is the primary cloud provider in `xsf`'s cascade because its Language Processing Unit (LPU) delivers responses in **~200ms** — fast enough to feel native in your terminal.

* **Cost**: 100% Free developer tier (no credit card required)
* **Allowance**: **14,400 requests/day** and **30 requests/minute**
* **Default Model**: `qwen/qwen3.8-27b` (automatic fallback to `llama3-8b-8192`, `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`)

---

## Step 1: Generate Your Free Groq API Key

1. Open **[console.groq.com/keys](https://console.groq.com/keys)** in your browser.
2. Sign in with Google or GitHub.
3. Click **"Create API Key"**, name it `xsf-terminal`, and copy the generated key (it starts with `gsk_`).

---

## Step 2: Attach the Key to `xsf`

Choose any of the three methods below:

### Option A: One-Line CLI (Fastest)
```bash
xsf key set groq gsk_YOUR_KEY_HERE --test
```

### Option B: Interactive Setup / Config Menu
```bash
xsf config
# Press [1] -> Paste your gsk_... key -> Press [S] to save
```

### Option C: Multiple Backup Keys (Zero Rate-Limit Interruption)
If you have two Groq accounts, attach both keys separated by a comma. If Key #1 hits a 30 RPM burst limit, `xsf` automatically rotates to Key #2 without failing:
```bash
xsf key set groq "gsk_PRIMARY_KEY,gsk_BACKUP_KEY" --test
```

---

## Switching or Removing Your Groq Key Later

* **Switch to a new account key**:
  ```bash
  xsf key set groq gsk_NEW_ACCOUNT_KEY --test
  ```
* **Remove key**:
  ```bash
  xsf key remove groq
  ```
