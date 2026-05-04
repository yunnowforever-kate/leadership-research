# 리더십 리서치 자동화 - 설치 및 실행 스크립트 (PowerShell)
# 실행: 우클릭 → "PowerShell로 실행" 또는 터미널에서: .\setup_and_run.ps1

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  리더십 리서치 자동화 - 초기 설정" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# ── 1. Python 경로 탐색 ────────────────────────────────────────────────────
$python = $null
$candidates = @(
    "python",
    "python3",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe"
)
foreach ($c in $candidates) {
    try {
        $ver = & $c --version 2>&1
        if ($ver -match "Python 3") {
            $python = $c
            Write-Host "[OK] Python 발견: $c ($ver)" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $python) {
    Write-Host ""
    Write-Host "[오류] Python 3이 설치되어 있지 않습니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "설치 방법 (둘 중 하나):" -ForegroundColor Yellow
    Write-Host "  1. Microsoft Store: 검색창에 'Python 3.12' 검색 후 설치"
    Write-Host "  2. 공식 사이트: https://www.python.org/downloads/"
    Write-Host "     → 설치 시 'Add Python to PATH' 체크 필수!"
    Write-Host ""
    Write-Host "설치 후 이 스크립트를 다시 실행하세요."
    Read-Host "엔터를 눌러 종료"
    exit 1
}

# ── 2. ANTHROPIC_API_KEY 확인 ──────────────────────────────────────────────
if (-not $env:ANTHROPIC_API_KEY) {
    Write-Host ""
    Write-Host "[입력 필요] ANTHROPIC_API_KEY를 입력하세요." -ForegroundColor Yellow
    Write-Host "  Anthropic Console(https://console.anthropic.com)에서 발급"
    $key = Read-Host "API Key (sk-ant-...)"
    if (-not $key.StartsWith("sk-")) {
        Write-Host "[경고] API 키 형식이 올바르지 않습니다." -ForegroundColor Red
    }
    $env:ANTHROPIC_API_KEY = $key
}
Write-Host "[OK] ANTHROPIC_API_KEY 설정됨" -ForegroundColor Green

# ── 3. 패키지 설치 ─────────────────────────────────────────────────────────
Write-Host ""
Write-Host "패키지 설치 중..." -ForegroundColor Cyan
Set-Location $ScriptDir
& $python -m pip install -r requirements.txt --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[오류] 패키지 설치 실패" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] 패키지 설치 완료" -ForegroundColor Green

# ── 4. 실행 ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  리서치 자동화 실행" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$args_extra = ""
if ($args -contains "--no-cache") { $args_extra = "--no-cache" }

& $python main_orchestrator.py $args_extra

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "완료! outputs\ 폴더에서 .docx 파일을 확인하세요." -ForegroundColor Green
    # 파일 탐색기로 outputs 폴더 열기
    Start-Process explorer.exe -ArgumentList (Join-Path $ScriptDir "outputs")
} else {
    Write-Host "[오류] 실행 실패 (종료 코드: $LASTEXITCODE)" -ForegroundColor Red
}

Read-Host "엔터를 눌러 종료"
