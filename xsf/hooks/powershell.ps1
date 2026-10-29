# xe-shell-fix (xsf) - PowerShell Hook
# Add to your $PROFILE:
#   try { (& (Get-Command -CommandType Application xsf -ErrorAction Stop | Select-Object -First 1) init powershell | Out-String) | Invoke-Expression } catch { (& python -m xsf.cli init powershell | Out-String) | Invoke-Expression }

$_XSF_INIT_PYTHON = "@XSF_INIT_PYTHON@"

function _xsf_run_cli {
    param([string[]]$CliArgs)
    $app = (Get-Command -CommandType Application xsf -ErrorAction SilentlyContinue | Select-Object -First 1)
    if ($app) {
        try {
            return & $app.Source @CliArgs
        } catch {}
    }
    if ($_XSF_INIT_PYTHON -and (Test-Path $_XSF_INIT_PYTHON)) {
        return & $_XSF_INIT_PYTHON -m xsf.cli @CliArgs
    }
    try {
        $test = python -c "import xsf" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return python -m xsf.cli @CliArgs
        }
    } catch {}
    try {
        $testPy = py -c "import xsf" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return py -m xsf.cli @CliArgs
        }
    } catch {}
    return python -m xsf.cli @CliArgs
}

function _xsf_exec {
    param(
        [switch]$Rerun,
        [switch]$Offline,
        [switch]$Ai,
        [switch]$Auto,
        [switch]$DryRun,
        [switch]$NoCache,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$RemainingArgs
    )

    if ($RemainingArgs -and $RemainingArgs.Count -gt 0 -and ($RemainingArgs[0] -in @("init", "config", "ui", "setup", "power", "key", "keys", "commands", "help", "--commands", "--version", "-v", "--help", "-h"))) {
        _xsf_run_cli $RemainingArgs
        return
    }

    $posArgs = @()
    $extraArgs = @()
    if ($Offline) { $extraArgs += "--offline" }
    if ($Ai) { $extraArgs += "--ai" }
    if ($Auto) { $extraArgs += "--auto" }
    if ($DryRun) { $extraArgs += "--dry-run" }
    if ($NoCache) { $extraArgs += "--no-cache" }
    if ($RemainingArgs) {
        foreach ($arg in $RemainingArgs) {
            if ($arg -in @("--offline", "--ai", "--auto", "--dry-run", "--no-cache")) {
                if ($extraArgs -notcontains $arg) {
                    $extraArgs += $arg
                }
            } elseif (-not $arg.StartsWith("-")) {
                $posArgs += $arg
            }
        }
    }

    if ($posArgs.Count -gt 0) {
        $targetCmd = ($posArgs -join " ").Trim()
    } else {
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
            if ($extraArgs -contains "--ai") {
                _xsf_run_cli (@("--shell", "powershell") + $extraArgs)
                return
            }
            Write-Host "xsf: no previous command found" -ForegroundColor Yellow
            return
        }
        $targetCmd = $last
    }

    $tmp = $null
    if ($Rerun) {
        Write-Host "This will re-run the previous command to capture stderr:" -ForegroundColor Yellow
        Write-Host "  $targetCmd" -ForegroundColor Cyan
        $ans = Read-Host "Proceed? [y/N]"
        if ($ans -match '^[Yy]') {
            $tmp = [System.IO.Path]::GetTempFileName()
            try {
                Invoke-Expression $targetCmd 2> $tmp | Out-Null
            } catch {}
            $extraArgs += @("--stderr-file", $tmp)
        }
    }

    try {
        $cliCallArgs = @($targetCmd, "--shell", "powershell") + $extraArgs
        $fixed = _xsf_run_cli $cliCallArgs

        if ($LASTEXITCODE -eq 0 -and $fixed) {
            $cmdToRun = ($fixed -join "`n").Trim()
            if ($cmdToRun.Length -gt 0 -and $cmdToRun.Length -lt 4096) {
                Invoke-Expression $cmdToRun
            }
        }
    } finally {
        if ($tmp -and (Test-Path $tmp)) {
            Remove-Item $tmp -Force -ErrorAction SilentlyContinue
        }
    }
}

function xsf   { _xsf_exec @args }
function xefix { _xsf_exec @args }
function xeeee { _xsf_exec @args }
function fuxx  { _xsf_exec @args }
