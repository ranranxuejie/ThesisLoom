param(
  [switch]$OneFile,
  [string]$PythonExe = "C:/ProgramData/anaconda3/envs/ENV2026/python.exe"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

if (-not (Test-Path $PythonExe)) {
  throw "Python executable not found: $PythonExe"
}

$pythonRoot = Split-Path -Parent $PythonExe
$condaBinDir = Join-Path $pythonRoot "Library/bin"
$sitePackagesDir = Join-Path $pythonRoot "Lib/site-packages"

$legacyProtobufEgg = Join-Path $sitePackagesDir "protobuf-3.10.0-py3.11.egg"
$legacyProtobufEggDisabled = "$legacyProtobufEgg.disabled_for_pyinstaller"
$legacyProtobufRenamed = $false

if (Test-Path $legacyProtobufEgg) {
  if (Test-Path $legacyProtobufEggDisabled) {
    Remove-Item -Recurse -Force $legacyProtobufEggDisabled
  }
  Rename-Item -Path $legacyProtobufEgg -NewName (Split-Path -Leaf $legacyProtobufEggDisabled)
  $legacyProtobufRenamed = $true
  Write-Host "[build] temporarily disabled legacy protobuf egg: $legacyProtobufEgg"
}

$buildMode = if ($OneFile) { "--onefile" } else { "--onedir" }

Write-Host "[build] install/update pyinstaller"
& $PythonExe -m pip install --upgrade pyinstaller | Out-Null

$pyiArgs = @(
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  $buildMode,
  "--name", "ThesisLoom",
  "--additional-hooks-dir", "scripts/pyinstaller_hooks",
  "--collect-all", "streamlit",
  "--collect-all", "webview",
  "--collect-submodules", "core",
  "--hidden-import", "webview",
  "--hidden-import", "workflow",
  "--hidden-import", "state_dashboard",
  "--hidden-import", "core.state",
  "--hidden-import", "core.nodes",
  "--hidden-import", "core.llm",
  "--hidden-import", "core.prompts",
  "--hidden-import", "core.project_paths",
  "--add-data", "streamlit_app.py;.",
  "--add-data", "state_dashboard.py;.",
  "--add-data", "workflow.py;.",
  "--add-data", "core;core",
  "--add-data", "inputs;inputs",
  "--add-data", "README.md;.",
  "main.py"
)

# Conda environments often need explicit MKL/OpenMP runtime DLL bundling.
if (Test-Path $condaBinDir) {
  $mklDlls = Get-ChildItem $condaBinDir -Filter "mkl_*.dll" -ErrorAction SilentlyContinue
  foreach ($dll in $mklDlls) {
    $pyiArgs += @("--add-binary", "$($dll.FullName);.")
  }

  foreach ($dllName in @("libiomp5md.dll", "tbb12.dll", "tbbmalloc.dll")) {
    $dllPath = Join-Path $condaBinDir $dllName
    if (Test-Path $dllPath) {
      $pyiArgs += @("--add-binary", "$dllPath;.")
    }
  }
}

try {
  Write-Host "[build] running: $PythonExe $($pyiArgs -join ' ')"
  & $PythonExe @pyiArgs
  if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
  }
}
finally {
  if ($legacyProtobufRenamed -and (Test-Path $legacyProtobufEggDisabled)) {
    Rename-Item -Path $legacyProtobufEggDisabled -NewName (Split-Path -Leaf $legacyProtobufEgg)
    Write-Host "[build] restored legacy protobuf egg"
  }
}

Write-Host "[done] build complete"
if ($OneFile) {
  Write-Host "artifact: dist/ThesisLoom.exe"
} else {
  Write-Host "artifact: dist/ThesisLoom/ThesisLoom.exe"
}
