param(
  [string]$PythonExe = ".venv/Scripts/python.exe",
  [ValidateSet("onefile", "onedir")]
  [string]$BackendMode = "onefile",
  [switch]$IncludeOptionalTlsBackends,
  [switch]$SkipBackend
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Host "[setup] build full desktop package (frontend + backend sidecar)"

$bundleScript = Join-Path $repoRoot "scripts/build_desktop_bundle.ps1"
if (-not (Test-Path $bundleScript)) {
  throw "Bundle script not found: $bundleScript"
}

$bundleArgs = @{
  PythonExe = $PythonExe
  BackendMode = $BackendMode
}
if ($IncludeOptionalTlsBackends) {
  $bundleArgs.IncludeOptionalTlsBackends = $true
}
if ($SkipBackend) {
  $bundleArgs.SkipBackend = $true
}

& $bundleScript @bundleArgs
if ($LASTEXITCODE -ne 0) {
  throw "Desktop setup build failed with exit code $LASTEXITCODE"
}

Write-Host "[done] desktop setup build complete"
Write-Host "artifact: desktop_ui/src-tauri/target/release/bundle"
