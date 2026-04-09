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

function New-DemoPackageAssets {
  param(
    [string]$OutputRoot
  )

  if (Test-Path $OutputRoot) {
    Remove-Item -Path $OutputRoot -Recurse -Force
  }

  $inputsDir = Join-Path $OutputRoot "inputs"
  New-Item -ItemType Directory -Force -Path $inputsDir | Out-Null

  $demoInputs = [ordered]@{
    topic = "Demo topic: Human-in-the-Loop thesis writing workflow"
    language = "English"
    model = "gemini-3.1-pro"
    max_review_rounds = 3
    paper_search_limit = 30
    openalex_api_key = ""
    ark_api_key = ""
    base_url = "http://localhost:8000/v1"
    model_api_key = ""
    auto_resume = $false
  }
  $demoInputsJson = ($demoInputs | ConvertTo-Json -Depth 8)
  [System.IO.File]::WriteAllText(
    (Join-Path $inputsDir "inputs.json"),
    $demoInputsJson + [Environment]::NewLine,
    [System.Text.Encoding]::UTF8
  )

  $demoMarkdownFiles = [ordered]@{
    "existing_material.md" = "# Existing Materials`n`nPaste your existing manuscript materials or notes here.`n"
    "existing_sections.md" = "# Existing Sections`n`nPaste any existing chapter content here.`n"
    "related_works.md" = "# Related Works`n`nAdd your literature review summary here.`n"
    "revision_requests.md" = "# Manual Revision Instructions`n`n### GLOBAL`n- Add your global revision requirements here.`n"
    "write_requests.md" = "# Write Requests`n`nDescribe writing goals, style constraints, and output preferences.`n"
    "research_gaps.md" = "# Research Gaps`n`n(Workflow will update this file.)`n"
  }

  foreach ($name in $demoMarkdownFiles.Keys) {
    [System.IO.File]::WriteAllText(
      (Join-Path $inputsDir $name),
      [string]$demoMarkdownFiles[$name],
      [System.Text.Encoding]::UTF8
    )
  }

  return (Resolve-Path $inputsDir).Path
}

$buildMode = if ($OneFile) { "--onefile" } else { "--onedir" }

$packageAssetsRoot = Join-Path $repoRoot "build/package_assets"
$demoInputsDir = New-DemoPackageAssets -OutputRoot $packageAssetsRoot
Write-Host "[build] demo-only package assets prepared: $demoInputsDir"
Write-Host "[build] personal inputs/projects are excluded from installer payload"

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
  "--hidden-import", "backend_api",
  "--hidden-import", "core.state",
  "--hidden-import", "core.nodes",
  "--hidden-import", "core.llm",
  "--hidden-import", "core.prompts",
  "--hidden-import", "core.project_paths",
  "--add-data", "workflow.py;.",
  "--add-data", "backend_api.py;.",
  "--add-data", "state_dashboard.py;.",
  "--add-data", "core;core",
  "--add-data", "$demoInputsDir;inputs",
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
