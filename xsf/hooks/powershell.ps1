# xe-shell-fix (xsf) - PowerShell Hook
# Add to your $PROFILE:
#   (& (Get-Command -CommandType Application xsf) init powershell | Out-String) | Invoke-Expression

function _xsf_exec {
    param(
        [switch]$Rerun,
        [switch]$Offline,
        [switch]$Ai,
        [switch]$Auto
    )

    $history = Get-History -Count 15
    $last = ""
    for ($i = $history.Count - 1; $i -ge 0; $i--) {
        $line = $history[$i].CommandLine.Trim()
        if ($line -and $line -notmatch '^(xsf|xefix|xeeee|fuxx)\b') {
            $last = $line
            break
        }
    }

    if (-not $last) {
        Write-Host "xsf: no previous command found" -ForegroundColor Yellow
        return
    }

    $extraArgs = @()
    if ($Offline) { $extraArgs += "--offline" }
    if ($Ai) { $extraArgs += "--ai" }
    if ($Auto) { $extraArgs += "--auto" }

    if ($Rerun) {
        Write-Host "This will re-run the previous command to capture stderr:" -ForegroundColor Yellow
        Write-Host "  $last" -ForegroundColor Cyan
        $ans = Read-Host "Proceed? [y/N]"
        if ($ans -match '^[Yy]') {
            $tmp = [System.IO.Path]::GetTempFileName()
            try {
                Invoke-Expression $last 2> $tmp | Out-Null
            } catch {}
            $extraArgs += @("--stderr-file", $tmp)
        }
    }

    $app = (Get-Command -CommandType Application xsf -ErrorAction SilentlyContinue)
    if ($app) {
        $fixed = & $app.Source $last --shell powershell @extraArgs
    } else {
        $fixed = python -m xsf.cli $last --shell powershell @extraArgs
    }

    if ($LASTEXITCODE -eq 0 -and $fixed) {
        Invoke-Expression $fixed
    }
}

function xsf {
    if ($args.Count -gt 0 -and ($args[0] -in @("init", "config", "ui", "--version", "-v", "--help", "-h"))) {
        & (Get-Command -CommandType Application xsf) @args
        return
    }
    _xsf_exec @args
}
function xefix { _xsf_exec @args }
function xeeee { _xsf_exec @args }
function fuxx  { _xsf_exec @args }
