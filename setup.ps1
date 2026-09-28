<#
.SYNOPSIS
  ForecastGuard AI (SIH 26079) - one-shot setup + run script for Windows.

.DESCRIPTION
  Checks Python/Node, installs backend + frontend dependencies, rebuilds the
  React dashboard, trains the pilot model, (optionally) downloads the pilot
  GEFS slice, then starts the API server and opens the dashboard.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup.ps1
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -FetchData
  powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Background -NoBrowser

.NOTES
  ASCII-only on purpose: keeps Windows PowerShell 5.1 parsing identical on
  every system codepage.
#>
[CmdletBinding()]
param(
  [switch]$FetchData,  # Download pilot GEFS slice (~130 MB). Skip if already present.
  [switch]$SkipBuild,  # Skip frontend npm install/build (serve last build in dashboard/).
  [switch]$SkipTrain,  # Skip pilot model training (reuse data/processed/model.joblib).
  [switch]$Background, # Run the server detached instead of blocking this shell.
  [switch]$NoBrowser   # Do not auto-open http://127.0.0.1:8000/
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

if (-not $env:LOKY_MAX_CPU_COUNT) {
  $env:LOKY_MAX_CPU_COUNT = [string][Environment]::ProcessorCount
}

$Port = 8000
$ServerUrl = "http://127.0.0.1:$Port/"

function Step($msg) {
  Write-Host ''
  Write-Host "==> $msg" -ForegroundColor Cyan
}

function Warn($msg) { Write-Host '  ! ' -NoNewline -ForegroundColor Yellow; Write-Host $msg }
function Ok($msg)   { Write-Host '  [OK] ' -NoNewline -ForegroundColor Green; Write-Host $msg }

function Assert-Command($name, $hint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw ("'" + $name + "' not found on PATH. " + $hint)
  }
}

function Test-PortFree($port) {
  $client = New-Object System.Net.Sockets.TcpClient
  try {
    $iar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
    $connected = $iar.AsyncWaitHandle.WaitOne(800)
    if ($connected -and $client.Connected) { return $false }
    return $true
  } catch { return $true } finally { $client.Close() }
}

function Wait-Server($url, $retries = 30) {
  for ($i = 1; $i -le $retries; $i++) {
    try {
      $r = Invoke-RestMethod -Uri ($url + 'api/v1/health') -TimeoutSec 5
      if ($r.status -eq 'healthy') { return $true }
    } catch { Start-Sleep -Seconds 2 }
  }
  return $false
}

Write-Host 'ForecastGuard AI - setup and run (SIH 26079)' -ForegroundColor White
Write-Host "Project root: $Root" -ForegroundColor DarkGray

# ---------- 1. Toolchain ----------
Step '1/6 Checking toolchain (Python 3.10+, Node 18+)'
Assert-Command 'python' 'Install Python 3.11 from python.org and tick "Add to PATH".'
Assert-Command 'node'   'Install Node.js LTS from nodejs.org.'
Assert-Command 'npm'    'Comes with the Node.js installer.'

$pyv = (& python --version 2>&1).ToString()
if ($pyv -notmatch 'Python 3\.(\d+)') { throw "Unrecognised Python version: $pyv" }
if ([int]$Matches[1] -lt 10) { throw "Python 3.10+ required (found $pyv)." }
Ok "Python $pyv"
$nodev = (& node --version).ToString().TrimStart('v')
if ([int]($nodev.Split('.')[0]) -lt 18) { throw "Node 18+ required (found v$nodev)." }
Ok "Node v$nodev"

# ---------- 2. Backend deps ----------
Step '2/6 Installing backend dependencies'
# Demo essentials first (everything the prototype needs to train + serve).
$Essentials = @(
  'requests>=2.32', 'tqdm>=4.66', 'numpy>=1.26', 'pandas>=2.2',
  'scipy>=1.13', 'scikit-learn>=1.5', 'joblib', 'pyarrow>=15.0',
  'lightgbm>=4.5', 'fastapi>=0.115', 'uvicorn>=0.30'
)
& python -m pip install --upgrade pip | Out-Null
& python -m pip install @Essentials
Ok 'Backend essentials installed'
# Full stack (GRIB2 readers need the eccodes C library - Conda/WSL2 recommended).
try {
  & python -m pip install -r requirements.txt
  Ok 'Full requirements.txt installed'
} catch {
  Warn 'Full requirements.txt failed (usually cfgrib/eccodes need Conda).'
  Warn 'Run: conda install -c conda-forge eccodes python-eccodes cfgrib'
  Warn 'Demo still runs - only GRIB2 file reading is affected.'
}

