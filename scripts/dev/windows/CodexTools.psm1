Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-CodexKnownToolPaths {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$RepoRoot
  )

  switch ($Name) {
    'python' {
      return @(
        (Join-Path $RepoRoot '.venv\Scripts\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python310\python.exe'),
        (Join-Path $env:SystemRoot 'py.exe')
      )
    }
    'node' {
      return @(
        (Join-Path $RepoRoot '.tools\node\node.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs\node.exe'),
        (Join-Path $env:ProgramFiles 'nodejs\node.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'nodejs\node.exe'),
        (Join-Path $env:USERPROFILE 'scoop\apps\nodejs\current\node.exe'),
        'C:\ProgramData\chocolatey\bin\node.exe'
      )
    }
    'npm' {
      return @(
        (Join-Path $RepoRoot '.tools\node\npm.cmd'),
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs\npm.cmd'),
        (Join-Path $env:ProgramFiles 'nodejs\npm.cmd'),
        (Join-Path ${env:ProgramFiles(x86)} 'nodejs\npm.cmd'),
        (Join-Path $env:USERPROFILE 'scoop\apps\nodejs\current\npm.cmd'),
        'C:\ProgramData\chocolatey\bin\npm.exe'
      )
    }
    'quarto' {
      return @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Quarto\bin\quarto.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Quarto\bin\quarto.cmd'),
        (Join-Path $env:ProgramFiles 'Quarto\bin\quarto.exe'),
        (Join-Path $env:ProgramFiles 'Quarto\bin\quarto.cmd'),
        (Join-Path ${env:ProgramFiles(x86)} 'Quarto\bin\quarto.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Quarto\bin\quarto.cmd')
      )
    }
    'Rscript' {
      $localR = @()
      $localRRoot = Join-Path $env:LOCALAPPDATA 'Programs\R'
      if (Test-Path -LiteralPath $localRRoot -PathType Container) {
        Get-ChildItem -Path $localRRoot -Directory -Filter 'R-*' -ErrorAction SilentlyContinue |
          ForEach-Object {
            if ($_.Name -match '^R-(?<version>\d+(?:\.\d+)*)$' ) {
              try {
                [version]$version = $Matches.version
                [pscustomobject]@{ Path = (Join-Path $_.FullName 'bin\Rscript.exe'); Version = $version }
              } catch {
                $null
              }
            }
          } |
          Sort-Object -Property @{ Expression = { $_.Version }; Descending = $true } |
          ForEach-Object { $_.Path }
      }

      $programFilesR = @()
      if (Test-Path -LiteralPath (Join-Path $env:ProgramFiles 'R') -PathType Container) {
        $programFilesR = Get-ChildItem -Path (Join-Path $env:ProgramFiles 'R') -Directory -Filter 'R-*' -ErrorAction SilentlyContinue |
          ForEach-Object {
            if ($_.Name -match '^R-(?<version>\d+(?:\.\d+)*)$' ) {
              try {
                [version]$version = $Matches.version
                [pscustomobject]@{ Path = (Join-Path $_.FullName 'bin\Rscript.exe'); Version = $version }
              } catch {
                $null
              }
            }
          } |
          Sort-Object -Property @{ Expression = { $_.Version }; Descending = $true } |
          ForEach-Object { $_.Path }
      }

      $programFilesX86R = @()
      if (Test-Path -LiteralPath (Join-Path ${env:ProgramFiles(x86)} 'R') -PathType Container) {
        $programFilesX86R = Get-ChildItem -Path (Join-Path ${env:ProgramFiles(x86)} 'R') -Directory -Filter 'R-*' -ErrorAction SilentlyContinue |
          ForEach-Object {
            if ($_.Name -match '^R-(?<version>\d+(?:\.\d+)*)$' ) {
              try {
                [version]$version = $Matches.version
                [pscustomobject]@{ Path = (Join-Path $_.FullName 'bin\Rscript.exe'); Version = $version }
              } catch {
                $null
              }
            }
          } |
          Sort-Object -Property @{ Expression = { $_.Version }; Descending = $true } |
          ForEach-Object { $_.Path }
      }

      return @(
        $localR,
        $programFilesR,
        $programFilesX86R
      )
    }
    'git-bash' {
      return @(
        (Join-Path $env:ProgramFiles 'Git\bin\bash.exe'),
        (Join-Path $env:ProgramFiles 'Git\usr\bin\bash.exe'),
        (Join-Path $env:ProgramFiles 'Git\git-bash.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Git\bin\bash.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe')
      )
    }
    default {
      throw "Unknown tool name: $Name"
    }
  }
}

