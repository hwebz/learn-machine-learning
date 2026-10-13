<#
.SYNOPSIS
    Clean up test data from pc_chatbots (database + artifacts).

.DESCRIPTION
    Removes test jobs and artifact folders created by unit tests and smoke tests.
    Keeps real user jobs, browser profiles, and manual debug folders.

    Wraps: scripts/cleanup_test_data.py

.PARAMETER DryRun
    Show what would be removed without actually deleting anything.

.PARAMETER DatabaseOnly
    Only clean the database, skip artifacts.

.PARAMETER ArtifactsOnly
    Only clean artifacts, skip database.

.PARAMETER Yes
    Skip confirmation prompt.

.PARAMETER Help
    Show this help message.

.EXAMPLE
    .\CleanTestData.ps1
    # Interactive cleanup with confirmation

.EXAMPLE
    .\CleanTestData.ps1 -DryRun
    # Preview what would be removed

.EXAMPLE
    .\CleanTestData.ps1 -Yes
    # Non-interactive cleanup (good for automation)

.EXAMPLE
    .\CleanTestData.ps1 -DatabaseOnly -Yes
    # Only clean database, no artifacts
#>

param(
    [switch] $DryRun,
    [switch] $DatabaseOnly,
    [switch] $ArtifactsOnly,
    [switch] $Yes,
    [switch] $Help
)

if ($Help) {
    Get-Help $PSCommandPath -Detailed
    exit 0
}

# Resolve paths relative to this script (scripts/ folder inside the project)
$scriptDir = Split-Path -Parent $PSCommandPath
$projectDir = Split-Path -Parent $scriptDir
$pythonScript = Join-Path $scriptDir "cleanup_test_data.py"
$venvPython = Join-Path $projectDir ".venv\Scripts\python.exe"

# Validate
if (-not (Test-Path $venvPython)) {
    Write-Error "Virtual environment not found at: $venvPython"
    exit 1
}
if (-not (Test-Path $pythonScript)) {
    Write-Error "Cleanup script not found at: $pythonScript"
    exit 1
}

# Build arguments
$args = @()
if ($DryRun)       { $args += "--dry-run" }
if ($DatabaseOnly) { $args += "--db-only" }
if ($ArtifactsOnly) { $args += "--artifacts-only" }
if ($Yes)          { $args += "--yes" }

Write-Host "Running cleanup..." -ForegroundColor Cyan
Write-Host "  Script: $pythonScript" -ForegroundColor Gray
Write-Host "  Python: $venvPython" -ForegroundColor Gray
Write-Host "  Args:   $($args -join ' ')" -ForegroundColor Gray
Write-Host ""

# Execute
& $venvPython $pythonScript @args
$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host "`nDone." -ForegroundColor Green
} else {
    Write-Host "`nFailed with exit code $exitCode" -ForegroundColor Red
}

exit $exitCode