# ---------- 3. Frontend ----------
if (-not $SkipBuild) {
  Step '3/6 Installing + building frontend (React -> dashboard/)'
  Push-Location -LiteralPath (Join-Path $Root 'frontend')
  try {
    & npm install --no-audit --no-fund
    & npm run build
  } finally { Pop-Location }
  if (-not (Test-Path (Join-Path $Root 'dashboard\index.html')) -or
      -not (Test-Path (Join-Path $Root 'dashboard\assets'))) {
    throw 'Frontend build did not emit dashboard/index.html + dashboard/assets.'
  }
  Ok 'React bundle built into dashboard/'
} else {
  Step '3/6 Skipped frontend build (-SkipBuild)'
}

# ---------- 4. Pilot model ----------
if (-not $SkipTrain) {
  Step '4/6 Training pilot model (July 2019 monsoon depression)'
  & python -m src.synthetic_pilot
  if (-not (Test-Path (Join-Path $Root 'data\processed\model.joblib'))) {
    throw 'Training did not produce data/processed/model.joblib.'
  }
  Ok 'Model + pilot_samples.parquet ready'
} else {
  Step '4/6 Skipped training (-SkipTrain)'
}

# ---------- 5. Pilot data (optional) ----------
if ($FetchData) {
  Step '5/6 Downloading pilot GEFS slice (~130 MB, 2019071500/c00)'
  & python fetch_data.py gefs --init 2019071500 --var apcp_sfc --member c00
  & python fetch_data.py gefs --init 2019071500 --var tmp_2m  --member c00
  & python fetch_data.py gefs --init 2019071500 --var pres_msl --member c00
  Ok 'GEFS pilot slice present'
} else {
  Step '5/6 Skipped data download (pass -FetchData to fetch it)'
}

# ---------- 6. Serve ----------
Step '6/6 Starting server'
if (-not (Test-PortFree $Port)) {
  throw "Port $Port is busy. Stop the old server first: Get-Process python | Stop-Process"
}

if ($Background) {
  $p = Start-Process -FilePath 'python' -ArgumentList 'src/api/server.py' `
    -WorkingDirectory $Root -PassThru -WindowStyle Normal
  if (Wait-Server $ServerUrl) {
    Ok ("Server running in background (PID " + $p.Id + "). Stop it with: Stop-Process -Id " + $p.Id)
  } else {
    Warn 'Server process started but health check timed out - see its window for errors.'
  }
} else {
  $job = Start-Job -ScriptBlock {
    Set-Location $using:Root; python src/api/server.py
  }
  if (Wait-Server $ServerUrl) {
    Ok 'Server is live'
  } else {
    Warn 'Health check slow - opening browser anyway.'
  }
}

Write-Host ''
Write-Host "  Dashboard : $ServerUrl" -ForegroundColor Green
Write-Host ("  Health    : " + $ServerUrl + "api/v1/health") -ForegroundColor Green
Write-Host ("  Map API   : " + $ServerUrl + "api/v1/confidence-map?date=2019-07-15&lead_day=4") -ForegroundColor Green
Write-Host ''

if (-not $NoBrowser) {
  Start-Process $ServerUrl | Out-Null
  Ok 'Browser opened'
}

if (-not $Background) {
  Write-Host 'Server running in this window. Press Ctrl+C to stop.' -ForegroundColor Yellow
  try {
    # Block until the user stops us; the background job owns the server.
    while ($true) {
      Start-Sleep -Seconds 5
      $failed = Get-Job -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Failed' }
      if ($failed -and ($failed.Count -gt 0)) {
        throw "Server job failed - run 'Receive-Job *' to see the error."
      }
    }
  } finally {
    Get-Job -ErrorAction SilentlyContinue | Stop-Job -ErrorAction SilentlyContinue | Out-Null
    Get-Job -ErrorAction SilentlyContinue | Remove-Job -Force -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process -Filter "Name='python.exe' AND CommandLine LIKE '%src/api/server.py%'" -ErrorAction SilentlyContinue |
      ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Write-Host "Server stopped. Port $Port is free." -ForegroundColor DarkGray
  }
}
