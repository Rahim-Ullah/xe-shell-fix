@echo off
REM shellfix (offline) - CMD hook
REM
REM Wired up via a doskey macro (the installer does this for you):
REM     doskey fix=%USERPROFILE%\.shellfix\offline\hooks\cmd_hook.bat $*
REM
REM CMD's own command history isn't readable by an external program without
REM doskey, so this reads it via `doskey /history`, which only works once
REM doskey has been loaded in the session - which it has, because defining
REM the "fix" macro above loads it. That's why CMD needs the doskey macro
REM even though bash/PowerShell just define a function.
REM
REM Note: unlike the bash/PowerShell hooks, this does NOT support --rerun.
REM CMD gives no safe way to capture a previous command's real error text
REM without piping it through `for /f`, which frequently breaks stdin for
REM the interactive confirm prompt. Typo and missing-flag fixes (the large
REM majority of cases) don't need the error text anyway - they work off the
REM command text alone, same as here.

setlocal EnableDelayedExpansion

set "SHELLFIX_HOME=%USERPROFILE%\.shellfix\offline"
set "HISTFILE=%TEMP%\shellfix_hist_%RANDOM%.txt"

doskey /history > "%HISTFILE%" 2>nul

set "PREV="
set "CUR="
for /f "usebackq delims=" %%L in ("%HISTFILE%") do (
    set "PREV=!CUR!"
    set "CUR=%%L"
)
del "%HISTFILE%" >nul 2>&1

if "!PREV!"=="" (
    echo fixcmd: no previous command found
    goto :done
)

where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo fixcmd: no 'python' or 'py' found on PATH
        goto :done
    )
    set "PYEXE=py"
) else (
    set "PYEXE=python"
)

set "FIXED="
for /f "usebackq delims=" %%F in (`!PYEXE! "%SHELLFIX_HOME%\fixcmd.py" "!PREV!" --shell cmd`) do (
    set "FIXED=%%F"
)

if defined FIXED (
    call !FIXED!
)

:done
endlocal
