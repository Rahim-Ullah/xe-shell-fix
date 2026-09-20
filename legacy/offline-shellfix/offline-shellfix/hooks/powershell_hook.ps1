# shellfix (offline) - PowerShell hook
#
# Add this to your $PROFILE (the installer does this for you):
#   . "$HOME\.shellfix\offline\hooks\powershell_hook.ps1"
#
# Usage:
#   <run a command with a typo>
#   fix              # suggest a fix, ask to run it
#   fix -Rerun       # also re-run the previous command first to capture
#                     # its error text for the small set of error-based
#                     # rules. You'll be asked to confirm that separately.

if (-not $env:SHELLFIX_HOME) {
    $env:SHELLFIX_HOME = Join-Path $HOME ".shellfix\offline"
}

function fix {
    param([switch]$Rerun)

    $last = (Get-History -Count 1).CommandLine
    if (-not $last -or $last -eq "fix" -or $last -eq "fix -Rerun") {
        Write-Host "fixcmd: no previous command found" -ForegroundColor Yellow
        return
    }

    $stderrArgs = @()
    if ($Rerun) {
        Write-Host "This will re-run the previous command to capture its exact error text:" -ForegroundColor Yellow
        Write-Host "  $last"
        $ans = Read-Host "Continue? [y/N]"
        if ($ans -match '^[Yy]') {
            $tmp = [System.IO.Path]::GetTempFileName()
            try { Invoke-Expression $last 2> $tmp | Out-Null } catch {}
            $stderrArgs = @("--stderr-file", $tmp)
        }
    }

    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pyCmd) {
        Write-Host "fixcmd: no 'python' or 'python3' found on PATH" -ForegroundColor Red
        return
    }

    $fixed = & $pyCmd.Source "$env:SHELLFIX_HOME\fixcmd.py" $last --shell powershell @stderrArgs
    if ($LASTEXITCODE -eq 0 -and $fixed) {
        Invoke-Expression $fixed
    }
}
