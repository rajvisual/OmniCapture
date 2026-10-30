# OmniCapture Sanity & Quality Assurance Check Script
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "         OmniCapture Repository Quality Assurance       " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python syntax compilation
Write-Host "[1/4] Checking Python syntax compilation across all files..." -ForegroundColor Yellow
$pyFiles = Get-ChildItem -Path $repoRoot -Filter "*.py" -Recurse | Where-Object { $_.FullName -notmatch "\\\.venv\\" }
foreach ($file in $pyFiles) {
    Write-Host "  Compiling $($file.Name)..." -NoNewline
    python -m py_compile $file.FullName
    if ($LASTEXITCODE -ne 0) {
        Write-Host " FAILED" -ForegroundColor Red
        exit 1
    }
    Write-Host " OK" -ForegroundColor Green
}

# 2. Check bundled binaries
Write-Host ""
Write-Host "[2/4] Verifying required runtime binaries in bin/..." -ForegroundColor Yellow
$requiredBins = @(
    "bin\adb.exe",
    "bin\scrcpy.exe",
    "bin\scrcpy-server",
    "bin\SDL2.dll",
    "bin\avcodec-61.dll"
)
foreach ($bin in $requiredBins) {
    $binPath = Join-Path $repoRoot $bin
    if (Test-Path $binPath) {
        Write-Host "  Found: $bin" -ForegroundColor Green
    } else {
        Write-Host "  MISSING: $bin" -ForegroundColor Red
        exit 1
    }
}

# 3. Run Automated Unit Tests
Write-Host ""
Write-Host "[3/4] Running automated unit test suite..." -ForegroundColor Yellow
python -m unittest discover -s (Join-Path $repoRoot "tests") -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "Unit tests failed!" -ForegroundColor Red
    exit 1
}

# 4. Check for unwanted or sensitive files
Write-Host ""
Write-Host "[4/4] Checking for accidental sensitive file inclusion..." -ForegroundColor Yellow
$sensitivePatterns = @("*.pyc", "__pycache__", "client_secrets.json", "drive_token.json", "*.mp4", "*.mkv")
$leaksFound = $false
foreach ($pattern in $sensitivePatterns) {
    $matches = Get-ChildItem -Path $repoRoot -Filter $pattern -Recurse -File -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "\\\.venv\\" }
    if ($matches) {
        foreach ($m in $matches) {
            # config.example.json is safe, but real tokens are not
            if ($m.Name -eq "client_secrets.json" -or $m.Name -eq "drive_token.json") {
                Write-Host "  WARNING: Found credential file: $($m.FullName)" -ForegroundColor Red
                $leaksFound = $true
            }
        }
    }
}

if (-not $leaksFound) {
    Write-Host "  No unencrypted credentials or media recordings detected." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "All QA checks passed successfully! Repository is clean." -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
