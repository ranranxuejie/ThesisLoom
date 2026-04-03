param(
  [string]$InnoCompiler = "",
  [string]$InstallerScript = "installer/ThesisLoom.iss"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Test-Path $InstallerScript)) {
  throw "Installer script not found: $InstallerScript"
}

if (-not (Test-Path "dist/ThesisLoom/ThesisLoom.exe")) {
  throw "Missing EXE artifact: dist/ThesisLoom/ThesisLoom.exe. Run ./scripts/build_exe.ps1 first."
}

if (-not (Test-Path "dist/ThesisLoom/_internal")) {
  throw "Missing internal folder: dist/ThesisLoom/_internal. Run ./scripts/build_exe.ps1 first."
}

$candidates = @()
if ($InnoCompiler) {
  $candidates += $InnoCompiler
}
$candidates += @(
  "C:/Program Files (x86)/Inno Setup 6/ISCC.exe",
  "C:/Program Files/Inno Setup 6/ISCC.exe"
)

$compilerPath = $null
foreach ($candidate in $candidates) {
  if (Test-Path $candidate) {
    $compilerPath = (Resolve-Path $candidate).Path
    break
  }
}

if (-not $compilerPath) {
  throw "Inno Setup compiler not found. Install Inno Setup 6 or pass -InnoCompiler <path-to-ISCC.exe>."
}

Write-Host "[setup] using compiler: $compilerPath"
Write-Host "[setup] building installer from: $InstallerScript"

& $compilerPath $InstallerScript
if ($LASTEXITCODE -ne 0) {
  throw "Installer build failed with exit code $LASTEXITCODE"
}

Write-Host "[done] installer build complete"
Write-Host "artifact: dist/installer/ThesisLoomSetup.exe"
