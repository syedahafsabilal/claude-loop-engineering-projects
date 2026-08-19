# Creates/refreshes the repository-root workflow from the canonical copy in
# project-6 so GitHub actually executes the event-driven PR review.
#
# GitHub only runs workflows from `.github/workflows/` at the repository root,
# so this one-time promotion step is required to activate the loop. Running this
# script does NOT modify any other project folder.

$ErrorActionPreference = 'Stop'

$root = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$src  = Join-Path $PSScriptRoot '..\..' 'project-6' '.github' 'workflows' 'opencode-review.yml'
$src  = Resolve-Path $src
$destDir = Join-Path $root '.github' 'workflows'
$dest = Join-Path $destDir 'opencode-review.yml'

if (-not (Test-Path -LiteralPath $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

Copy-Item -LiteralPath $src -Destination $dest -Force
Write-Host "Installed workflow -> $dest"
