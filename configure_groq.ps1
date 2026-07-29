param(
    [switch]$FromClipboard
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$envPath = Join-Path $projectRoot ".env"

if ($FromClipboard) {
    $apiKey = (Get-Clipboard -Raw).Trim()
} else {
    $secureKey = Read-Host "Dán Groq API key (nội dung sẽ được ẩn)" -AsSecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
    try {
        $apiKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

if (-not $apiKey.StartsWith("gsk_")) {
    throw "Giá trị không có định dạng Groq API key hợp lệ."
}

$preserved = @()
if (Test-Path -LiteralPath $envPath) {
    $preserved = Get-Content -Encoding utf8 -LiteralPath $envPath |
        Where-Object {
            $_ -notmatch '^\s*GROQ_API_KEY\s*=' -and
            $_ -notmatch '^\s*GROQ_MODEL\s*=' -and
            $_ -notmatch '^\s*LLM_PROVIDER\s*='
        }
}

$lines = @(
    $preserved
    "GROQ_API_KEY=$apiKey"
    "GROQ_MODEL=openai/gpt-oss-20b"
    "LLM_PROVIDER=groq"
) | Where-Object { $_ -ne $null }

$lines | Set-Content -Encoding utf8 -LiteralPath $envPath
$apiKey = $null
[GC]::Collect()

Write-Host "Đã lưu Groq API key và đặt LLM_PROVIDER=groq."
Write-Host "Hãy khởi động lại run_demo.ps1 để áp dụng."
