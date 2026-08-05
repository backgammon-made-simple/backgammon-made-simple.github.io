[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [string]$Command = 'help',

  [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
  [string[]]$CommandArguments
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
Import-Module (Join-Path $PSScriptRoot 'CodexTools.psm1') -Force

function Show-Usage {
  Write-Host 'Usage: powershell -ExecutionPolicy Bypass -File scripts/codex-tools.ps1 <command> [arguments]'
  Write-Host 'Commands: verify, browser-contract, quick, comprehensive, preview [PORT]'
}

if ($Command -in @('help', '-h', '--help')) { Show-Usage; exit 0 }
if ($Command -notin @('verify', 'browser-contract', 'quick', 'comprehensive', 'preview')) {
  Write-Error "Unknown command '$Command'."
  Show-Usage
  exit 2
}

$required = switch ($Command) {
  'browser-contract' { @('node') }
  'quick' { @('python', 'node', 'git-bash') }
  'preview' { @('python', 'quarto', 'git-bash') }
  default { @('python', 'node', 'npm', 'quarto', 'Rscript', 'git-bash') }
}

try {
  $tools = Resolve-CodexTools -Names $required -RepoRoot $repoRoot
  $environmentPath = Get-CodexEnvironmentPath -Tools $tools
  $toolsByName = @{}
  foreach ($tool in $tools) { $toolsByName[$tool.Name] = $tool }

  Write-Host "Repository: $repoRoot"
  foreach ($tool in $tools) {
    $version = Get-CodexToolVersion -Tool $tool -RepoRoot $repoRoot -EnvironmentPath $environmentPath
    Write-Host ("{0}: {1}" -f $tool.Name, $tool.Path)
    Write-Host ("{0} version: {1}" -f $tool.Name, $version)
  }

  $spec = Get-CodexInvocationSpec -Command $Command -RepoRoot $repoRoot `
    -ToolsByName $toolsByName -CommandArguments $CommandArguments
  $display = @($spec.FilePath) + $spec.Arguments -join ' '
  Write-Host "Running: $display"
  $result = Invoke-CodexChildProcess -FilePath $spec.FilePath -ArgumentList $spec.Arguments `
    -WorkingDirectory $repoRoot -PrependPath $environmentPath -DisplayCommand $display
  exit $result.ExitCode
} catch [System.IO.FileNotFoundException] {
  Write-Error $_.Exception.Message
  exit 127
} catch [System.UnauthorizedAccessException] {
  Write-Error $_.Exception.Message
  exit 126
} catch {
  Write-Error $_.Exception.Message
  exit 1
}

