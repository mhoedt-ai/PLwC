[CmdletBinding()]
param(
    [string] $OutputDirectory
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$extensionRoot = Split-Path -Parent $scriptRoot
$distRoot = Join-Path $extensionRoot "dist"
$manifestPath = Join-Path $extensionRoot "src\manifest.json"

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $extensionRoot "store\out"
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)

$sourceManifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string] $sourceManifest.key)) {
    throw "The source manifest must retain its documented development identity key."
}

$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -eq $npm) {
    $npm = Get-Command npm -ErrorAction SilentlyContinue
}
if ($null -eq $npm) {
    throw "npm is required to build the draft identity seed."
}

& $npm.Source run build
if ($LASTEXITCODE -ne 0) {
    throw "The extension build failed with exit code $LASTEXITCODE."
}

$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("plwc-store-draft-seed-" + [Guid]::NewGuid().ToString("N"))
$packageRoot = Join-Path $temporaryRoot "package"

try {
    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
    New-Item -ItemType Directory -Path (Join-Path $packageRoot "icons") -Force | Out-Null

    foreach ($fileName in @("background.js", "content.js")) {
        Copy-Item -LiteralPath (Join-Path $distRoot $fileName) -Destination (Join-Path $packageRoot $fileName)
    }
    Copy-Item -LiteralPath (Join-Path $distRoot "icons\plwc-icon-512.png") -Destination (Join-Path $packageRoot "icons\plwc-icon-512.png")

    $seedManifest = Get-Content -LiteralPath (Join-Path $distRoot "manifest.json") -Raw | ConvertFrom-Json
    if ($null -eq $seedManifest.PSObject.Properties["key"]) {
        throw "The built manifest did not contain the development key that must be removed."
    }
    $seedManifest.PSObject.Properties.Remove("key")
    $seedManifestJson = $seedManifest | ConvertTo-Json -Depth 100
    $utf8NoBom = [Text.UTF8Encoding]::new($false)
    [IO.File]::WriteAllText((Join-Path $packageRoot "manifest.json"), $seedManifestJson + [Environment]::NewLine, $utf8NoBom)

    $writtenManifest = Get-Content -LiteralPath (Join-Path $packageRoot "manifest.json") -Raw | ConvertFrom-Json
    if ($null -ne $writtenManifest.PSObject.Properties["key"]) {
        throw "Draft identity seed manifest still contains a development key."
    }

    $unexpected = Get-ChildItem -LiteralPath $packageRoot -Recurse -File | Where-Object {
        $_.Extension -in @(".map", ".pem", ".p12", ".pfx", ".key")
    }
    if ($unexpected) {
        throw "Draft identity seed contains prohibited development or key material."
    }

    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $safeVersion = ([string] $sourceManifest.version_name) -replace '[^0-9A-Za-z._-]', '-'
    $archivePath = Join-Path $OutputDirectory "PLwC-Chat-Bridge-$safeVersion-DRAFT-IDENTITY-SEED-DO-NOT-SUBMIT.zip"
    if (Test-Path -LiteralPath $archivePath) {
        Remove-Item -LiteralPath $archivePath -Force
    }
    Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $archivePath -CompressionLevel Optimal

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        $entryNames = @($archive.Entries | ForEach-Object { $_.FullName -replace '\\', '/' })
        foreach ($required in @("manifest.json", "background.js", "content.js", "icons/plwc-icon-512.png")) {
            if ($entryNames -notcontains $required) {
                throw "Draft identity seed is missing archive-root entry: $required"
            }
        }
        if ($entryNames | Where-Object { $_ -match '(?i)\.(?:map|pem|p12|pfx|key)$' }) {
            throw "Draft identity seed archive contains prohibited development or key material."
        }
    } finally {
        $archive.Dispose()
    }

    $hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    Write-Output "Draft identity seed created (unpublished item creation only; do not submit):"
    Write-Output $archivePath
    Write-Output "SHA-256: $hash"
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
