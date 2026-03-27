param(
    [string]$OutputDir = "dist",
    [string]$Version
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifestPath = Join-Path $projectRoot "manifest.ini"

if (-not (Test-Path -LiteralPath $manifestPath)) {
    throw "manifest.ini was not found in $projectRoot"
}

function Get-ManifestValue {
    param([string]$Key)

    $pattern = '^\s*' + [regex]::Escape($Key) + '\s*=\s*(.+?)\s*$'
    foreach ($line in Get-Content -LiteralPath $manifestPath) {
        $match = [regex]::Match($line, $pattern)
        if ($match.Success) {
            return $match.Groups[1].Value.Trim().Trim('"')
        }
    }

    throw "Missing '$Key' in manifest.ini"
}

function Get-ArchiveRelativePath {
    param([string]$FullPath)

    $normalizedRoot = $projectRoot.TrimEnd('\', '/')
    $normalizedPath = $FullPath

    if (-not $normalizedPath.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Path '$FullPath' is outside the project root."
    }

    return $normalizedPath.Substring($normalizedRoot.Length).TrimStart('\', '/') -replace '\\', '/'
}

$addonName = Get-ManifestValue -Key "name"
$addonVersion = if ($Version) { $Version } else { Get-ManifestValue -Key "version" }
$outputDirPath = Join-Path $projectRoot $OutputDir
$addonPath = Join-Path $outputDirPath "$addonName-$addonVersion.nvda-addon"

$packageEntries = @("manifest.ini", "globalPlugins", "locale", "doc", "LICENSE")
$requiredEntries = @("manifest.ini", "globalPlugins")
$excludedDirectoryNames = @("__pycache__")
$excludedExtensions = @(".pyc", ".pyo")

foreach ($entry in $requiredEntries) {
    $entryPath = Join-Path $projectRoot $entry
    if (-not (Test-Path -LiteralPath $entryPath)) {
        throw "Required add-on entry '$entry' was not found."
    }
}

$pathsToPackage = foreach ($entry in $packageEntries) {
    $entryPath = Join-Path $projectRoot $entry
    if (Test-Path -LiteralPath $entryPath) {
        $entryPath
    }
}

if (-not (Test-Path -LiteralPath $outputDirPath)) {
    New-Item -ItemType Directory -Path $outputDirPath | Out-Null
}

if (Test-Path -LiteralPath $addonPath) {
    Remove-Item -LiteralPath $addonPath -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open(
    $addonPath,
    [System.IO.Compression.ZipArchiveMode]::Create
)

try {
    foreach ($path in $pathsToPackage) {
        $item = Get-Item -LiteralPath $path
        if ($item.PSIsContainer) {
            foreach ($file in Get-ChildItem -LiteralPath $item.FullName -File -Recurse) {
                if ($excludedExtensions -contains $file.Extension.ToLowerInvariant()) {
                    continue
                }

                $directoryNames = $file.DirectoryName.Split([System.IO.Path]::DirectorySeparatorChar)
                if ($directoryNames | Where-Object { $excludedDirectoryNames -contains $_ }) {
                    continue
                }

                $relativePath = Get-ArchiveRelativePath -FullPath $file.FullName
                [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                    $archive,
                    $file.FullName,
                    $relativePath,
                    [System.IO.Compression.CompressionLevel]::Optimal
                ) | Out-Null
            }
        } else {
            $relativePath = Get-ArchiveRelativePath -FullPath $item.FullName
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $item.FullName,
                $relativePath,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
        }
    }
}
finally {
    $archive.Dispose()
}

$hash = Get-FileHash -LiteralPath $addonPath -Algorithm SHA256

Write-Host "Built add-on package:"
Write-Host "  $addonPath"
Write-Host "SHA256:"
Write-Host "  $($hash.Hash)"