function Resolve-CodexNodeBootstrapSource {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [switch]$PreferInstalledOnly
  )

  $candidates = [System.Collections.Generic.List[string]]::new()
  $nodePaths = Get-CodexKnownToolPaths -Name 'node' -RepoRoot $RepoRoot
  $projectLocalNode = Join-Path $RepoRoot '.tools\node\node.exe'
  foreach ($path in $nodePaths) {
    if ($PreferInstalledOnly -and [IO.Path]::GetFullPath($path).Equals([IO.Path]::GetFullPath($projectLocalNode), [System.StringComparison]::OrdinalIgnoreCase)) {
      continue
    }
    if ($path) { $candidates.Add((Split-Path -Path $path -Parent)) }
  }

  $fromCommand = Get-Command node -CommandType Application, ExternalScript -ErrorAction SilentlyContinue |
    Select-Object -First 1 -ExpandProperty Source
  if ($fromCommand) { $candidates.Add((Split-Path -Path $fromCommand -Parent)) }

  $normalized = [System.Collections.Generic.List[string]]::new()
  $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($candidate in $candidates) {
    if ($candidate -and $seen.Add($candidate)) { $normalized.Add($candidate) }
  }

  $requiredFiles = @('node.exe', 'npm.cmd')
  foreach ($candidate in $normalized) {
    $hasRuntime = $true
    foreach ($requiredFile in $requiredFiles) {
      $candidateFile = Join-Path $candidate $requiredFile
      if (-not (Test-Path -LiteralPath $candidateFile -PathType Leaf)) {
        $hasRuntime = $false
        break
      }
    }
    if (-not $hasRuntime) { continue }
    if (-not (Test-Path -LiteralPath (Join-Path $candidate 'node_modules\npm\bin\npm-cli.js') -PathType Leaf)) {
      continue
    }
    return (Resolve-Path -LiteralPath $candidate).Path
  }

  $candidateText = if ($normalized.Count -eq 0) { '(none)' } else { $normalized -join '; ' }
  throw "Unable to locate installed Node runtime with npm support. Searched: $candidateText"
}

