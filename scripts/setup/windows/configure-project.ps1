[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
Set-Location $RepoRoot

foreach ($required in @('social_generator/requirements-social.txt', 'social_generator/requirements-social.R', 'site/_quarto.yml')) {
  if (-not (Test-Path $required -PathType Leaf)) { throw "Missing repository dependency source: $required" }
}
foreach ($command in @('py', 'Rscript', 'quarto')) {
  if (-not (Get-Command $command -ErrorAction SilentlyContinue)) { throw "Required system tool is missing: $command" }
}
$pythonParts = & py -c 'import sys; print(sys.version_info[0]); print(sys.version_info[1])'
$pythonVersion = "$($pythonParts[0]).$($pythonParts[1])"
if ([version]$pythonVersion -lt [version]'3.11') { throw "Python 3.11+ is required by testing-sop.md; found $pythonVersion" }
$quartoVersion = (& quarto --version | Select-Object -First 1).Trim()
if ($quartoVersion -ne '1.10.15') { throw "Quarto 1.10.15 is required by scripts/bms-setup-server-environment.sh; found $quartoVersion" }

$venv = Join-Path $RepoRoot '.venv'
$python = Join-Path $venv 'Scripts/python.exe'
if (-not (Test-Path $python -PathType Leaf)) {
  & py -m venv $venv
}

& $python -m pip install --upgrade pip
& $python -m pip install -r 'social_generator/requirements-social.txt'
& $python -m pip check
& $python -m playwright install chromium

$rLibrary = Join-Path $RepoRoot '.r-library'
New-Item -ItemType Directory -Force -Path $rLibrary | Out-Null
$env:R_LIBS_USER = $rLibrary
& Rscript --vanilla -e 'source("social_generator/requirements-social.R"); stopifnot(requireNamespace("yaml", quietly = TRUE))'

Write-Host 'Project configuration completed.'
