@echo off
REM shellfix (AI) - CMD hook
REM
REM Wired up via a doskey macro (the installer does this for you):
REM     doskey fixai=%USERPROFILE%\.shellfix\api\hooks\cmd_hook.bat $*
REM
REM Same history-capture trick as the offline project's CMD hook - see that
REM one's comments for why `doskey /history` is what makes this possible.
REM
REM No --rerun here: CMD has no safe way to capture a previous command's
REM real error text without breaking the interactive confirm prompt (see
REM the offline project's README for the full explanation). The command
REM text alone is still sent to Gemini and is usually enough context for
REM common mistakes; for errors where the exact message really matters,
REM use PowerShell or Git Bash's `fixai --rerun` instead.

setlocal EnableDelayedExpansion

set "SHELLFIX_AI_HOME=%USERPROFILE%\.shellfix\api"
set "HISTFILE=%TEMP%\shellfix_ai_hist_%RANDOM%.txt"

doskey /history > "%HISTFILE%" 2>nul

set "PREV="
set "CUR="
for /f "usebackq delims=" %%L in ("%HISTFILE%") do (
    set "PREV=!CUR!"
    set "CUR=%%L"
)
del "%HISTFILE%" >nul 2>&1

if "!PREV!"=="" (
    echo fixcmd-ai: no previous command found
    goto :done
)

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo fixcmd-ai: no 'python' or 'py' found on PATH
        goto :done
    )
    set "PYEXE=py"
) else (
    set "PYEXE=python"
)

set "FIXED="
for /f "usebackq delims=" %%F in (`!PYEXE! "%SHELLFIX_AI_HOME%\fixcmd_ai.py" "!PREV!" --shell cmd`) do (
    set "FIXED=%%F"
)

if defined FIXED (
    call !FIXED!
)

:done
endlocal
