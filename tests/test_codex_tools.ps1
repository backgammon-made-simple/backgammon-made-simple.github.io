$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Import-Module (Join-Path $repoRoot 'scripts\dev\windows\CodexTools.psm1') -Force
$failures = [System.Collections.Generic.List[string]]::new()
$skips = [System.Collections.Generic.List[string]]::new()

function Add-Failure([string]$Message) {
  $script:failures.Add($Message)
}

function Add-Skip([string]$Message) {
  $script:skips.Add($Message)
}

function Assert-True([bool]$Condition, [string]$Message) {
  if (-not $Condition) { Add-Failure $Message }
}

function Assert-Equal($Expected, $Actual, [string]$Message) {
  if ($Expected -ne $Actual) {
    Add-Failure "$Message (expected '$Expected', got '$Actual')"
  }
}

function Invoke-Launcher([string[]]$Arguments) {
  $powershell = (Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
  $launcher = Join-Path $repoRoot 'scripts\dev\windows\codex-tools.ps1'
  $argumentList = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $launcher)
  $argumentList += $Arguments
  $global:LASTEXITCODE = 0
  & $powershell @argumentList | Out-Host
  return [pscustomobject]@{ ExitCode = $global:LASTEXITCODE; StdOut = ''; StdErr = '' }
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
  $powershell = (Get-Command powershell.exe -CommandType Application).Source
  $result = Invoke-CodexChildProcess -FilePath $powershell `
    -ArgumentList @('-NoProfile', '-Command', '[Environment]::GetEnvironmentVariable(''PATH'',''Process'')') `
    -WorkingDirectory $fixture -PrependPath @($marker) -CaptureOutput
  Assert-True ($result.StdOut.TrimStart().StartsWith($marker)) 'child PATH must contain launcher paths'
  Assert-Equal $parentPath $env:PATH 'launcher must not change parent PATH'

  $pathEnv = Get-CodexEnvironmentPath -Tools @(
    [pscustomobject]@{ Name = 'python'; Path = (Join-Path $fixture '.venv\Scripts\python.exe') },
    [pscustomobject]@{ Name = 'node'; Path = $knownNode },
    [pscustomobject]@{ Name = 'quarto'; Path = (Join-Path $fixture 'quarto.exe') },
    [pscustomobject]@{ Name = 'Rscript'; Path = (Join-Path $fixture 'Rscript.exe') },
    [pscustomobject]@{ Name = 'git-bash'; Path = (Join-Path $fixture 'bash.exe') }
  )
  Assert-True ($pathEnv -contains (Split-Path $venvPython -Parent)) 'child PATH includes project python directory'
  Assert-True ($pathEnv -contains (Split-Path $knownNode -Parent)) 'child PATH includes node directory'
  Assert-True ($pathEnv -contains (Split-Path (Join-Path $fixture 'quarto.exe') -Parent)) 'child PATH includes quarto directory'
  Assert-True ($pathEnv -contains (Split-Path (Join-Path $fixture 'Rscript.exe') -Parent)) 'child PATH includes R directory'

  $result = Invoke-CodexChildProcess -FilePath $powershell -ArgumentList @('-NoProfile', '-Command', 'exit 37') `
    -WorkingDirectory $fixture -CaptureOutput
  Assert-Equal 37 $result.ExitCode 'child exit code must be forwarded exactly'

  try {
    Find-CodexTool -Name node -RepoRoot $fixture -CommandLookup { param($name) $null } -KnownPaths @() | Out-Null
    Add-Failure 'missing-tool discovery must fail'
  } catch {
    Assert-True ($_.Exception.Message -match "Missing tool 'node'") 'missing-tool error must name the tool'
  }

  $denied = ConvertTo-CodexLaunchException -Exception ([System.UnauthorizedAccessException]::new('denied')) `
    -FilePath 'C:\tools\denied.exe' -DisplayCommand 'denied-test --version'
  Assert-True ($denied.Message -match 'Permission denied') 'permission-denied error must be explicit'
  Assert-True ($denied.Message -match [regex]::Escape('C:\tools\denied.exe')) 'permission-denied error must name executable'
  Assert-True ($denied.Message -match 'denied-test --version') 'permission-denied error must include command'

  $wrappedDenied = ConvertTo-CodexLaunchException `
    -Exception ([System.Management.Automation.MethodInvocationException]::new('wrapped', [System.UnauthorizedAccessException]::new('denied'))) `
    -FilePath 'C:\tools\wrapped-denied.exe'
  Assert-True ($wrappedDenied.Message -match 'Permission denied') 'wrapped permission-denied errors must be explicit'

  $quoted = ConvertTo-CodexCommandLineArgument 'C:\Program Files\my tool\bin\app.exe'
  Assert-Equal '"C:\Program Files\my tool\bin\app.exe"' $quoted 'path quoting must wrap paths with spaces'

  $quoted = ConvertTo-CodexCommandLineArgument 'C:\path\"with quote".exe'
  Assert-True ($quoted -eq '"C:\path\\\"with quote\".exe"') 'path quoting must escape embedded quotes'

  $fakeTools = @{
    node = [pscustomobject]@{ Path = 'C:\tools\node.exe' }
    npm = [pscustomobject]@{ Path = 'C:\tools\npm.cmd' }
    'git-bash' = [pscustomobject]@{ Path = 'C:\Program Files\Git\bin\bash.exe' }
    quarto = [pscustomobject]@{ Path = 'C:\Program Files\Quarto\bin\quarto.exe' }
    python = [pscustomobject]@{ Path = 'C:\Project\.venv\Scripts\python.exe' }
    Rscript = [pscustomobject]@{ Path = 'C:\Tools\R\bin\Rscript.exe' }
  }
  $quick = Get-CodexInvocationSpec -Command quick -RepoRoot $repoRoot -ToolsByName $fakeTools
  Assert-Equal './scripts/testing/quick.sh' $quick.Arguments[0] 'quick must run the canonical script directly'
  Assert-True ($quick.Arguments -notcontains '-c') 'quick must not call Git Bash with a nested command string'
  Assert-True ($quick.Arguments -notcontains 'bash') 'quick must not invoke nested Bash'

  $comprehensive = Get-CodexInvocationSpec -Command comprehensive -RepoRoot $repoRoot -ToolsByName $fakeTools
  Assert-Equal './scripts/testing/comprehensive.sh' $comprehensive.Arguments[0] 'comprehensive must run the canonical script directly'
  Assert-True ($comprehensive.Arguments -notcontains '-c') 'comprehensive must not call Git Bash with a nested command string'
  Assert-True ($comprehensive.Arguments -notcontains 'bash') 'comprehensive must not invoke nested Bash'

  $preview = Get-CodexInvocationSpec -Command preview -RepoRoot $repoRoot -ToolsByName $fakeTools
  Assert-Equal './scripts/preview-site.sh' $preview.Arguments[0] 'preview must run the canonical preview script'
  Assert-Equal '8765' $preview.Arguments[1] 'preview must default to port 8765'
  $preview = Get-CodexInvocationSpec -Command preview -RepoRoot $repoRoot -ToolsByName $fakeTools -CommandArguments @('9123')
  Assert-Equal '9123' $preview.Arguments[1] 'preview must forward an explicit port'

  $previewSmoke = Get-CodexInvocationSpec -Command preview-smoke -RepoRoot $repoRoot -ToolsByName $fakeTools
  Assert-Equal './scripts/preview-site.sh' $previewSmoke.Arguments[0] 'preview-smoke script path must be canonical'

  $badLauncher = Invoke-Launcher @('nonsense')
  Assert-Equal 2 $badLauncher.ExitCode 'unknown command must return 2'

  if (Get-Command node -CommandType Application -ErrorAction SilentlyContinue) {
    $badLauncher = Invoke-Launcher @('preview-smoke', 'foo')
    Assert-True ($badLauncher.ExitCode -ne 0) 'invalid port value must fail'

    $occupiedPort = 9987
    $occupier = Start-Process -FilePath (Get-Command powershell.exe).Source -ArgumentList @(
      '-NoProfile',
      '-Command',
      "& {`$l = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $occupiedPort); `$l.Start(); Start-Sleep -Seconds 120}"
    ) -PassThru

    Start-Sleep -Milliseconds 500
    $occupiedSmoke = Invoke-Launcher @('preview-smoke', $occupiedPort.ToString())
    Assert-True ($occupiedSmoke.ExitCode -ne 0) 'preview-smoke must fail when port is already in use'
    try {
      $occupierState = Get-Process -Id $occupier.Id -ErrorAction Stop
    } catch {
      $occupierState = $null
    }
    Assert-True ($occupierState -ne $null) 'occupied port process must not be killed by preview-smoke'
    Stop-Process -Id $occupier.Id -Force
    $occupier.WaitForExit()

    $smoke = Invoke-Launcher @('preview-smoke', '8765')
    if ($smoke.ExitCode -eq 0) {
      Write-Host 'preview-smoke execution completed cleanly'
    } else {
      Add-Failure "preview-smoke must complete cleanly (exit $($smoke.ExitCode))"
    }
  } else {
    Add-Skip 'Node is not available in this Spark environment; skipping preview-smoke launcher execution checks.'
  }
} finally {
  Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}

if ($skips.Count -gt 0) { Write-Host ("SKIPPED: {0}" -f ($skips -join '; ')) }
Write-Host 'Codex Windows tool launcher tests passed'
