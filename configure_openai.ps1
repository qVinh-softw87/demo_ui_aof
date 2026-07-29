param(
    [switch]$FromClipboard
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $projectRoot ".env"

if ($FromClipboard) {
    $apiKey = (Get-Clipboard -Raw).Trim()
} else {
    $secureKey = Read-Host "Dán API key mới (nội dung sẽ được ẩn)" -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try {
        $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

if (-not $apiKey.StartsWith("sk-")) {
    throw "Giá trị không có định dạng API key OpenAI hợp lệ."
}

$preserved = @()
if (Test-Path -LiteralPath $envPath) {
    $preserved = Get-Content -Encoding utf8 -LiteralPath $envPath |
        Where-Object {
            $_ -notmatch '^\s*OPENAI_API_KEY\s*=' -and
            $_ -notmatch '^\s*OPENAI_MODEL\s*='
        }
}

$lines = @(
    $preserved
    "OPENAI_API_KEY=$apiKey"
    "OPENAI_MODEL=gpt-5.6-sol"
) | Where-Object { $_ -ne $null }

$lines | Set-Content -Encoding utf8 -LiteralPath $envPath
$apiKey = $null
[GC]::Collect()

Write-Host "Đã lưu cấu hình OpenAI vào .env (đã được .gitignore bảo vệ)."
Write-Host "Hãy khởi động lại run_demo.ps1 để áp dụng."
