# Starts FlameIntel: FastAPI backend (port 8000) + Next.js dashboard (port 3000).
# Usage (from the project folder):  powershell -ExecutionPolicy Bypass -File .\start.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3.12 is required (python not found)." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node.js LTS is required (install: winget install OpenJS.NodeJS.LTS), then reopen the terminal." }
if (-not (Test-Path "$root\.env")) { Write-Warning ".env not found: the assistant needs it (copy .env.example and add your key). The rest of the dashboard still works." }

Push-Location $root
python -c "import fastapi, uvicorn, pandas, openpyxl, xlrd, chromadb, fastembed" 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "Installing Python packages..."; python -m pip install -r requirements.txt -r api\requirements.txt }
if (-not (Test-Path "api\data\investigations.json")) { Write-Host "Building investigation records..."; python api\build_investigations.py }
if (-not (Test-Path "api\data\insights.json")) { Write-Warning "api\data\insights.json missing: Insights page will be empty. Run: python api\build_insights.py" }
Pop-Location

if (-not (Test-Path "$root\dashboard\node_modules")) { Write-Host "Installing dashboard packages..."; Push-Location "$root\dashboard"; npm install --no-audit --no-fund; Pop-Location }

Write-Host "Starting API on http://localhost:8000 (loads the index, ~20-30 s)..."
Start-Process -FilePath "cmd.exe" -WorkingDirectory $root -ArgumentList "/k","title FlameIntel API && python -m uvicorn api.main:app --port 8000"
Write-Host "Starting dashboard on http://localhost:3000 ..."
Start-Process -FilePath "cmd.exe" -WorkingDirectory "$root\dashboard" -ArgumentList "/k","title FlameIntel Web && npm run dev"

Start-Sleep -Seconds 12
Start-Process "http://localhost:3000"
Write-Host "Done. Close the two console windows to stop."
