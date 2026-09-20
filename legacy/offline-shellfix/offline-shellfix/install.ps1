<#
  install.ps1 - sets up the offline shellfix "fix" command for
  PowerShell, Git Bash, and CMD in one pass.

  Run this FROM POWERSHELL (it needs PowerShell's file/registry cmdlets
  even though it's wiring up all three shells):

      cd path\to\offline-shellfix
      powershell -ExecutionPolicy Bypass -File .\install.ps1

  What it touches:
    - Copies this folder to  %USERPROFILE%\.shellfix\offline
    - Appends one line to your PowerShell $PROFILE
    - Appends one line to ~\.bashrc (used by Git Bash)
    - Adds a doskey macro via the HKCU\...\Command Processor\AutoRun
      registry value, so new CMD windows get the `fix` command too.
      This is a per-user registry change - see the README for how to
      undo it if you ever want to remove this.
#>

$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$dest = Join-Path $HOME ".shellfix\offline"

Write-Host "Installing shellfix (offline) to $dest ..."
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $src '*') -Destination $dest -Recurse -Force

# --- PowerShell -------------------------------------------------------
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Force -Path $PROFILE | Out-Null
}
$hookLine = ". `"$dest\hooks\powershell_hook.ps1`""
$alreadyThere = (Test-Path $PROFILE) -and (Select-String -Path $PROFILE -SimpleMatch -Pattern $dest -Quiet -ErrorAction SilentlyContinue)
if (-not $alreadyThere) {
    Add-Content -Path $PROFILE -Value "`n# shellfix (offline)`n$hookLine"
    Write-Host "  PowerShell profile updated: $PROFILE"
} else {
    Write-Host "  PowerShell profile already wired up, skipped."
}

# --- Git Bash -----------------------------------------------------------
$bashrc = Join-Path $HOME ".bashrc"
$destForward = $dest -replace '\\', '/'
$bashHookLine = "source `"$destForward/hooks/bash_hook.sh`""
$bashAlready = (Test-Path $bashrc) -and (Select-String -Path $bashrc -SimpleMatch -Pattern $destForward -Quiet -ErrorAction SilentlyContinue)
if (-not $bashAlready) {
    Add-Content -Path $bashrc -Value "`n# shellfix (offline)`n$bashHookLine"
    Write-Host "  ~/.bashrc updated: $bashrc"
} else {
    Write-Host "  ~/.bashrc already wired up, skipped."
}

# --- CMD ------------------------------------------------------------
$cmdInit = Join-Path $dest "hooks\cmd_autorun.cmd"
"@doskey fix=$dest\hooks\cmd_hook.bat `$*" | Set-Content -Path $cmdInit -Encoding ASCII

$autoRunKey = "HKCU:\Software\Microsoft\Command Processor"
if (-not (Test-Path $autoRunKey)) {
    New-Item -Path $autoRunKey -Force | Out-Null
}
$existing = (Get-ItemProperty -Path $autoRunKey -Name AutoRun -ErrorAction SilentlyContinue).AutoRun
if ($existing -and ($existing -notmatch [regex]::Escape($cmdInit))) {
    $newValue = "$existing & `"$cmdInit`""
} elseif (-not $existing) {
    $newValue = "`"$cmdInit`""
} else {
    $newValue = $existing
}
New-ItemProperty -Path $autoRunKey -Name AutoRun -Value $newValue -PropertyType String -Force | Out-Null
Write-Host "  CMD AutoRun registry key updated (new cmd.exe windows will load 'fix')."

Write-Host ""
Write-Host "Done. Open a NEW PowerShell window, Git Bash window, and CMD window to try 'fix'."
Write-Host "You can also test the engine directly right now, no shell hook needed:"
Write-Host "  python `"$dest\fixcmd.py`" `"pip instaaaaal fastapi`" --dry-run"
