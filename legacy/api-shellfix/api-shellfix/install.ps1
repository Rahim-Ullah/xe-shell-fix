<#
  install.ps1 - sets up the AI-assisted shellfix "fixai" command for
  PowerShell, Git Bash, and CMD in one pass.

  Run this FROM POWERSHELL:
      cd path\to\api-shellfix
      powershell -ExecutionPolicy Bypass -File .\install.ps1

  What it touches (same shape as the offline installer, safe to run both):
    - Copies this folder to  %USERPROFILE%\.shellfix\api
    - Appends one line to your PowerShell $PROFILE
    - Appends one line to ~\.bashrc (used by Git Bash)
    - Adds a doskey macro via the HKCU\...\Command Processor\AutoRun
      registry value (additive - won't remove the offline project's macro
      if you installed that too)

  This does NOT set your API key. After installing, either:
    setx GEMINI_API_KEY "your-key-here"
  or copy config.example.toml to %USERPROFILE%\.shellfix\config.toml and
  fill it in. Get a free key at https://aistudio.google.com/apikey
#>

$ErrorActionPreference = "Stop"
$src = $PSScriptRoot
$dest = Join-Path $HOME ".shellfix\api"

Write-Host "Installing shellfix (AI) to $dest ..."
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $src '*') -Destination $dest -Recurse -Force

# --- PowerShell -------------------------------------------------------
if (-not (Test-Path $PROFILE)) {
    New-Item -ItemType File -Force -Path $PROFILE | Out-Null
}
$hookLine = ". `"$dest\hooks\powershell_hook.ps1`""
$alreadyThere = (Test-Path $PROFILE) -and (Select-String -Path $PROFILE -SimpleMatch -Pattern $dest -Quiet -ErrorAction SilentlyContinue)
if (-not $alreadyThere) {
    Add-Content -Path $PROFILE -Value "`n# shellfix (AI)`n$hookLine"
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
    Add-Content -Path $bashrc -Value "`n# shellfix (AI)`n$bashHookLine"
    Write-Host "  ~/.bashrc updated: $bashrc"
} else {
    Write-Host "  ~/.bashrc already wired up, skipped."
}

# --- CMD ------------------------------------------------------------
$cmdInit = Join-Path $dest "hooks\cmd_autorun.cmd"
"@doskey fixai=$dest\hooks\cmd_hook.bat `$*" | Set-Content -Path $cmdInit -Encoding ASCII

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
Write-Host "  CMD AutoRun registry key updated (new cmd.exe windows will load 'fixai')."

Write-Host ""
Write-Host "Done. Open NEW shell windows, then set your API key:"
Write-Host "  setx GEMINI_API_KEY `"your-key-here`""
Write-Host "Get a free key (no card) at https://aistudio.google.com/apikey"
Write-Host ""
Write-Host "Test the engine directly any time, no shell hook needed:"
Write-Host "  python `"$dest\fixcmd_ai.py`" `"some broken command`" --dry-run"
