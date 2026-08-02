[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$RepoRoot
)

$ErrorActionPreference = 'Stop'
$failures = [System.Collections.Generic.List[string]]::new()
Set-Location $RepoRoot

foreach ($required in @('site/_quarto.yml', 'social_generator/requirements-social.txt', 'social_generator/requirements-social.R')) {
  if (Test-Path $required -PathType Leaf) { Write-Host "PASS source: $required" } else { $failures.Add("missing source: $required") }
}

foreach ($command in @('git', 'bash', 'py', 'node', 'quarto', 'Rscript')) {
  $tool = Get-Command $command -ErrorAction SilentlyContinue
  if ($tool) { Write-Host "PASS tool: $command ($($tool.Source))" } else { $failures.Add("missing system tool: $command") }
}

if (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonParts = & py -c 'import sys; print(sys.version_info[0]); print(sys.version_info[1])'
  $pythonVersion = "$($pythonParts[0]).$($pythonParts[1])"
  if ([version]$pythonVersion -ge [version]'3.11') { Write-Host "PASS Python version: $pythonVersion" } else { $failures.Add("Python 3.11+ required by testing-sop.md; found $pythonVersion") }
}
if (Get-Command quarto -ErrorAction SilentlyContinue) {
  $quartoVersion = (& quarto --version | Select-Object -First 1).Trim()
  if ($quartoVersion -eq '1.10.15') { Write-Host "PASS Quarto version: $quartoVersion" } else { $failures.Add("Quarto 1.10.15 required by server setup evidence; found $quartoVersion") }
}

$venvPython = Join-Path $RepoRoot '.venv/Scripts/python.exe'
if (Test-Path $venvPython -PathType Leaf) {
  Write-Host "PASS local Python: $venvPython"
  & $venvPython -m pip check
} else {
  $failures.Add('missing repository-local Python environment: .venv/Scripts/python.exe')
}

if (Test-Path (Join-Path $RepoRoot '.r-library') -PathType Container) { Write-Host 'PASS local R library: .r-library' } else { $failures.Add('missing repository-local R library: .r-library') }

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Host "FAIL $_" }
  exit 1
}

Write-Host 'PASS: Windows developer-tooling verification.'
