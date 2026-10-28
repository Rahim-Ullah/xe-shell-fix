# 04 — Grok (xAI), OpenAI / Custom Endpoints & Local Ollama

In addition to free cloud tiers, `xsf` supports opt-in commercial keys (`grok`, `openai`, custom OpenAI-compatible providers like DeepSeek/Mistral) and **100% offline local LLMs** via Ollama.

---

## 1. Local Private LLM via Ollama (100% Offline, Zero API Keys)

If you want AI reasoning without sending a single byte over the internet:

1. Install **[Ollama](https://ollama.com/download)** on your machine.
2. Pull a fast coding model:
   ```bash
   ollama pull qwen2.5-coder:1.5b
   ```
3. Enable Ollama in `xsf`:
   ```bash
   xsf config
   # Press [7] to toggle Local Ollama LLM -> Press [S] to save
   ```
   When enabled, `xsf` pings `http://localhost:11434` in `<0.8s` and uses your local model before touching any cloud API.

---

## 2. xAI Grok (`xai-...`)

1. Generate a key at **[console.x.ai](https://console.x.ai/)**.
2. Attach it to `xsf`:
   ```bash
   xsf key set grok xai-YOUR_KEY_HERE --test
   ```

---

## 3. OpenAI or Custom Compatible Endpoints (DeepSeek, Mistral, Together, vLLM)

1. Attach your OpenAI (or compatible) key:
   ```bash
   xsf key set openai sk-YOUR_KEY_HERE --test
   ```
2. *(Optional)* To point to a custom OpenAI-compatible provider (e.g. DeepSeek or local vLLM), set `openai_base_url` and `openai_model` in `~/.shellfix/config.toml`:
   ```toml
   [ai]
   openai_api_key = "sk-..."
   openai_base_url = "https://api.deepseek.com/v1"
   openai_model = "deepseek-chat"
   ```
