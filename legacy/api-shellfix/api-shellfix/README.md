# shellfix (AI)

A `fixai` command for PowerShell, Git Bash, and CMD that sends your last
failed command (and, optionally, its real error text) to Gemini's free API
and offers back a corrected command. Meant as the companion to the sibling
`offline-shellfix` project: use `fix` for instant, free, no-network typo/flag
fixes, and `fixai` for the harder cases the offline rules don't cover -
real tracebacks, config errors, "why did this actually fail."

## Why Gemini, not Grok

You asked for "free AI APIs (Grok/Gemini)" - I checked both before wiring
anything up. Gemini has an ongoing free tier (rate-limited, but real, no
card required). Grok's API only gives a one-time $25 in credits that
expires in about 30 days - after that it's paid, so it doesn't actually fit
"free." `providers.py` is written as a small interface (`fix()` in,
`(command, explanation, confidence)` out) specifically so you can drop in a
`GrokProvider` or an OpenRouter-backed provider later without touching
anything else in the project.

## How it works

Same three-stage shape as the offline project, with one stage swapped:

1. **Shell hook** grabs the previous command text (and, if you ask for
   `--rerun`, re-executes it in a controlled way to capture its real
   stderr - see the offline project's README for why that re-run has to
   happen in the shell hook, not in Python).
2. **`fixcmd_ai.py`** checks a local cache first (so retyping the exact
   same mistake twice doesn't cost an API call), then sends the command +
   shell name + error text to Gemini with a strict "reply with only this
   JSON shape" prompt, and asks you to confirm the result.
3. **Shell hook** `eval`s the approved command in *your* live shell, so
   `cd`, env vars, etc. behave correctly - `fixcmd_ai.py` itself never
   executes anything.

The prompt explicitly asks the model to flag destructive commands; our own
regex denylist in `safety.py` is still the thing that actually gates
`--auto` and demands a typed `yes`, though - the model's opinion is a
second signal, not the safety mechanism.

## Install

```powershell
cd path\to\api-shellfix
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Same shape as the offline installer (copies to `%USERPROFILE%\.shellfix\api`,
wires up all three shells) - safe to run alongside the offline project's
installer, they use different folders, profile lines, and registry entries.

Then set your key. Get a free one (no credit card) at
**https://aistudio.google.com/apikey**, then either:

```powershell
setx GEMINI_API_KEY "your-key-here"
```
or copy `config.example.toml` to `%USERPROFILE%\.shellfix\config.toml` and
fill in `api_key`. The env var wins if both are set.

## Usage

```
<run something that fails for a non-obvious reason>
fixai              # bash & PowerShell & CMD
```

Same confirmation rules as the offline project: Enter/`y` runs it, `n`
cancels, destructive-looking suggestions need a typed `yes`.

```
fixai --rerun      # bash/PowerShell only - re-runs the previous command
                    # to capture its real stderr before asking Gemini,
                    # which noticeably improves fixes for anything beyond
                    # a simple typo. You confirm the re-run separately.
```

Test the engine directly, no shell integration or even a real request
needed to see the plumbing work:
```
python fixcmd_ai.py "some broken command" --dry-run
```

## Cost / quota reality check

The free tier is rate-limited (currently in the ballpark of low
requests-per-minute and a few hundred per day on Flash-class models - check
the live numbers for your account at https://aistudio.google.com/, they
change). For a single developer fixing typos, that's generous. The local
cache (`~/.shellfix/ai_cache.json`) also means you never pay twice for the
identical mistake. If you ever add a paid key, nothing here needs to
change - it's still just a header on an HTTP request.

## Extending it

- **Add a provider**: implement `Provider.fix()` in `providers.py`
  (signature: `(raw_command, stderr_text, shell) -> (command, explanation,
  confidence)`), register it in `get_provider()`, and set `provider = "..."`
  in `config.toml`.
- **Change the model**: edit `model` in `config.toml`. Check
  https://ai.google.dev/gemini-api/docs/pricing for current free-tier IDs.
- **Tune the prompt**: `SYSTEM_PROMPT` in `providers.py`.

## Known limitations

- **CMD has no `--rerun`** - same reason as the offline project (see its
  README): capturing real stderr non-invasively in `cmd.exe` without
  breaking the interactive confirm prompt isn't reliable. The command text
  alone still goes to Gemini in CMD, which is often enough.
- **Network required.** No connection or a Gemini outage means `fixai`
  fails outright (with a plain-English error, not a crash) - it does not
  silently fall back to the offline engine. Run the sibling `fix` command
  instead in that case.
- **The model can be wrong.** Confidence scores are the model's own
  self-report, not a guarantee. Read the suggestion, especially anything
  flagged destructive, before typing `yes`.
- **Free-tier data usage.** Google's free tier terms (as of this writing)
  allow using free-tier requests to improve their products. Don't run
  commands containing secrets/credentials through `fixai` if that matters
  to you - use the offline version for those, or a paid key.

## Uninstall

```powershell
Remove-Item -Recurse -Force "$HOME\.shellfix\api"
```
Then remove the `# shellfix (AI)` block from your `$PROFILE` and from
`~\.bashrc`, and remove the `fixai`-related entry from
`HKCU:\Software\Microsoft\Command Processor\AutoRun`.
