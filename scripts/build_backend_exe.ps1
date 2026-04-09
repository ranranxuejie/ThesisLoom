param(
  [switch]$OneFile,
  [switch]$IncludeOptionalTlsBackends,
  [string]$PythonExe = ".venv/Scripts/python.exe"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $repoRoot

$pythonPath = $PythonExe
if (-not [System.IO.Path]::IsPathRooted($pythonPath)) {
  $pythonPath = Join-Path $repoRoot $pythonPath
}

if (-not (Test-Path $pythonPath)) {
  throw "Python executable not found: $pythonPath (tip: create venv first: python -m venv .venv)"
}

$PythonExe = (Resolve-Path $pythonPath).Path

$buildMode = if ($OneFile) { "--onefile" } else { "--onedir" }

$baseExcludes = @(
  "streamlit",
  "streamlit_autorefresh",
  "webview",
  "pywebview",
  "fastapi",
  "uvicorn",
  "matplotlib",
  "seaborn",
  "plotly",
  "pandas",
  "numpy",
  "scipy",
  "sklearn",
  "torch",
  "tensorflow",
  "IPython"
)

$trimExcludes = @(
  "OpenSSL",
  "cryptography",
  "urllib3.contrib.pyopenssl"
)

if (-not $IncludeOptionalTlsBackends) {
  $baseExcludes += $trimExcludes
  Write-Host "[build] size trim enabled: exclude optional TLS backends (OpenSSL/cryptography)"
} else {
  Write-Host "[build] optional TLS backends retained"
}

$excludeArgs = @()
foreach ($moduleName in $baseExcludes) {
  $excludeArgs += @("--exclude-module", $moduleName)
}

Write-Host "[build] verify pyinstaller"
$pyinstallerReady = $false
$oldErrorPreference = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& $PythonExe -m PyInstaller --version *> $null
$pyinstallerReady = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $oldErrorPreference

if (-not $pyinstallerReady) {
  Write-Host "[build] pyinstaller not found, installing"
  & $PythonExe -m pip install pyinstaller | Out-Null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "[build] default index install failed, retry from https://pypi.org/simple"
    & $PythonExe -m pip install -i https://pypi.org/simple pyinstaller | Out-Null
  }
  if ($LASTEXITCODE -ne 0) {
    throw "Failed to install pyinstaller in selected environment"
  }
}

$pyiArgs = @(
  "-m", "PyInstaller",
  "--noconfirm",
  "--clean",
  $buildMode,
  "--noconsole",
  "--name", "ThesisLoomBackend",
  "--additional-hooks-dir", "scripts/pyinstaller_hooks",
  "--optimize", "2",
  "--collect-submodules", "core",
  "--hidden-import", "workflow",
  "--hidden-import", "state_dashboard",
  "--hidden-import", "core.state",
  "--hidden-import", "core.nodes",
  "--hidden-import", "core.llm",
  "--hidden-import", "core.prompts",
  "--hidden-import", "core.project_paths",
  "--add-data", "workflow.py;.",
  "--add-data", "state_dashboard.py;.",
  "--add-data", "core;core",
  "--add-data", "inputs;inputs",
  "--add-data", "README.md;."
)

$pyiArgs += $excludeArgs
$pyiArgs += "desktop_backend.py"

Write-Host "[build] running: $PythonExe $($pyiArgs -join ' ')"
& $PythonExe @pyiArgs
if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller failed with exit code $LASTEXITCODE"
}

Write-Host "[done] build complete"
if ($OneFile) {
  Write-Host "artifact: dist/ThesisLoomBackend.exe"
} else {
  Write-Host "artifact: dist/ThesisLoomBackend/ThesisLoomBackend.exe"
}
