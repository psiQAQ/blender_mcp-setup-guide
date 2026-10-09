param(
    [ValidateSet('5.1', '5.2')][string]$BlenderVersion = '5.2',
    [Parameter(Mandatory = $true)][string]$Package,
    [int]$Runs = 5,
    [switch]$ExternalWorker,
    [switch]$Focused
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$packagePath = (Resolve-Path -LiteralPath $Package).Path
if (-not $packagePath.StartsWith($repositoryRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw 'The diagnostic package must be inside this repository.'
}
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw 'FileIO/Minifilter recording requires an administrator PowerShell session.'
}
$recorderState = (& wpr -status | Out-String)
if ($LASTEXITCODE -ne 0 -or $recorderState -notmatch 'WPR is not recording') {
    throw 'WPR already has a recording or its status is unavailable; leave that recording intact.'
}
$traceLabel = if ($ExternalWorker) { "$BlenderVersion-external" } else { $BlenderVersion }
if ($Focused) { $traceLabel = "$traceLabel-focused" }
$outputDirectory = Join-Path $repositoryRoot "build\latest\evidence\native-trace-$traceLabel"
[System.IO.Directory]::CreateDirectory($outputDirectory) | Out-Null
$traceFile = Join-Path $outputDirectory 'native-install.etl'
if ((Test-Path -LiteralPath $traceFile) -or (Test-Path -LiteralPath ($traceFile + '.gz'))) {
    throw 'The existing trace must be reviewed and explicitly retired before a new recording.'
}
$blenderRoot = "C:\Program Files\Blender Foundation\Blender $BlenderVersion\$BlenderVersion"
$pythonPath = Join-Path $blenderRoot 'python\bin\python.exe'
$installerPath = Join-Path $blenderRoot 'scripts\addons_core\bl_pkg\cli\blender_ext.py'
$driverPath = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'miniforge3\python.exe'
$exactVersion = if ($BlenderVersion -eq '5.1') { '5.1.1' } else { '5.2.2' }
$started = $false
$checkExit = 1
$controlFile = Join-Path $outputDirectory 'trace-control.json'
$stopRequest = Join-Path $outputDirectory 'stop-request.json'
if ($ExternalWorker -and (Test-Path -LiteralPath $stopRequest)) {
    throw 'Review and retire the previous stop request before a new recording.'
}
$traceControl = @{ status = 'Not Run'; administrator = $true; pid = $PID; package = $packagePath; trace = $traceFile; started_at = (Get-Date).ToUniversalTime().ToString('o') }
$traceControl.worker_elevated = -not $ExternalWorker
try {
    $profileName = if ($Focused) { 'native_install_focused.wprp' } else { 'native_install.wprp' }
    $recordingProfile = Join-Path $PSScriptRoot $profileName
    $traceControl.recording_profile = $recordingProfile
    $traceControl.recording_profile_sha256 = (Get-FileHash -LiteralPath $recordingProfile -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $recordingProfile -Destination (Join-Path $outputDirectory 'recording-profile.wprp') -Force
    $startOutput = (& wpr -start "$recordingProfile!NativeInstall" -filemode | Out-String)
    $traceControl.start_output = $startOutput
    if ($LASTEXITCODE -ne 0) { throw "WPR start failed: $LASTEXITCODE" }
    $started = $true
    $traceControl.status = 'Recording'
    [IO.File]::WriteAllText($controlFile, ($traceControl | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
    if ($ExternalWorker) {
        $deadline = (Get-Date).AddMinutes(3)
        while (-not (Test-Path -LiteralPath $stopRequest) -and (Get-Date) -lt $deadline) {
            Start-Sleep -Milliseconds 250
        }
        if (-not (Test-Path -LiteralPath $stopRequest)) { throw 'The ordinary-token worker did not finish within three minutes.' }
        $checkExit = (Get-Content -LiteralPath $stopRequest -Raw | ConvertFrom-Json).exit_code
    }
    else {
        Push-Location -LiteralPath $repositoryRoot
        try {
            & $driverPath -B scripts/diagnose_native_install.py --python $pythonPath --installer $installerPath --package $packagePath --version $exactVersion --runs $Runs --label "trace-$BlenderVersion"
            $checkExit = $LASTEXITCODE
        }
        finally { Pop-Location }
    }
}
finally {
    if ($started) {
        $stopOutput = (& wpr -stop $traceFile -compress -skipPdbGen | Out-String)
        $traceControl.stop_output = $stopOutput
        if ($LASTEXITCODE -ne 0) { throw "WPR stop failed: $LASTEXITCODE" }
        $traceControl.status = 'Captured'
    }
    else { $traceControl.status = 'Failed' }
    $traceControl.native_check_exit_code = $checkExit
    $traceControl.finished_at = (Get-Date).ToUniversalTime().ToString('o')
    [IO.File]::WriteAllText($controlFile, ($traceControl | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
}
Write-Output "Trace saved: $traceFile"
exit $checkExit
