[CmdletBinding()]
param(
  [Parameter(Position = 0)]
  [string]$Command = 'help',

  [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
  [string[]]$CommandArguments
)

$implementation = Join-Path $PSScriptRoot 'dev/windows/codex-tools.ps1'
& $implementation $Command @CommandArguments
exit $LASTEXITCODE

