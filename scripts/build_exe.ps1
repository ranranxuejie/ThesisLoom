param(
  [string]$PythonExe = ".venv/Scripts/python.exe",
  [string]$NpmCmd = "npm",
  [ValidateSet("onefile", "onedir")]
  [string]$BackendMode = "onefile",
  [switch]$IncludeOptionalTlsBackends
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

Write-Warning "[deprecated] scripts/build_exe.ps1 was the legacy Streamlit packer and is no longer maintained."
Write-Host "[build] Use unified desktop bundle pipeline instead."

$args = @(
  "-PythonExe", $PythonExe,
  "-NpmCmd", $NpmCmd,
  "-BackendMode", $BackendMode
)
if ($IncludeOptionalTlsBackends) {
  $args += "-IncludeOptionalTlsBackends"
}

& (Join-Path $repoRoot "scripts/build_desktop_bundle.ps1") @args
if ($LASTEXITCODE -ne 0) {
  throw "Desktop bundle build failed with exit code $LASTEXITCODE"
}
