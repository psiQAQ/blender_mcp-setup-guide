[CmdletBinding()]
param(
    [Parameter()]
    [switch]$Help
)

if ($Help) {
    @"
Usage: build_extension.ps1 [-Help]

Build Blender extension from template root.

Options:
  -Help    Show this help message and exit
"@ | Write-Output
    exit 0
}

$ScriptDir = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
$ExtensionRoot = Split-Path -Path $ScriptDir -Parent

Push-Location -Path $ExtensionRoot
try {
    $pythonRunner = $null

    if (Get-Command python -ErrorAction SilentlyContinue) {
        & python --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $pythonRunner = { param([string[]]$Args) & python @Args }
        }
    }

    if (-not $pythonRunner -and (Get-Command py -ErrorAction SilentlyContinue)) {
        & py -3 --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $pythonRunner = { param([string[]]$Args) & py -3 @Args }
        }
    }

    if (-not $pythonRunner) {
        Write-Error "No usable Python interpreter found. Tried 'python' and 'py -3'. Please install Python 3 and ensure one command is available in PATH."
        exit 1
    }

    & $pythonRunner "$ScriptDir/preflight_extension.py"
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }

    blender --command extension build
}
finally {
    Pop-Location
}
