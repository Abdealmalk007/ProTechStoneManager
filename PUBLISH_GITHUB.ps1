#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Repository = 'Abdealmalk007/ProTechStoneManager',
    [string]$Tag = 'v2.0.0'
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$installer = Join-Path $root 'Release\Setup.exe'
$notes = Join-Path $root 'RELEASE_NOTES_AR.md'
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) { throw 'Setup.exe missing.' }
if (-not (Test-Path -LiteralPath $notes -PathType Leaf)) { throw 'Release notes missing.' }
$publisher = Join-Path $root 'tools\Publish-SignedWindowsRelease.ps1'
if (-not (Test-Path -LiteralPath $publisher)) { throw 'Mandatory signature gate missing.' }
& $publisher -Repository $Repository -Tag $Tag -Assets @($installer) -NotesFile $notes
if ($LASTEXITCODE -ne 0) { throw 'Unsigned or untrusted release was blocked.' }
