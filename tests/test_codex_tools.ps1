$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Import-Module (Join-Path $repoRoot 'scripts\dev\windows\CodexTools.psm1') -Force
$failures = [System.Collections.Generic.List[string]]::new()

function Assert-True([bool]$Condition, [string]$Message) {
  if (-not $Condition) { $script:failures.Add($Message) }
}

function Assert-Equal($Expected, $Actual, [string]$Message) {
  if ($Expected -ne $Actual) { $script:failures.Add("$Message (expected '$Expected', got '$Actual')") }
}

$fixture = Join-Path $env:TEMP ("bms-codex-tools-{0}" -f [guid]::NewGuid())
New-Item -ItemType Directory -Path $fixture | Out-Null
try {
  $knownNode = Join-Path $fixture 'known\node.exe'
  New-Item -ItemType Directory -Path (Split-Path $knownNode -Parent) | Out-Null
  New-Item -ItemType File -Path $knownNode | Out-Null
  $tool = Find-CodexTool -Name node -RepoRoot $fixture -CommandLookup { param($name) $null } -KnownPaths @($knownNode)
  Assert-Equal (Resolve-Path $knownNode).Path $tool.Path 'tool discovery must use known installed locations'

  $venvPython = Join-Path $fixture '.venv\Scripts\python.exe'
  New-Item -ItemType Directory -Path (Split-Path $venvPython -Parent) | Out-Null
  New-Item -ItemType File -Path $venvPython | Out-Null
  $pathPython = Join-Path $fixture 'path-python.exe'
  New-Item -ItemType File -Path $pathPython | Out-Null
  $tool = Find-CodexTool -Name python -RepoRoot $fixture -CommandLookup { param($name) $pathPython } -KnownPaths @()
  Assert-Equal (Resolve-Path $venvPython).Path $tool.Path 'project Python must take precedence over PATH'

  $parentPath = $env:PATH
  $marker = Join-Path $fixture 'child-only'
  $powershell = (Get-Command powershell.exe).Source
  $result = Invoke-CodexChildProcess -FilePath $powershell `
    -ArgumentList @('-NoProfile', '-Command', '[Environment]::GetEnvironmentVariable(''PATH'',''Process'')') `
    -WorkingDirectory $fixture -PrependPath @($marker) -CaptureOutput
  Assert-True ($result.StdOut.StartsWith($marker)) 'child PATH must contain launcher paths'
  Assert-Equal $parentPath $env:PATH 'launcher must not change parent PATH'

  $result = Invoke-CodexChildProcess -FilePath $powershell -ArgumentList @('-NoProfile', '-Command', 'exit 37') `
    -WorkingDirectory $fixture -CaptureOutput
  Assert-Equal 37 $result.ExitCode 'child exit code must be forwarded exactly'

  try {
    Find-CodexTool -Name node -RepoRoot $fixture -CommandLookup { param($name) $null } -KnownPaths @() | Out-Null
    $failures.Add('missing-tool discovery must fail')
  } catch {
    Assert-True ($_.Exception.Message -match "Missing tool 'node'") 'missing-tool error must name the tool'
  }

  $denied = ConvertTo-CodexLaunchException -Exception ([System.UnauthorizedAccessException]::new('denied')) `
    -FilePath 'C:\tools\denied.exe' -DisplayCommand 'denied-test --version'
  Assert-True ($denied.Message -match 'Permission denied') 'permission-denied error must be explicit'
  Assert-True ($denied.Message -match [regex]::Escape('C:\tools\denied.exe')) 'permission-denied error must name the executable'
  Assert-True ($denied.Message -match 'denied-test --version') 'permission-denied error must include the command'
  $wrappedDenied = ConvertTo-CodexLaunchException `
    -Exception ([System.Management.Automation.MethodInvocationException]::new('wrapped', [System.UnauthorizedAccessException]::new('denied'))) `
    -FilePath 'C:\tools\wrapped-denied.exe'
  Assert-True ($wrappedDenied.Message -match 'Permission denied') 'wrapped permission-denied errors must be explicit'

  $fakeTools = @{
    node = [pscustomobject]@{ Path = 'C:\tools\node.exe' }
    'git-bash' = [pscustomobject]@{ Path = 'C:\Program Files\Git\bin\bash.exe' }
  }
  $quick = Get-CodexInvocationSpec -Command quick -RepoRoot $repoRoot -ToolsByName $fakeTools
  Assert-Equal 'scripts/testing/quick.sh' $quick.Arguments[0] 'quick must run the canonical script directly'
  Assert-True ($quick.Arguments -notcontains '-c') 'Git Bash invocation must not use a nested command string'
  Assert-True ($quick.Arguments -notcontains 'bash') 'Git Bash invocation must not call nested Bash'

  $preview = Get-CodexInvocationSpec -Command preview -RepoRoot $repoRoot -ToolsByName $fakeTools
  Assert-Equal '8765' $preview.Arguments[1] 'preview must default to port 8765'
  $preview = Get-CodexInvocationSpec -Command preview -RepoRoot $repoRoot -ToolsByName $fakeTools -CommandArguments @('9123')
  Assert-Equal '9123' $preview.Arguments[1] 'preview must forward an explicit port'
  Assert-Equal 'scripts/preview-site.sh' $preview.Arguments[0] 'preview must use the existing preview script'
} finally {
  Remove-Item -LiteralPath $fixture -Recurse -Force
}

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}
Write-Host 'Codex Windows tool launcher tests passed'
