Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-CodexKnownToolPaths {
  param(
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$RepoRoot
  )

  switch ($Name) {
    'python' {
      $paths = @(
        (Join-Path $RepoRoot '.venv\Scripts\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python313\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python312\python.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python311\python.exe'),
        (Join-Path $env:SystemRoot 'py.exe')
      )
    }
    'node' {
      $paths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs\node.exe'),
        (Join-Path $env:ProgramFiles 'nodejs\node.exe'),
        (Join-Path $env:USERPROFILE 'scoop\apps\nodejs\current\node.exe'),
        'C:\ProgramData\chocolatey\bin\node.exe'
      )
    }
    'npm' {
      $paths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\nodejs\npm.cmd'),
        (Join-Path $env:ProgramFiles 'nodejs\npm.cmd'),
        (Join-Path $env:USERPROFILE 'scoop\apps\nodejs\current\npm.cmd'),
        'C:\ProgramData\chocolatey\bin\npm.exe'
      )
    }
    'quarto' {
      $paths = @(
        (Join-Path $env:LOCALAPPDATA 'Programs\Quarto\bin\quarto.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Quarto\bin\quarto.cmd'),
        (Join-Path $env:ProgramFiles 'Quarto\bin\quarto.exe'),
        (Join-Path $env:ProgramFiles 'Quarto\bin\quarto.cmd')
      )
    }
    'Rscript' {
      $paths = @(
        Get-ChildItem (Join-Path $env:ProgramFiles 'R\R-*\bin\Rscript.exe') -File -ErrorAction SilentlyContinue |
          Sort-Object FullName -Descending |
          Select-Object -ExpandProperty FullName
      )
    }
    'git-bash' {
      $paths = @(
        (Join-Path $env:ProgramFiles 'Git\bin\bash.exe'),
        (Join-Path $env:ProgramFiles 'Git\usr\bin\bash.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\bin\bash.exe')
      )
    }
    default { throw "Unknown tool name: $Name" }
  }
  return @($paths | Where-Object { $_ })
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

  # The repository interpreter is deliberately considered before inherited PATH.
  if ($Name -eq 'python') {
    $candidates.Add((Join-Path $RepoRoot '.venv\Scripts\python.exe'))
  }
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
  if ($Value -notmatch '[\s"]') { return $Value }
  return '"' + ($Value -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
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
    if ($cause -is [System.UnauthorizedAccessException] -or
      ($cause -is [System.ComponentModel.Win32Exception] -and $cause.NativeErrorCode -eq 5)) {
      $denied = $true
      break
    }
    $cause = $cause.InnerException
  }
  if ($denied) {
    $shown = if ($DisplayCommand) { $DisplayCommand } else { $FilePath }
    return [System.UnauthorizedAccessException]::new(
      "Permission denied launching '$FilePath' for command '$shown'.", $Exception
    )
  }
  return $Exception
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

  $psi = [System.Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = $FilePath
  $psi.WorkingDirectory = $WorkingDirectory
  $psi.UseShellExecute = $false
  $psi.CreateNoWindow = $false
  $psi.Arguments = (($ArgumentList | ForEach-Object { ConvertTo-CodexCommandLineArgument $_ }) -join ' ')
  if ($CaptureOutput) {
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
  }

  $pathParts = [System.Collections.Generic.List[string]]::new()
  foreach ($path in $PrependPath) {
    if ($path -and -not $pathParts.Contains($path)) { $pathParts.Add($path) }
  }
  $inheritedPath = [Environment]::GetEnvironmentVariable('PATH', 'Process')
  if ($inheritedPath) { $pathParts.Add($inheritedPath) }
  $childPath = $pathParts -join [IO.Path]::PathSeparator
  if (($psi.PSObject.Properties.Name -contains 'Environment') -and $null -ne $psi.Environment) {
    $psi.Environment.Item('PATH') = $childPath
  } else {
    $psi.EnvironmentVariables.Item('PATH') = $childPath
  }

  try {
    $process = [System.Diagnostics.Process]::new()
    $process.StartInfo = $psi
    if (-not $process.Start()) { throw "The process did not start." }
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
    $mapped = ConvertTo-CodexLaunchException -Exception $_.Exception -FilePath $FilePath -DisplayCommand $DisplayCommand
    if ($mapped -ne $_.Exception) { throw $mapped }
    throw
  }
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
  if ([IO.Path]::GetExtension($Tool.Path) -eq '.cmd') {
    $executable = $env:ComSpec
    $arguments = @('/d', '/c', 'call', $Tool.Path) + $arguments
  } elseif ([IO.Path]::GetExtension($Tool.Path) -eq '.ps1') {
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
  $tools = foreach ($name in $Names) { Find-CodexTool -Name $name -RepoRoot $RepoRoot }
  return @($tools)
}

function Get-CodexEnvironmentPath {
  param([Parameter(Mandatory = $true)][object[]]$Tools)
  return @($Tools | ForEach-Object { Split-Path $_.Path -Parent } | Select-Object -Unique)
}

function Get-CodexInvocationSpec {
  param(
    [Parameter(Mandatory = $true)][ValidateSet('verify', 'browser-contract', 'quick', 'comprehensive', 'preview')][string]$Command,
    [Parameter(Mandatory = $true)][string]$RepoRoot,
    [Parameter(Mandatory = $true)][hashtable]$ToolsByName,
    [string[]]$CommandArguments = @()
  )

  switch ($Command) {
    'verify' {
      return [pscustomobject]@{
        FilePath = (Get-Command powershell.exe -CommandType Application -ErrorAction Stop).Source
        Arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
          (Join-Path $RepoRoot 'scripts\setup\windows\verify.ps1'), '-RepoRoot', $RepoRoot)
      }
    }
    'browser-contract' {
      return [pscustomobject]@{ FilePath = $ToolsByName.node.Path; Arguments = @('tests/test_release_ui_browser_check.mjs') }
    }
    'quick' {
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('scripts/testing/quick.sh') }
    }
    'comprehensive' {
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('scripts/testing/comprehensive.sh') + $CommandArguments }
    }
    'preview' {
      if ($CommandArguments.Count -gt 1) { throw 'preview accepts zero or one port.' }
      $port = if ($CommandArguments.Count -eq 1) { $CommandArguments[0] } else { '8765' }
      return [pscustomobject]@{ FilePath = $ToolsByName.'git-bash'.Path; Arguments = @('scripts/preview-site.sh', $port) }
    }
  }
}

Export-ModuleMember -Function Find-CodexTool, ConvertTo-CodexLaunchException, Invoke-CodexChildProcess, Get-CodexToolVersion, `
  Resolve-CodexTools, Get-CodexEnvironmentPath, Get-CodexInvocationSpec
