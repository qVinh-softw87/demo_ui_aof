$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $projectRoot
$envPath = Join-Path $projectRoot ".env"

if (Test-Path -LiteralPath $envPath) {
    foreach ($line in Get-Content -Encoding utf8 -LiteralPath $envPath) {
        if ($line -match '^\s*([^#][^=]*)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim().Trim('"').Trim("'")
            if ($name) {
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
}

if (-not $env:AQ_AUTH_SECRET -or $env:AQ_AUTH_SECRET -eq "development-only-change-me-before-production") {
    $secretBytes = New-Object byte[] 48
    $randomGenerator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $randomGenerator.GetBytes($secretBytes)
    } finally {
        $randomGenerator.Dispose()
    }
    $generatedSecret = [Convert]::ToBase64String($secretBytes)
    $existing = if (Test-Path -LiteralPath $envPath) {
        Get-Content -Raw -Encoding utf8 -LiteralPath $envPath
    } else {
        ""
    }
    if ($existing -match '(?m)^AQ_AUTH_SECRET=.*$') {
        $existing = $existing -replace '(?m)^AQ_AUTH_SECRET=.*$', "AQ_AUTH_SECRET=$generatedSecret"
    } else {
        $existing = $existing.TrimEnd() + [Environment]::NewLine + "AQ_AUTH_SECRET=$generatedSecret" + [Environment]::NewLine
    }
    Set-Content -Encoding utf8 -NoNewline -LiteralPath $envPath -Value $existing
    $env:AQ_AUTH_SECRET = $generatedSecret
}

# Codex/sandbox sessions may inject a loopback proxy that intentionally blocks
# outbound traffic. Never pass that sentinel into the long-running production
# process; keep any real user/corporate proxy unchanged.
foreach ($proxyName in @("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY")) {
    $proxyValue = [Environment]::GetEnvironmentVariable($proxyName, "Process")
    if ($proxyValue -match '^https?://127\.0\.0\.1:9/?$') {
        [Environment]::SetEnvironmentVariable($proxyName, $null, "Process")
    }
}
$localNoProxy = "127.0.0.1,localhost"
if ($env:NO_PROXY) {
    $localNoProxy = "$localNoProxy,$env:NO_PROXY"
}
$env:NO_PROXY = $localNoProxy

$env:AQ_ENV = "production"
$env:AQ_AUTH_REQUIRED = "true"
if (-not $env:LLM_PROVIDER) {
    $env:LLM_PROVIDER = "deterministic"
}

if (-not (Test-Path -LiteralPath ".venv313\Scripts\python.exe")) {
    py -3.13 -m venv .venv313
}

& ".venv313\Scripts\python.exe" -m pip install -r requirements.txt
npm.cmd install --prefix frontend
npm.cmd run build --prefix frontend
& ".venv313\Scripts\python.exe" -m backend.scripts.migrate
& ".venv313\Scripts\python.exe" -m backend.scripts.seed_mock_data
& ".venv313\Scripts\python.exe" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --proxy-headers
