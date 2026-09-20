# shellfix (AI) - PowerShell hook
#
# Add this to your $PROFILE (the installer does this for you):
#   . "$HOME\.shellfix\api\hooks\powershell_hook.ps1"
#
# Named `fixai` (not `fix`) so this can be installed side by side with the
# offline project without clashing.
#
# Usage:
#   <run a command with a less common error>
#   fixai              # ask Gemini, then ask you to confirm
#   fixai -Rerun       # also re-run the previous command first to capture
#                       # its real error text before asking the model.
#                       # You'll be asked to confirm that separately.

if (-not $env:SHELLFIX_AI_HOME) {
    $env:SHELLFIX_AI_HOME = Join-Path $HOME ".shellfix\api"
}

function fixai {
    param([switch]$Rerun)

    $last = (Get-History -Count 1).CommandLine
    if (-not $last -or $last -eq "fixai" -or $last -eq "fixai -Rerun") {
        Write-Host "fixcmd-ai: no previous command found" -ForegroundColor Yellow
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
        Write-Host "fixcmd-ai: no 'python' or 'python3' found on PATH" -ForegroundColor Red
        return
    }

    $fixed = & $pyCmd.Source "$env:SHELLFIX_AI_HOME\fixcmd_ai.py" $last --shell powershell @stderrArgs
    if ($LASTEXITCODE -eq 0 -and $fixed) {
        Invoke-Expression $fixed
    }
}