function Invoke-CodexNodeBootstrap {
  param([Parameter(Mandatory = $true)][string]$RepoRoot)

  $sourceRoot = Resolve-CodexNodeBootstrapSource -RepoRoot $RepoRoot
  $destinationRoot = Join-Path $RepoRoot '.tools\node'
  $destinationNode = Join-Path $destinationRoot 'node.exe'
  $destinationNpm = Join-Path $destinationRoot 'npm.cmd'

  Write-Host ("Source: {0}" -f $sourceRoot)
  Write-Host ("Destination: {0}" -f $destinationRoot)

  if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Node source path is not a directory: $sourceRoot"
  }

  $destinationRootResolved = Resolve-Path -Path $destinationRoot -ErrorAction SilentlyContinue
  if ($destinationRootResolved) {
    if ((Resolve-Path -LiteralPath $sourceRoot).Path -eq $destinationRootResolved.Path) {
      $alreadyProvisioned = (Test-Path -LiteralPath $destinationNode -PathType Leaf) -and
        (Test-Path -LiteralPath $destinationNpm -PathType Leaf) -and
        (Test-Path -LiteralPath (Join-Path $destinationRoot 'node_modules\npm\bin\npm-cli.js') -PathType Leaf)
      if ($alreadyProvisioned) {
        return [pscustomobject]@{
          Source = $sourceRoot
          Destination = $destinationRoot
        }
      }
      try {
        $sourceRoot = Resolve-CodexNodeBootstrapSource -RepoRoot $RepoRoot -PreferInstalledOnly
        Write-Host ('Source was incomplete; retrying from installed runtime: {0}' -f $sourceRoot)
      } catch {
        throw "Existing project-local Node runtime at '$sourceRoot' is incomplete and no installed fallback was found."
      }
    }
  }

  New-Item -ItemType Directory -Force -Path $destinationRoot | Out-Null
  try {
    Copy-Item -Path (Join-Path $sourceRoot 'node.exe') -Destination $destinationNode -Force
    Copy-Item -Path (Join-Path $sourceRoot 'npm.cmd') -Destination $destinationNpm -Force
    $sourceNpmDirectory = Join-Path $sourceRoot 'node_modules\npm'
    $destinationNpmDirectory = Join-Path $destinationRoot 'node_modules\npm'
    if (Test-Path -LiteralPath $destinationNpmDirectory -PathType Container) {
      Remove-Item -LiteralPath $destinationNpmDirectory -Recurse -Force
    }
    Copy-Item -Path (Join-Path $sourceNpmDirectory 'bin') -Destination (Join-Path $destinationNpmDirectory 'bin') -Recurse -Force
    if (Test-Path -LiteralPath (Join-Path $sourceNpmDirectory 'node_modules') -PathType Container) {
      Copy-Item -Path (Join-Path $sourceNpmDirectory 'node_modules') -Destination (Join-Path $destinationNpmDirectory 'node_modules') -Recurse -Force
    }
    $sourceNpmPackageJson = Join-Path $sourceNpmDirectory 'package.json'
    if (Test-Path -LiteralPath $sourceNpmPackageJson -PathType Leaf) {
      Copy-Item -Path $sourceNpmPackageJson -Destination (Join-Path $destinationNpmDirectory 'package.json') -Force
    }
  } catch {
    throw [System.UnauthorizedAccessException]::new(
      "Permission denied while copying Node runtime from '$sourceRoot' to '$destinationRoot': $($_.Exception.Message)",
      $_.Exception
    )
  }

  $copiedNpmCli = Test-Path -LiteralPath (Join-Path $destinationRoot 'node_modules\npm\bin\npm-cli.js') -PathType Leaf
  if (-not (Test-Path -LiteralPath $destinationNode -PathType Leaf) -or
      -not (Test-Path -LiteralPath $destinationNpm -PathType Leaf) -or
      -not $copiedNpmCli) {
    throw "Bootstrap did not complete because required Node runtime files are missing from $destinationRoot"
  }

  return [pscustomobject]@{
    Source = $sourceRoot
    Destination = $destinationRoot
  }
}

