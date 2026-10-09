param([string]$Manifest = 'build/latest/maintenance/preservation.json')
$ErrorActionPreference = 'Stop'
$taskRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$taskBuild = [IO.Path]::GetFullPath((Join-Path $taskRoot 'build'))
$taskManifest = [IO.Path]::GetFullPath((Join-Path $taskRoot $Manifest))
if (-not $taskManifest.StartsWith($taskBuild + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Preservation manifest must be inside the project build directory'
}
$taskRecord = Get-Content -LiteralPath $taskManifest -Raw | ConvertFrom-Json
foreach ($item in $taskRecord.sources) {
    $destination = [IO.Path]::GetFullPath((Join-Path $taskRoot $item.destination))
    if (-not $destination.StartsWith($taskRoot + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Preserved destination is outside the workspace: $destination"
    }
    if ((Get-FileHash -LiteralPath $destination -Algorithm SHA256).Hash.ToLowerInvariant() -ne $item.sha256) {
        throw "Preserved hash mismatch: $destination"
    }
}
$remaining = @()
foreach ($target in $taskRecord.cleanup_targets) {
    $absolute = [IO.Path]::GetFullPath($target)
    # Only verified immediate children of this checkout's build directory.
    if ([IO.Path]::GetDirectoryName($absolute) -ne $taskBuild -or [IO.Path]::GetFileName($absolute) -in @('latest', '.working')) {
        throw "Invalid cleanup target: $absolute"
    }
    if (-not (Test-Path -LiteralPath $absolute)) { continue }
    try {
        $item = Get-Item -LiteralPath $absolute -Force
        if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'Cleanup target is a link' }
        if ($item.PSIsContainer) {
            $links = @(Get-ChildItem -LiteralPath $absolute -Recurse -Force -Attributes ReparsePoint)
            if ($links.Count -gt 0) { throw 'Cleanup target contains a link' }
            Remove-Item -LiteralPath $absolute -Recurse -Force
        } else { Remove-Item -LiteralPath $absolute -Force }
    } catch {
        $remaining += [PSCustomObject]@{path=$absolute; error=$_.Exception.Message}
    }
}
$bytes = (Get-ChildItem -LiteralPath $taskBuild -Recurse -Force -File | Measure-Object Length -Sum).Sum
$result = [ordered]@{status=$(if ($remaining.Count -eq 0) {'Passed'} else {'Failed'}); build_bytes=$bytes; remaining=$remaining}
$destination = Join-Path $taskBuild 'latest/maintenance/cleanup.json'
[IO.File]::WriteAllText($destination, ($result | ConvertTo-Json -Depth 8) + "`n", [Text.UTF8Encoding]::new($false))
$result | ConvertTo-Json -Depth 8
