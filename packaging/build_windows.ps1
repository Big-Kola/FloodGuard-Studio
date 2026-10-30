param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
Set-Location $Root

if (-not (Test-Path $Python)) {
    Write-Host "Creating Python 3.11 virtual environment..."
    py -3.11 -m venv (Join-Path $Root ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}

Write-Host "Installing pinned build dependencies..."
& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root "requirements-dev.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

if (-not $SkipTests) {
    Write-Host "Running the automated test suite..."
    $env:QT_QPA_PLATFORM = "offscreen"
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "Tests failed; packaging stopped." }
}

Write-Host "Building FloodGuard Studio with PyInstaller..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath (Join-Path $Root "dist") `
    --workpath (Join-Path $Root "build") `
    (Join-Path $PSScriptRoot "FloodGuardStudio.spec")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$Output = Join-Path $Root "dist\FloodGuardStudio"
Write-Host ""
Write-Host "Build complete: $Output"
Write-Host "Executable: $Output\FloodGuardStudio.exe"
Write-Host "The executable is unsigned. Sign it before public distribution."
