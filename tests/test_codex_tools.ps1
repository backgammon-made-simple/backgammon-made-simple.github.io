$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Import-Module (Join-Path $repoRoot 'scripts\dev\windows\CodexTools.psm1') -Force
$failures = [System.Collections.Generic.List[string]]::new()
$skips = [System.Collections.Generic.List[string]]::new()
$originalEnv = @{
  LOCALAPPDATA = $env:LOCALAPPDATA
  PROGRAMFILES = $env:ProgramFiles
  PROGRAMFILES_X86 = ${env:ProgramFiles(x86)}
  USERPROFILE = $env:USERPROFILE
  PATH = $env:PATH
}

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

  $projectNode = Join-Path $fixture '.tools\node\node.exe'
  $projectNpm = Join-Path $fixture '.tools\node\npm.cmd'
  New-Item -ItemType Directory -Path (Split-Path $projectNode -Parent) | Out-Null
  New-Item -ItemType File -Path $projectNode | Out-Null
  New-Item -ItemType File -Path $projectNpm | Out-Null
  $legacyNode = Join-Path $fixture 'legacy\node.exe'
  New-Item -ItemType Directory -Path (Split-Path $legacyNode -Parent) | Out-Null
  New-Item -ItemType File -Path $legacyNode | Out-Null
  $tool = Find-CodexTool -Name node -RepoRoot $fixture -CommandLookup { param($name) $null } -KnownPaths @($projectNode, $legacyNode)
  Assert-Equal (Resolve-Path $projectNode).Path $tool.Path 'project-local Node should be preferred over other known locations'

  $env:LOCALAPPDATA = Join-Path $fixture 'bootstrap\appdata'
  $env:ProgramFiles = Join-Path $fixture 'bootstrap\programfiles'
  ${env:ProgramFiles(x86)} = Join-Path $fixture 'bootstrap\programfilesx86'
  $env:USERPROFILE = Join-Path $fixture 'bootstrap\user'
  $env:PATH = 'C:\Windows\System32'
  $bootstrapWorkspace = Join-Path $fixture 'bootstrap'
  $sourceRoot = Join-Path $env:LOCALAPPDATA 'Programs\nodejs'
  New-Item -ItemType Directory -Path (Split-Path $sourceRoot -Parent) -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $sourceRoot 'node_modules\npm\bin') -Force | Out-Null
  Set-Content -Path (Join-Path $sourceRoot 'node.exe') -Value 'bootstrap source node placeholder'
  Set-Content -Path (Join-Path $sourceRoot 'npm.cmd') -Value '@echo off'
  Set-Content -Path (Join-Path $sourceRoot 'node_modules\npm\bin\npm-cli.js') -Value 'console.log(''npm-cli placeholder'')'
  Set-Content -Path (Join-Path $sourceRoot 'node_modules\npm\package.json') -Value '{ }'
  $bootstrapResult = Invoke-CodexNodeBootstrap -RepoRoot $bootstrapWorkspace
  Assert-Equal (Resolve-Path $sourceRoot).Path $bootstrapResult.Source 'bootstrap should discover node source from installed path'
  Assert-True (Test-Path -LiteralPath (Join-Path $bootstrapWorkspace '.tools\node\node.exe') -PathType Leaf) 'bootstrap should copy node.exe to .tools\\node'
  Assert-True (Test-Path -LiteralPath (Join-Path $bootstrapWorkspace '.tools\node\npm.cmd') -PathType Leaf) 'bootstrap should copy npm.cmd to .tools\\node'
  Assert-True (Test-Path -LiteralPath (Join-Path $bootstrapWorkspace '.tools\node\node_modules\npm\bin\npm-cli.js') -PathType Leaf) 'bootstrap should copy npm runtime support files'
  Assert-Equal 'bootstrap source node placeholder' ((Get-Content -Path (Join-Path $bootstrapWorkspace '.tools\node\node.exe') -Raw).Trim()) 'copying node must copy content only, not execute node.exe'

  $firstNodeHash = (Get-FileHash -Path (Join-Path $bootstrapWorkspace '.tools\node\node.exe')).Hash
  Invoke-CodexNodeBootstrap -RepoRoot $bootstrapWorkspace
  $secondNodeHash = (Get-FileHash -Path (Join-Path $bootstrapWorkspace '.tools\node\node.exe')).Hash
  Assert-Equal $firstNodeHash $secondNodeHash 'repeated bootstrap should be idempotent'

  Remove-Item -LiteralPath (Join-Path $bootstrapWorkspace '.tools\node\npm.cmd') -Force
  Invoke-CodexNodeBootstrap -RepoRoot $bootstrapWorkspace
  Assert-True (Test-Path -LiteralPath (Join-Path $bootstrapWorkspace '.tools\node\npm.cmd') -PathType Leaf) 'incomplete bootstrap should be repaired'

  $missingWorkspace = Join-Path $fixture 'missing-source'
  $env:LOCALAPPDATA = Join-Path $missingWorkspace 'appdata'
  $env:ProgramFiles = Join-Path $missingWorkspace 'programfiles'
  ${env:ProgramFiles(x86)} = Join-Path $missingWorkspace 'programfilesx86'
  $env:USERPROFILE = Join-Path $missingWorkspace 'user'
  try {
    Invoke-CodexNodeBootstrap -RepoRoot $missingWorkspace | Out-Null
    Add-Failure 'bootstrap must fail when no source runtime exists'
  } catch {
    Assert-True ($_.Exception.Message -match 'Unable to locate installed Node runtime') 'missing source should produce a clear error'
  }
  $env:LOCALAPPDATA = $originalEnv.LOCALAPPDATA
  $env:ProgramFiles = $originalEnv.PROGRAMFILES
  ${env:ProgramFiles(x86)} = $originalEnv.PROGRAMFILES_X86
  $env:USERPROFILE = $originalEnv.USERPROFILE
  $env:PATH = $originalEnv.PATH

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

  $gitignore = Get-Content -Path (Join-Path $repoRoot '.gitignore')
  Assert-True ($gitignore -contains '.tools/') '.tools/ must be gitignored for project runtime'
  $resolvedTools = Resolve-CodexTools -Names @('node', 'npm') -RepoRoot $repoRoot
  $resolvedNode = $resolvedTools | Where-Object Name -eq node
  $resolvedNpm = $resolvedTools | Where-Object Name -eq npm
  Assert-True ($resolvedNode.Path.EndsWith('.tools\node\node.exe')) 'project-local node should be preferred in known paths'
  Assert-True ($resolvedNpm.Path.EndsWith('.tools\node\npm.cmd')) 'project-local npm should be preferred in known paths'

  $env:LOCALAPPDATA = Join-Path $fixture 'R\Local'
  $env:ProgramFiles = Join-Path $fixture 'R\ProgramFiles'
  ${env:ProgramFiles(x86)} = Join-Path $fixture 'R\ProgramFilesX86'
  New-Item -ItemType Directory -Path (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.2.1\bin') -Force | Out-Null
  New-Item -ItemType Directory -Path (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.4.3\bin') -Force | Out-Null
  New-Item -ItemType File -Path (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.2.1\bin\Rscript.exe') | Out-Null
  New-Item -ItemType File -Path (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.4.3\bin\Rscript.exe') | Out-Null
  $rPaths = Get-CodexKnownToolPaths -Name Rscript -RepoRoot $repoRoot
  Assert-Equal (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.4.3\bin\Rscript.exe') $rPaths[0] 'user-local R discovery should include highest-local version first'

  New-Item -ItemType Directory -Path (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.3.5\bin') -Force | Out-Null
  New-Item -ItemType File -Path (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.3.5\bin\Rscript.exe') | Out-Null
  $rPaths = Get-CodexKnownToolPaths -Name Rscript -RepoRoot $repoRoot
  Assert-Equal (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.4.3\bin\Rscript.exe') $rPaths[0] 'multiple local R versions should choose highest'
  Assert-Equal (Join-Path $env:LOCALAPPDATA 'Programs\R\R-4.3.5\bin\Rscript.exe') $rPaths[1] 'remaining local R versions should be deterministic'
  $rPathsRepeated = Get-CodexKnownToolPaths -Name Rscript -RepoRoot $repoRoot
  Assert-Equal $rPaths[0] $rPathsRepeated[0] 'local R ordering should be deterministic'
  Assert-Equal $rPaths[1] $rPathsRepeated[1] 'local R tie ordering should be deterministic'

  $missingRWorkspace = Join-Path $fixture 'missing-r'
  $env:LOCALAPPDATA = Join-Path $missingRWorkspace 'LocalAppData'
  $env:ProgramFiles = Join-Path $missingRWorkspace 'ProgramFiles'
  ${env:ProgramFiles(x86)} = Join-Path $missingRWorkspace 'ProgramFilesX86'
  try {
    Find-CodexTool -Name Rscript -RepoRoot $missingRWorkspace -CommandLookup { param($name) $null } -KnownPaths @() | Out-Null
    Add-Failure 'missing R reporting must fail when no Rscript is discoverable'
  } catch {
    Assert-True ($_.Exception.Message -match "Missing tool 'Rscript'") 'missing R reporting should mention missing Rscript'
  } finally {
    $env:LOCALAPPDATA = $originalEnv.LOCALAPPDATA
    $env:ProgramFiles = $originalEnv.PROGRAMFILES
    ${env:ProgramFiles(x86)} = $originalEnv.PROGRAMFILES_X86
  }

  $projectNodeForExecution = Join-Path $repoRoot '.tools\node\node.exe'
  $projectNodeRun = Invoke-CodexChildProcess -FilePath $projectNodeForExecution -ArgumentList @('--version') -WorkingDirectory $repoRoot -PrependPath @((Split-Path $projectNodeForExecution -Parent)) -CaptureOutput
  Assert-True ($projectNodeRun.ExitCode -eq 0) 'project-local Node execution should complete with --version'
  Assert-True ($projectNodeRun.StdOut.Trim().StartsWith('v22.14.0') -or $projectNodeRun.StdOut.Trim().StartsWith('v')) 'project-local Node execution output should resemble a version'

  $browserContract = Invoke-Launcher @('browser-contract')
  Assert-Equal 0 $browserContract.ExitCode 'browser-contract should run in the project-local Node flow'

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
  if ($badLauncher.ExitCode -eq 0) { Add-Failure 'invalid preview-smoke call unexpectedly passed' }
} finally {
  Remove-Item -LiteralPath $fixture -Recurse -Force -ErrorAction SilentlyContinue
  if ($originalEnv) {
    $env:LOCALAPPDATA = $originalEnv.LOCALAPPDATA
    $env:ProgramFiles = $originalEnv.PROGRAMFILES
    ${env:ProgramFiles(x86)} = $originalEnv.PROGRAMFILES_X86
    $env:USERPROFILE = $originalEnv.USERPROFILE
    $env:PATH = $originalEnv.PATH
  }
}

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}

if ($skips.Count -gt 0) { Write-Host ("SKIPPED: {0}" -f ($skips -join '; ')) }
Write-Host 'Codex Windows tool launcher tests passed'