function Find-CodexTool {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('python', 'node', 'npm', 'quarto', 'Rscript', 'git-bash')][string]$Name,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [scriptblock]$CommandLookup,
    [string[]]$KnownPaths
  )

  if (-not $CommandLookup) {
    $CommandLookup = {
      param($commandName)
      Get-Command $commandName -All -CommandType Application, ExternalScript -ErrorAction SilentlyContinue |
        Sort-Object @{ Expression = {
          switch ([IO.Path]::GetExtension($_.Source).ToLowerInvariant()) {
            '.exe' { 0 }
            '.cmd' { 1 }
            '.bat' { 2 }
            '.ps1' { 3 }
            default { 4 }
          }
        } } |
        Select-Object -First 1 -ExpandProperty Source
    }
  }

  $commandName = if ($Name -eq 'git-bash') { 'bash' } else { $Name }
  $candidates = [System.Collections.Generic.List[string]]::new()

  if ($Name -eq 'python') { $candidates.Add((Join-Path $RepoRoot '.venv\Scripts\python.exe')) }

  $fromCommand = & $CommandLookup $commandName
  if ($fromCommand) { $candidates.Add([string]$fromCommand) }

  if ($null -eq $KnownPaths) { $KnownPaths = Get-CodexKnownToolPaths -Name $Name -RepoRoot $RepoRoot }
  foreach ($path in $KnownPaths) { if ($path) { $candidates.Add($path) } }

  $seen = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
  foreach ($candidate in $candidates) {
    $expanded = [Environment]::ExpandEnvironmentVariables($candidate)
    if ($seen.Add($expanded) -and (Test-Path -LiteralPath $expanded -PathType Leaf)) {
      return [pscustomobject]@{ Name = $Name; Path = (Resolve-Path -LiteralPath $expanded).Path }
    }
  }

  throw [System.IO.FileNotFoundException]::new(
    "Missing tool '$Name'. Checked Get-Command and known installed Windows locations."
  )
}

function ConvertTo-CodexCommandLineArgument {
  param([AllowEmptyString()][string]$Value)
  if ($null -eq $Value) { return '' }
  if ($Value -eq '') { return '""' }
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
}

function ConvertTo-CodexCommandLine {
  param([string[]]$ArgumentList)
  return (($ArgumentList | ForEach-Object { ConvertTo-CodexCommandLineArgument $_ }) -join ' ')
}

function ConvertTo-CodexLaunchException {
  param(
    [Parameter(Mandatory = $true)][System.Exception]$Exception,
    [Parameter(Mandatory = $true)][string]$FilePath,
    [string]$DisplayCommand
  )

  $cause = $Exception
  $denied = $false
  while ($cause) {
    if (
      $cause -is [System.UnauthorizedAccessException] -or
      ($cause -is [System.ComponentModel.Win32Exception] -and $cause.NativeErrorCode -eq 5)
    ) {
      $denied = $true
      break
    }
    $cause = $cause.InnerException
  }

  if ($denied) {
    $shown = if ($DisplayCommand) { $DisplayCommand } else { $FilePath }
    return [System.UnauthorizedAccessException]::new(
      "Permission denied launching '$FilePath' for command '$shown'.",
      $Exception
    )
  }

  return $Exception
}

function New-CodexStartInfo {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string]$Arguments,
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [string[]]$PrependPath = @()
  )

  $pathParts = [System.Collections.Generic.List[string]]::new()
  foreach ($path in $PrependPath) {
    if ($path -and -not $pathParts.Contains($path)) { $pathParts.Add($path) }
  }
  $systemPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
  if ($systemPath) { $pathParts.Add($systemPath) }
  $childPath = $pathParts -join [IO.Path]::PathSeparator

  $psi = [System.Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = $FilePath
  $psi.WorkingDirectory = $WorkingDirectory
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $true
  $psi.Arguments = $Arguments
  if ($null -ne $psi.Environment) {
    $psi.Environment['PATH'] = $childPath
  } else {
    $psi.EnvironmentVariables['PATH'] = $childPath
  }
  return $psi
}

