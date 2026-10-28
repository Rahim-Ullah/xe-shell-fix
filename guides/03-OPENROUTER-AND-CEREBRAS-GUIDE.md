# 03 — OpenRouter & Cerebras Setup Guide

Configuring **OpenRouter** and/or **Cerebras** gives `xsf` deep third- and fourth-layer fallback protection so your terminal assistant never goes offline even during major cloud outages.

---

## Part A: OpenRouter Free Models (`sk-or-...`)

OpenRouter provides access to free community-hosted models (`meta-llama/llama-3.3-70b-instruct:free`, `qwen/qwen-2.5-coder-32b-instruct:free`, `google/gemini-2.0-flash-exp:free`).

1. Go to **[openrouter.ai/keys](https://openrouter.ai/keys)** and sign in.
2. Click **"Create Key"**, name it `xsf`, and copy the key (starts with `sk-or-v1-...`).
3. Attach it to `xsf`:
   ```bash
   xsf key set openrouter sk-or-v1-YOUR_KEY_HERE --test
   ```

---

## Part B: Cerebras Wafer-Scale Inference (`csk-...`)

Cerebras runs Llama and Qwen models on wafer-scale processors at ultra-high token speeds.

1. Go to **[cloud.cerebras.ai](https://cloud.cerebras.ai/)** and sign in.
2. Open **API Keys**, create a new key (starts with `csk-...`), and copy it.
3. Attach it to `xsf`:
   ```bash
   xsf key set cerebras csk-YOUR_KEY_HERE --test
   ```

> [!NOTE]
> If a Cerebras account requires billing credits (HTTP `402`), `xsf`'s circuit breaker automatically places that key in a 30-minute cooldown and routes to Gemini/OpenRouter with zero lag.
