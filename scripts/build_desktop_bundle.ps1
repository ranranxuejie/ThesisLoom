param(
  [string]$PythonExe = ".venv/Scripts/python.exe",
  [string]$NpmCmd = "npm",
  [ValidateSet("onefile", "onedir")]
  [string]$BackendMode = "onefile",
  [switch]$IncludeOptionalTlsBackends,
  [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

function Resolve-PathSafe([string]$pathValue) {
  $candidate = $pathValue
  if (-not [System.IO.Path]::IsPathRooted($candidate)) {
    $candidate = Join-Path $repoRoot $candidate
  }
  if (-not (Test-Path $candidate)) {
    throw "Path not found: $candidate"
  }
  return (Resolve-Path $candidate).Path
}

if (-not (Get-Command $NpmCmd -ErrorAction SilentlyContinue)) {
  throw "npm command not found: $NpmCmd"
}

$pythonPath = Resolve-PathSafe $PythonExe

if (-not $SkipBackend) {
  Write-Host "[bundle] step 1/3: build backend executable (mode=$BackendMode)"
  $backendBuildArgs = @("-PythonExe", $pythonPath)
  if ($BackendMode -eq "onefile") {
    $backendBuildArgs += "-OneFile"
  }
  if ($IncludeOptionalTlsBackends) {
    $backendBuildArgs += "-IncludeOptionalTlsBackends"
  }
  & (Join-Path $repoRoot "scripts/build_backend_exe.ps1") @backendBuildArgs
  if ($LASTEXITCODE -ne 0) {
    throw "Backend build failed with exit code $LASTEXITCODE"
  }
} else {
  Write-Host "[bundle] skip backend build"
}

$backendCandidates = @(
  (Join-Path $repoRoot "dist/ThesisLoomBackend.exe"),
  (Join-Path $repoRoot "dist/ThesisLoomBackend/ThesisLoomBackend.exe")
)
$backendExe = $backendCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $backendExe) {
  throw "Missing backend artifact, checked: $($backendCandidates -join ', ')"
}

if ($backendExe -like "*dist\ThesisLoomBackend\ThesisLoomBackend.exe") {
  Write-Warning "[bundle] onedir backend artifact detected; recommend BackendMode=onefile for standalone sidecar delivery."
}

$sidecarDir = Join-Path $repoRoot "desktop_ui/src-tauri/bin"
New-Item -ItemType Directory -Force -Path $sidecarDir | Out-Null
$sidecarPath = Join-Path $sidecarDir "ThesisLoomBackend-x86_64-pc-windows-msvc.exe"
Copy-Item -Path $backendExe -Destination $sidecarPath -Force
Write-Host "[bundle] sidecar copied: $sidecarPath"

Write-Host "[bundle] step 2/3: install ui dependencies"
Set-Location (Join-Path $repoRoot "desktop_ui")
if (Test-Path "package-lock.json") {
  & $NpmCmd ci
} else {
  & $NpmCmd install
}
if ($LASTEXITCODE -ne 0) {
  throw "npm install failed with exit code $LASTEXITCODE"
}

Write-Host "[bundle] step 3/3: build tauri bundle"
& $NpmCmd run tauri build
if ($LASTEXITCODE -ne 0) {
  Write-Warning "[bundle] tauri installer bundle failed, fallback to --no-bundle"
  & $NpmCmd run tauri build -- --no-bundle
  if ($LASTEXITCODE -ne 0) {
    throw "tauri build failed with exit code $LASTEXITCODE"
  }
}

Write-Host "[done] full desktop bundle complete"
Write-Host "backend: $backendExe"
Write-Host "tauri app: desktop_ui/src-tauri/target/release/thesisloom_desktop.exe"
Write-Host "tauri bundle: desktop_ui/src-tauri/target/release/bundle"
