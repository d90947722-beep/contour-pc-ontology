param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$siteUrl = 'http://127.0.0.1:8501'
function Test-SiteReady {
    try {
        return ((Invoke-RestMethod -Uri "$siteUrl/_stcore/health" -TimeoutSec 2) -eq 'ok')
    } catch { return $false }
}
try {
    if (Test-SiteReady) {
        if (-not $NoBrowser) { Start-Process $siteUrl }
        exit 0
    }
    $venvPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
    # Reuse the verified environment of this local workspace when available.
    $workspacePython = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../work/venv/Scripts/python.exe'))
    $usingWorkspaceEnvironment = $false
    if (Test-Path -LiteralPath $workspacePython) {
        @'
import importlib.metadata as m
from pathlib import Path
pairs = [line.strip().split("==") for line in Path("requirements.txt").read_text().splitlines() if line.strip() and not line.startswith("#")]
assert all(m.version(name) == version for name, version in pairs)
'@ | & $workspacePython -
        if ($LASTEXITCODE -eq 0) {
            $venvPython = $workspacePython
            $usingWorkspaceEnvironment = $true
        }
    }
    if (-not (Test-Path -LiteralPath $venvPython)) {
        $customPython = $env:PC_ONTOLOGY_PYTHON
        $bundledPython = Join-Path $env:USERPROFILE '.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe'
        if ($customPython -and (Test-Path -LiteralPath $customPython)) {
            & $customPython -m venv .venv
        } elseif (Test-Path -LiteralPath $bundledPython) {
            & $bundledPython -m venv .venv
        } elseif (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv .venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv .venv
        } else {
            throw 'Install Python 3.10+ and enable its PATH option, then run START.bat again.'
        }
        if ($LASTEXITCODE -ne 0) { throw 'Could not create a Python environment.' }
    }
    & $venvPython -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ is required"'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
    $requirementsHash = (Get-FileHash -LiteralPath 'requirements.txt' -Algorithm SHA256).Hash
    $stamp = Join-Path $PSScriptRoot '.venv/requirements.sha256'
    $installedHash = if (Test-Path -LiteralPath $stamp) { Get-Content -LiteralPath $stamp -Raw } else { '' }
    if (-not $usingWorkspaceEnvironment -and $installedHash.Trim() -ne $requirementsHash) {
        Write-Host 'Installing application dependencies. Internet is needed on the first run.'
        & $venvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check your internet connection.' }
        Set-Content -LiteralPath $stamp -Value $requirementsHash
    }
    $logDir = Join-Path $PSScriptRoot 'data'
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    $appFile = Join-Path $PSScriptRoot 'app.py'
    $serverProcess = Start-Process -FilePath $venvPython -ArgumentList @('-m', 'streamlit', 'run', ('"' + $appFile + '"'), '--server.address', '127.0.0.1', '--server.port', '8501', '--server.headless', 'true') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logDir 'server.log') -RedirectStandardError (Join-Path $logDir 'server-error.log') -PassThru
    $deadline = (Get-Date).AddSeconds(40)
    do {
        if (Test-SiteReady) {
            if (-not $NoBrowser) { Start-Process $siteUrl }
            Write-Host "Site is running: $siteUrl"
            exit 0
        }
        if ($serverProcess.HasExited) { throw 'Server could not start. See data/server-error.log.' }
        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $deadline)
    throw 'The server did not respond in time. See data/server-error.log.'
} catch {
    Write-Host $_ -ForegroundColor Red
    Read-Host 'Press Enter to close'
    exit 1
}
