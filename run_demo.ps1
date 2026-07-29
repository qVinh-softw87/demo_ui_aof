$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot

if (Test-Path -LiteralPath ".env") {
    foreach ($line in Get-Content -Encoding utf8 -LiteralPath ".env") {
        if ($line -match '^\s*([^#][^=]*)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            if ($name) {
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
}

if (-not (Test-Path -LiteralPath ".venv313\Scripts\python.exe")) {
    py -3.13 -m venv .venv313
}

& ".venv313\Scripts\python.exe" -m pip install -r requirements.txt
npm.cmd install --prefix frontend
npm.cmd run build --prefix frontend
& ".venv313\Scripts\python.exe" -m backend.scripts.migrate
& ".venv313\Scripts\python.exe" -m backend.scripts.seed_mock_data
& ".venv313\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
