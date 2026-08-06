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
  Write-Host 'Commands: verify, browser-contract, quick, comprehensive, preview [PORT], preview-smoke [PORT], bootstrap-node'
}

if ($Command -in @('help', '-h', '--help')) { Show-Usage; exit 0 }
if ($Command -notin @('verify', 'browser-contract', 'quick', 'comprehensive', 'preview', 'preview-smoke', 'bootstrap-node')) {
  Write-Host "Unknown command '$Command'."
  Show-Usage
  exit 2
}

$required = switch ($Command) {
  'bootstrap-node' { @() }
  'browser-contract' { @('node') }
  'quick' { @('python', 'node', 'git-bash') }
  'comprehensive' { @('python', 'node', 'quarto', 'git-bash') }
  'preview' { @('python', 'quarto', 'git-bash') }
  'preview-smoke' { @('python', 'quarto', 'git-bash') }
  default { @('python', 'node', 'npm', 'quarto', 'Rscript', 'git-bash') }
}

if ($Command -eq 'bootstrap-node') {
  try {
    $result = Invoke-CodexNodeBootstrap -RepoRoot $repoRoot
    Write-Host ("Source: {0}" -f $result.Source)
    Write-Host ("Destination: {0}" -f $result.Destination)
    exit 0
  } catch {
    Write-Error $_.Exception.Message
    exit 1
  }
}

try {
  $tools = Resolve-CodexTools -Names $required -RepoRoot $repoRoot
  $environmentPath = Get-CodexEnvironmentPath -Tools $tools
  $toolsByName = @{}
  foreach ($tool in $tools) { $toolsByName[$tool.Name] = $tool }

  $originalGitConfigGlobal = $env:GIT_CONFIG_GLOBAL
  $quickGitConfigPath = $null
  try {
    if ($Command -eq 'quick') {
      $quickGitConfigPath = Join-Path $env:TEMP ("bms-quick-safe-{0}.config" -f [guid]::NewGuid())
      Set-Content -Path $quickGitConfigPath -Value "[safe]`n`tdirectory = *`n"
      $env:GIT_CONFIG_GLOBAL = $quickGitConfigPath
    }

    Write-Host "Repository: $repoRoot"
    foreach ($tool in $tools) {
      $version = Get-CodexToolVersion -Tool $tool -RepoRoot $repoRoot -EnvironmentPath $environmentPath
      Write-Host ("{0}: {1}" -f $tool.Name, $tool.Path)
      Write-Host ("{0} version: {1}" -f $tool.Name, $version)
    }

    if ($Command -eq 'preview-smoke') {
      $result = Invoke-CodexPreviewSmoke -RepoRoot $repoRoot -ToolsByName $toolsByName -CommandArguments $CommandArguments
      exit $result
    }

    $spec = Get-CodexInvocationSpec -Command $Command -RepoRoot $repoRoot `
      -ToolsByName $toolsByName -CommandArguments $CommandArguments
    $quickOutputPath = $null
    $quickArguments = [string[]]$spec.Arguments
    if ($Command -eq 'quick') {
      $quickOutputPath = "tmp-quick-output-{0}.log" -f [guid]::NewGuid()
      $quickScript = $quickArguments[1]
      $quickArguments = @(
        $quickArguments[0],
        ("{0} > ./{1} 2>&1" -f $quickScript, $quickOutputPath)
      )
    }
    $display = @($spec.FilePath) + $spec.Arguments
    Write-Host ("Running: {0}" -f ($display -join ' '))
    $result = Invoke-CodexChildProcess -FilePath $spec.FilePath -ArgumentList $quickArguments `
      -WorkingDirectory $repoRoot -PrependPath $environmentPath -DisplayCommand ($display -join ' ')
    if ($quickOutputPath -and (Test-Path -LiteralPath $quickOutputPath -PathType Leaf)) {
      Write-Host (Get-Content -Raw -Path $quickOutputPath)
      Remove-Item -LiteralPath $quickOutputPath -Force -ErrorAction SilentlyContinue
    }
    exit $result.ExitCode
  } finally {
    if ($null -ne $quickGitConfigPath) {
      Remove-Item -LiteralPath $quickGitConfigPath -Force -ErrorAction SilentlyContinue
    }

    if ($originalGitConfigGlobal) {
      $env:GIT_CONFIG_GLOBAL = $originalGitConfigGlobal
    } else {
      Remove-Item Env:GIT_CONFIG_GLOBAL -ErrorAction SilentlyContinue
    }
  }
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