function Invoke-CodexChildProcess {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [string[]]$ArgumentList = @(),
    [Parameter(Mandatory = $true)][string]$WorkingDirectory,
    [string[]]$PrependPath = @(),
    [switch]$CaptureOutput,
    [string]$DisplayCommand
  )

  $argumentText = ConvertTo-CodexCommandLine -ArgumentList $ArgumentList
  if (-not $DisplayCommand) { $DisplayCommand = "$FilePath $argumentText" }

  $attempts = @(
    @{
      Label = 'ProcessStartInfo'
      File = $FilePath
      Args = $ArgumentList
      Fallback = $false
    },
    @{
      Label = 'cmd /c'
      File = $env:ComSpec
      Args = @('/d', '/c', ('{0} {1}' -f (ConvertTo-CodexCommandLineArgument $FilePath), $argumentText))
      Fallback = $true
    }
  )

  $attemptErrors = [System.Collections.Generic.List[string]]::new()
  foreach ($attempt in $attempts) {
    $commandForDisplay = if ($attempt.Fallback) {
      ('{0} {1}' -f $attempt.File, (ConvertTo-CodexCommandLine -ArgumentList $attempt.Args))
    } else {
      $DisplayCommand
    }
    try {
      $psi = New-CodexStartInfo -FilePath $attempt.File -Arguments (ConvertTo-CodexCommandLine -ArgumentList $attempt.Args) `
        -WorkingDirectory $WorkingDirectory -PrependPath $PrependPath
      if ($CaptureOutput) {
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true
      }

      $process = [System.Diagnostics.Process]::new()
      $process.StartInfo = $psi
      if (-not $process.Start()) { throw [System.InvalidOperationException]::new('The process did not start.') }

      if ($CaptureOutput) {
        $stdout = $process.StandardOutput.ReadToEnd()
        $stderr = $process.StandardError.ReadToEnd()
      }
      $process.WaitForExit()
      return [pscustomobject]@{
        ExitCode = $process.ExitCode
        StdOut = if ($CaptureOutput) { $stdout } else { '' }
        StdErr = if ($CaptureOutput) { $stderr } else { '' }
      }
    } catch {
      $mapped = ConvertTo-CodexLaunchException -Exception $_.Exception -FilePath $attempt.File -DisplayCommand $commandForDisplay
      if ($attempt.Fallback) {
        $attemptErrors.Add($mapped.Message)
        throw [System.UnauthorizedAccessException]::new(
          "Permission denied invoking '$FilePath' after trying multiple launch methods: $($attemptErrors -join '; ')",
          $_.Exception
        )
      }

      if ($mapped -is [System.UnauthorizedAccessException]) {
        $attemptErrors.Add($mapped.Message)
        continue
      }

      throw $mapped
    }
  }

  throw [System.UnauthorizedAccessException]::new(
    "Permission denied invoking '$FilePath' after trying multiple launch methods: $($attemptErrors -join '; ')"
  )
}

function Get-CodexToolVersion {
  param(
    [Parameter(Mandatory = $true)]$Tool,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][string[]]$EnvironmentPath
  )

  $executable = $Tool.Path
  $arguments = switch ($Tool.Name) {
    'Rscript' { @('--version') }
    default { @('--version') }
  }

  if ([IO.Path]::GetExtension($Tool.Path).ToLowerInvariant() -eq '.cmd') {
    $executable = $env:ComSpec
    $arguments = @('/d', '/c', 'call', $Tool.Path) + $arguments
  } elseif ([IO.Path]::GetExtension($Tool.Path).ToLowerInvariant() -eq '.ps1') {
    $executable = (Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $Tool.Path) + $arguments
  }

  $result = Invoke-CodexChildProcess -FilePath $executable -ArgumentList $arguments `
    -WorkingDirectory $RepoRoot -PrependPath $EnvironmentPath -CaptureOutput `
    -DisplayCommand "$($Tool.Name) --version"

  if ($result.ExitCode -ne 0) {
    throw "Unable to read $($Tool.Name) version (exit $($result.ExitCode)): $($result.StdErr.Trim())"
  }

  return (($result.StdOut + "`n" + $result.StdErr).Trim() -split "`r?`n" | Select-Object -First 1)
}

function Resolve-CodexTools {
  param(
    [Parameter(Mandatory = $true)][string[]]$Names,
    [Parameter(Mandatory = $true)][string]$RepoRoot
  )
  return @($Names | ForEach-Object { Find-CodexTool -Name $_ -RepoRoot $RepoRoot })
}

function Get-CodexEnvironmentPath {
  param([Parameter(Mandatory = $true)][object[]]$Tools)
  $paths = [System.Collections.Generic.List[string]]::new()
  foreach ($tool in $Tools) {
    $toolDir = Split-Path $tool.Path -Parent
    if ($toolDir -and -not $paths.Contains($toolDir)) {
      $paths.Add($toolDir)
    }
  }
  return @($paths)
}

function Get-CodexListeningProcesses {
  param([Parameter(Mandatory = $true)][int]$Port, [string]$Address = '127.0.0.1')
  try {
    return Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop |
      Where-Object {
        $_.LocalAddress -eq $Address -or $_.LocalAddress -eq '0.0.0.0' -or $_.LocalAddress -eq '::' -or $_.LocalAddress -eq '::1'
      }
  } catch {
    $pattern = ".*$([regex]::Escape("${Address}:$Port"))"
    $listeners = netstat -ano -p tcp 2>$null | Select-String $pattern
    if (-not $listeners) { return @() }
    return @(
      $listeners | ForEach-Object {
        $parts = ($_ -replace '^\s+', '').Split(' ', [StringSplitOptions]::RemoveEmptyEntries)
        if ($parts.Count -ge 5 -and $parts[3] -eq 'LISTENING') {
          [pscustomobject]@{
            ProcessId = [int]$parts[4]
            LocalAddress = $parts[1]
            State = $parts[3]
          }
        }
      }
    )
  }
}

function Get-CodexProcessTree {
  param([Parameter(Mandatory = $true)][int]$ParentProcessId)
  $queue = [System.Collections.Generic.Queue[object]]::new()
  $queue.Enqueue([int]$ParentProcessId)
  $output = [System.Collections.Generic.List[object]]::new()
  while ($queue.Count -gt 0) {
    $parent = [int]$queue.Dequeue()
    $children = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { [int]$_.ParentProcessId -eq $parent }
    foreach ($child in $children) {
      $output.Add($child)
      $queue.Enqueue([int]$child.ProcessId)
    }
  }
  return @($output)
}

function Stop-CodexProcessTree {
  param([Parameter(Mandatory = $true)][int]$RootProcessId)
  $children = Get-CodexProcessTree -ParentProcessId $RootProcessId
  foreach ($child in ($children | Sort-Object { $_.ProcessId } -Descending)) {
    try { Stop-Process -Id [int]$child.ProcessId -Force -ErrorAction Stop } catch { }
  }
  try { Stop-Process -Id $RootProcessId -Force -ErrorAction Stop } catch { }

  1..20 | ForEach-Object {
    if (-not (Get-Process -Id $RootProcessId -ErrorAction SilentlyContinue)) { return }
    Start-Sleep -Milliseconds 250
  }
}

function Wait-CodexHttpReady {
  param(
    [Parameter(Mandatory = $true)][string]$Uri,
    [int]$TimeoutSeconds = 20
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    try {
      $response = Invoke-WebRequest -UseBasicParsing -Uri $Uri -TimeoutSec 1
      if ($response.StatusCode -eq 200) { return $true }
    } catch {
      # keep waiting
    }
    Start-Sleep -Milliseconds 250
  }
  return $false
}

function Invoke-CodexPreviewSmoke {
  param(
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][hashtable]$ToolsByName,
    [string[]]$CommandArguments = @()
  )

  if ($CommandArguments.Count -gt 1) { throw 'preview-smoke accepts zero or one port.' }
  $port = if ($CommandArguments.Count -eq 1) { $CommandArguments[0] } else { '8765' }
  if ($port -notmatch '^[0-9]+$' -or [int]$port -lt 1 -or [int]$port -gt 65535) {
    throw "Invalid preview-smoke port: $port"
  }

  $hostAddress = '127.0.0.1'
  $uri = "http://$($hostAddress):$port/"
  $existing = Get-CodexListeningProcesses -Port [int]$port -Address $hostAddress
  if ($existing) {
    throw "Port $port is already in use; refusing to start preview-smoke."
  }

  $environmentPath = Get-CodexEnvironmentPath -Tools @($ToolsByName.Values)
  $bashPath = $ToolsByName.'git-bash'.Path
  if (-not $bashPath) { throw 'Missing tool git-bash.' }

  $psi = New-CodexStartInfo -FilePath $bashPath -Arguments (ConvertTo-CodexCommandLine -ArgumentList @('./scripts/preview-site.sh', $port)) `
    -WorkingDirectory $RepoRoot -PrependPath $environmentPath

  $process = [System.Diagnostics.Process]::new()
  $process.StartInfo = $psi
  if (-not $process.Start()) { throw 'Unable to start preview process.' }

  try {
    if (-not (Wait-CodexHttpReady -Uri $uri -TimeoutSeconds 20)) {
      $startCode = if ($process.HasExited) { $process.ExitCode } else { 1 }
      throw "preview-smoke failed to observe HTTP 200 on $uri (code $startCode)."
    }

    Stop-CodexProcessTree -RootProcessId $process.Id
    $process.WaitForExit(3000) | Out-Null

    $remaining = Get-CodexProcessTree -ParentProcessId $process.Id | ForEach-Object {
      [pscustomobject]@{
        ProcessId = [int]$_.ProcessId
        Executable = $_.Name
        CommandLine = $_.CommandLine
        ParentProcessId = [int]$_.ParentProcessId
      }
    } | Where-Object { Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue }

    if ($remaining) {
      Write-Host 'Remaining launcher-created processes:'
      $remaining | ForEach-Object {
        Write-Host ("PID $($_.ProcessId): $($_.Executable) (PPID $($_.ParentProcessId))")
        Write-Host ("  $_")
      }
      return 1
    }

    $listeners = Get-CodexListeningProcesses -Port [int]$port -Address $hostAddress
    if ($listeners) {
      Write-Host "Port $port is still bound after shutdown."
      return 1
    }

    return 0
  } finally {
    Stop-CodexProcessTree -RootProcessId $process.Id
  }
}

function Get-CodexInvocationSpec {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('verify', 'browser-contract', 'quick', 'comprehensive', 'preview', 'preview-smoke')][string]$Command,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][hashtable]$ToolsByName,
    [string[]]$CommandArguments = @()
  )

  switch ($Command) {
    'verify' {
      return [pscustomobject]@{
        FilePath = (Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
        Arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $RepoRoot 'scripts\\setup\\windows\\verify.ps1'), '-RepoRoot', $RepoRoot)
      }
    }
    'browser-contract' {
      return [pscustomobject]@{
        FilePath = $ToolsByName.node.Path
        Arguments = @('tests/test_release_ui_browser_check.mjs')
      }
    }
    'quick' {
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('./scripts/testing/quick.sh') }
    }
    'comprehensive' {
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('./scripts/testing/comprehensive.sh') + $CommandArguments }
    }
    'preview' {
      if ($CommandArguments.Count -gt 1) { throw 'preview accepts zero or one port.' }
      $port = if ($CommandArguments.Count -eq 1) { $CommandArguments[0] } else { '8765' }
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('./scripts/preview-site.sh', $port) }
    }
    'preview-smoke' {
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('./scripts/preview-site.sh') + $CommandArguments }
    }
  }
}

Export-ModuleMember -Function Find-CodexTool, Get-CodexKnownToolPaths, ConvertTo-CodexLaunchException, Invoke-CodexChildProcess, Get-CodexToolVersion, `
  Resolve-CodexTools, Get-CodexEnvironmentPath, Get-CodexInvocationSpec, Invoke-CodexPreviewSmoke, `
  Resolve-CodexNodeBootstrapSource, Invoke-CodexNodeBootstrap, `
  ConvertTo-CodexCommandLineArgument, ConvertTo-CodexCommandLine
