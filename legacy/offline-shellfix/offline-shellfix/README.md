# shellfix (offline)

A `fix` command for PowerShell, Git Bash, and CMD that catches the last
failed command and offers a corrected version - typo'd subcommands
(`pip instaaaaal` → `pip install`) and missing/wrong flags
(`python venv .venv` → `python -m venv .venv`). Runs entirely locally, no
API key, no network calls.

## How it works

```
                 ┌──────────────────────────────┐
  you type       │  1. shell hook grabs the      │
  a broken   ───►│     previous command text     │
  command        └───────────────┬───────────────┘
                                  │ passes it as a plain string
                                  ▼
                 ┌──────────────────────────────┐
                 │  2. fixcmd.py (this engine)   │
                 │     a) deterministic flag/    │
                 │        pattern rules first    │
                 │     b) fuzzy typo matching    │
                 │        as a fallback          │
                 └───────────────┬───────────────┘
                                  │ prints ONLY the fixed command,
                                  │ and only after you approve it
                                  ▼
                 ┌──────────────────────────────┐
                 │  3. shell hook `eval`s it in  │
                 │     YOUR shell (so cd, env    │
                 │     vars etc. actually stick) │
                 └──────────────────────────────┘
```

The engine (`fixcmd.py`) never runs anything itself - it only ever prints
one line (the approved fix) to stdout, after asking you to confirm on
stderr. The shell hook is what actually executes it, in your live shell
session. That split matters: if the Python process executed `cd ..`
itself, the directory change would vanish the moment that process exited.
Handing the string back to the shell for `eval`/`Invoke-Expression` is what
makes `cd`, environment variables, and aliases behave correctly.

## Install

```powershell
cd path\to\offline-shellfix
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Run it from PowerShell even though it wires up all three shells - it's the
one with the file and registry cmdlets needed to do that safely. It:

- copies this folder to `%USERPROFILE%\.shellfix\offline`
- adds one line to your PowerShell `$PROFILE`
- adds one line to `~\.bashrc` (Git Bash)
- adds a `doskey fix=...` macro via the `HKCU\...\Command Processor\AutoRun`
  registry value, so new CMD windows load it automatically

Then open **new** windows for each shell. Requires Python 3.9+ on PATH in
each shell (you've already got this, since you're running `pip`/`python`
day to day).

Don't want to touch your profiles/registry? Skip `install.ps1` and just run
the engine directly any time:
```
python fixcmd.py "pip instaaaaal fastapi" --dry-run
```

## Usage

```
<run something with a typo>
fix              # bash & PowerShell & CMD
```

- Enter / `y` → runs the suggested fix
- `n` → cancels, nothing runs
- destructive-looking fixes (`rm -rf`, `git push --force`, `DROP TABLE`,
  `format`, ...) require typing the full word `yes` - Enter or `y` alone
  will *not* approve them
- `fix --rerun` (bash/PowerShell only, see limitations) - re-runs the
  previous command first to capture its real error text, which unlocks a
  couple of error-based rules (missing `chmod +x`, missing `./`). You're
  asked to confirm the re-run separately, since re-running a command that
  partially succeeded before failing could repeat a side effect.

Flags for testing the engine directly, no shell integration needed:
```
python fixcmd.py "<command>" --shell bash|powershell|cmd [--dry-run] [--auto]
```

## What it can and can't fix

**Can:** subcommand typos for ~30 common dev tools (git, npm, pip, docker,
node, python, go, cargo, etc. - see `vocabulary.json`), a handful of
missing-flag patterns (`python -m ...`, `git commit -m`, `npm run <script>`,
Windows venv activation per-shell), and two error-text rules when you use
`--rerun`.

**Can't:** anything that needs actual reasoning about *why* a command
failed beyond those patterns - a real stack trace, a logic bug, a
misconfigured tool. That's what the AI/API version (the sibling project) is
for; the two are meant to be used together, with `fix` for the instant,
free, offline cases and `fixai` for everything else.

## Extending it

- **New tool / subcommand vocabulary** → edit `vocabulary.json`. Each entry
  is `{"subcommands": [...], "safe_autorun": [...]}`. `safe_autorun` lists
  which subcommands are safe to run without asking when `--auto` is passed
  (keep this to read-only/idempotent ones).
- **New flag-pattern rule** → add a function to `flag_rules.py` and append
  it to the `RULES` list. Return `None` if unsure - a rule that guesses
  wrong is worse than a rule that stays quiet.
- **New destructive pattern** → add a regex to `DENYLIST` in `safety.py`.

## Known limitations (read before you trust `--auto`)

- **CMD has no `--rerun`.** There's no reliable, non-invasive way to read a
  previous command's actual error text in `cmd.exe` without piping it
  through `for /f`, which routinely breaks the interactive confirm prompt.
  Typo/flag fixes (the majority of cases, including the exact
  `python venv .venv` example) work fine in CMD without it.
- **The fuzzy matcher only touches unrecognized tokens.** It never
  "corrects" `cp`, `ps`, `cd`, `grep`, etc. into an unrelated tool name -
  those are in `_known_safe_commands` in `vocabulary.json` precisely so
  short real commands don't get mangled. If you add new tools whose names
  collide with common short commands, keep that list updated.
- **Quoting is simplified.** Fixed commands with spaces get wrapped in
  plain double quotes. This covers the common case (a filename, a commit
  message) but isn't a full shell-quoting engine for every edge case
  (embedded backticks, `$()`, nested quotes).
- **The denylist is a safety net, not a guarantee.** It's pattern-based and
  deliberately broad, but no regex list catches every destructive command
  in three different shell dialects. Read the suggestion before you type
  `yes`.

## Uninstall

```powershell
Remove-Item -Recurse -Force "$HOME\.shellfix\offline"
```
Then remove the `# shellfix (offline)` block from your `$PROFILE` and from
`~\.bashrc`, and remove the `fix.cmd_autorun.cmd` reference from
`HKCU:\Software\Microsoft\Command Processor\AutoRun` (or clear that value
entirely if you don't use it for anything else).
