[CmdletBinding()]
param(
    [string] $OutputDirectory,
    [switch] $SkipBuild
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$extensionRoot = Split-Path -Parent $scriptRoot
$integrationRoot = Split-Path -Parent $extensionRoot
$distRoot = Join-Path $extensionRoot "dist"
$sourceManifestPath = Join-Path $extensionRoot "src\manifest.json"
$storeContractPath = Join-Path $extensionRoot "store\store-contract.json"
$identityContractPath = Join-Path $integrationRoot "native\extension-identity.json"
$buildIdentityPath = Join-Path $integrationRoot "build-identity.json"

if ([string]::IsNullOrWhiteSpace($OutputDirectory)) {
    $OutputDirectory = Join-Path $extensionRoot "store\out"
}
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)

$sourceManifest = Get-Content -LiteralPath $sourceManifestPath -Raw | ConvertFrom-Json
$storeContract = Get-Content -LiteralPath $storeContractPath -Raw | ConvertFrom-Json
$identityContract = Get-Content -LiteralPath $identityContractPath -Raw | ConvertFrom-Json
$buildIdentity = Get-Content -LiteralPath $buildIdentityPath -Raw | ConvertFrom-Json

if (
    $storeContract.schemaVersion -ne 2 -or
    $identityContract.schemaVersion -ne 2 -or
    $sourceManifest.version_name -ne $storeContract.releaseVersion -or
    $sourceManifest.version_name -ne $identityContract.releaseVersion -or
    $sourceManifest.version_name -ne $buildIdentity.releaseVersion
) {
    throw "Store package version and identity contracts are inconsistent."
}

$targets = @(
    [PSCustomObject]@{
        Name = "chrome-brave"
        StoreKey = "chrome"
        IdentityKey = "chromeStore"
    },
    [PSCustomObject]@{
        Name = "edge"
        StoreKey = "edge"
        IdentityKey = "edgeStore"
    }
)
$expectedNativeOrigins = @(
    [string] $identityContract.identities.development.nativeMessagingOrigin,
    [string] $identityContract.identities.chromeStore.nativeMessagingOrigin,
    [string] $identityContract.identities.edgeStore.nativeMessagingOrigin
)
if (
    $expectedNativeOrigins.Count -ne 3 -or
    ($expectedNativeOrigins | Select-Object -Unique).Count -ne 3 -or
    @($expectedNativeOrigins | Where-Object { $_ -notmatch '^chrome-extension://[a-p]{32}/$' -or $_ -match '\*' }).Count -ne 0 -or
    (ConvertTo-Json -Compress @($identityContract.allowedOrigins)) -ne (ConvertTo-Json -Compress $expectedNativeOrigins) -or
    (ConvertTo-Json -Compress @($storeContract.nativeMessaging.allowedOrigins)) -ne (ConvertTo-Json -Compress $expectedNativeOrigins) -or
    $storeContract.nativeMessaging.wildcardsAllowed -ne $false
) {
    throw "Store package Native Messaging origin contract is invalid."
}

if (-not $SkipBuild) {
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if ($null -eq $npm) {
        $npm = Get-Command npm -ErrorAction SilentlyContinue
    }
    if ($null -eq $npm) {
        throw "npm is required to build Store packages."
    }
    Push-Location -LiteralPath $extensionRoot
    try {
        & $npm.Source run build
        if ($LASTEXITCODE -ne 0) {
            throw "The extension build failed with exit code $LASTEXITCODE."
        }
    }
    finally {
        Pop-Location
    }
}

foreach ($requiredFile in @(
    "manifest.json",
    "background.js",
    "content.js",
    "icons\plwc-icon-512.png"
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $distRoot $requiredFile) -PathType Leaf)) {
        throw "The production extension build is missing $requiredFile."
    }
}

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Value
    )
    [IO.File]::WriteAllText($Path, $Value, [Text.UTF8Encoding]::new($false))
}

function Assert-PublicPackageTree {
    param([Parameter(Mandatory = $true)][string] $PackageRoot)

    $expectedEntries = @(
        "background.js",
        "content.js",
        "icons/plwc-icon-512.png",
        "manifest.json"
    )
    $actualEntries = @(
        Get-ChildItem -LiteralPath $PackageRoot -Recurse -File |
            ForEach-Object {
                $_.FullName.Substring($PackageRoot.Length + 1).Replace('\', '/')
            } |
            Sort-Object
    )
    if ((ConvertTo-Json -Compress $actualEntries) -ne (ConvertTo-Json -Compress $expectedEntries)) {
        throw "Store package tree contains a missing or repository-only file: $($actualEntries -join ', ')"
    }

    $manifest = Get-Content -LiteralPath (Join-Path $PackageRoot "manifest.json") -Raw | ConvertFrom-Json
    if ($null -ne $manifest.PSObject.Properties["key"]) {
        throw "Store package manifest contains the development key."
    }
    if ($manifest.version_name -ne $storeContract.releaseVersion) {
        throw "Store package manifest version does not match the Store contract."
    }

    $prohibitedExtensions = @(".map", ".pem", ".p12", ".pfx", ".key", ".env")
    $prohibitedNames = @(
        ".gitignore",
        "AGENTS.md",
        "package.json",
        "package-lock.json",
        "store-contract.json",
        "extension-identity.json",
        "README.md",
        "tsconfig.json"
    )
    $prohibited = Get-ChildItem -LiteralPath $PackageRoot -Recurse -File | Where-Object {
        $_.Extension.ToLowerInvariant() -in $prohibitedExtensions -or $_.Name -in $prohibitedNames
    }
    if ($prohibited) {
        throw "Store package contains prohibited development or repository material."
    }

    $secretPatterns = @(
        '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        '(?i)(?:api[_-]?key|client[_-]?secret|refresh[_-]?token|access[_-]?token|password)\s*[:=]\s*["''][A-Za-z0-9_./+\-=]{12,}["'']',
        '\bAKIA[0-9A-Z]{16}\b',
        '\bgh[pousr]_[A-Za-z0-9]{36,}\b',
        '\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b'
    )
    foreach ($textFile in Get-ChildItem -LiteralPath $PackageRoot -Recurse -File | Where-Object {
        $_.Extension -in @(".js", ".json")
    }) {
        $content = Get-Content -LiteralPath $textFile.FullName -Raw
        foreach ($pattern in $secretPatterns) {
            if ($content -match $pattern) {
                throw "Store package secret scan failed for $($textFile.Name)."
            }
        }
    }
}

function New-DeterministicZip {
    param(
        [Parameter(Mandatory = $true)][string] $PackageRoot,
        [Parameter(Mandatory = $true)][string] $ArchivePath
    )

    Add-Type -AssemblyName System.IO.Compression
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path -LiteralPath $ArchivePath) {
        Remove-Item -LiteralPath $ArchivePath -Force
    }
    $archive = [IO.Compression.ZipFile]::Open($ArchivePath, [IO.Compression.ZipArchiveMode]::Create)
    try {
        $files = Get-ChildItem -LiteralPath $PackageRoot -Recurse -File | Sort-Object FullName
        foreach ($file in $files) {
            $entryName = $file.FullName.Substring($PackageRoot.Length + 1).Replace('\', '/')
            $entry = $archive.CreateEntry($entryName, [IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = [DateTimeOffset]::new(2000, 1, 1, 0, 0, 0, [TimeSpan]::Zero)
            $input = [IO.File]::OpenRead($file.FullName)
            $output = $entry.Open()
            try {
                $input.CopyTo($output)
            }
            finally {
                $output.Dispose()
                $input.Dispose()
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}

function Assert-ArchiveInventory {
    param([Parameter(Mandatory = $true)][string] $ArchivePath)

    $expectedEntries = @(
        "background.js",
        "content.js",
        "icons/plwc-icon-512.png",
        "manifest.json"
    )
    $archive = [IO.Compression.ZipFile]::OpenRead($ArchivePath)
    try {
        $actualEntries = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') } | Sort-Object)
        if ((ConvertTo-Json -Compress $actualEntries) -ne (ConvertTo-Json -Compress $expectedEntries)) {
            throw "Store archive inventory is invalid: $($actualEntries -join ', ')"
        }
        if ($actualEntries -notcontains "manifest.json") {
            throw "Store archive does not contain manifest.json at the archive root."
        }
    }
    finally {
        $archive.Dispose()
    }
}

$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("plwc-store-packages-" + [Guid]::NewGuid().ToString("N"))
$packageRoot = Join-Path $temporaryRoot "package"

try {
    New-Item -ItemType Directory -Path (Join-Path $packageRoot "icons") -Force | Out-Null
    Copy-Item -LiteralPath (Join-Path $distRoot "background.js") -Destination (Join-Path $packageRoot "background.js")
    Copy-Item -LiteralPath (Join-Path $distRoot "content.js") -Destination (Join-Path $packageRoot "content.js")
    Copy-Item -LiteralPath (Join-Path $distRoot "icons\plwc-icon-512.png") -Destination (Join-Path $packageRoot "icons\plwc-icon-512.png")

    $packageManifest = Get-Content -LiteralPath (Join-Path $distRoot "manifest.json") -Raw | ConvertFrom-Json
    if ($null -eq $packageManifest.PSObject.Properties["key"]) {
        throw "The development build manifest did not contain the key that Store packaging must remove."
    }
    $packageManifest.PSObject.Properties.Remove("key")
    Write-Utf8NoBom `
        -Path (Join-Path $packageRoot "manifest.json") `
        -Value (($packageManifest | ConvertTo-Json -Depth 100) + [Environment]::NewLine)

    Assert-PublicPackageTree -PackageRoot $packageRoot
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
    $safeVersion = ([string] $sourceManifest.version_name) -replace '[^0-9A-Za-z._-]', '-'

    foreach ($target in $targets) {
        $store = $storeContract.stores.PSObject.Properties[$target.StoreKey].Value
        $identity = $identityContract.identities.PSObject.Properties[$target.IdentityKey].Value
        if (
            $store.packageTarget -ne $target.Name -or
            $store.extensionId -ne $identity.extensionId -or
            $store.nativeMessagingOrigin -ne $identity.nativeMessagingOrigin -or
            $store.webSocketOrigin -ne $identity.webSocketOrigin
        ) {
            throw "Store target $($target.Name) does not match the canonical identity contract."
        }

        $archiveName = "PLwC-Chat-Bridge-$safeVersion-$($target.Name)-store.zip"
        $archivePath = Join-Path $OutputDirectory $archiveName
        New-DeterministicZip -PackageRoot $packageRoot -ArchivePath $archivePath
        Assert-ArchiveInventory -ArchivePath $archivePath
        $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
        $archiveSize = (Get-Item -LiteralPath $archivePath).Length

        $sidecar = [ordered]@{
            schemaVersion = 1
            product = "PLwC Chat Bridge"
            releaseVersion = [string] $sourceManifest.version_name
            buildId = [string] $buildIdentity.buildId
            target = [string] $target.Name
            expectedExtensionId = [string] $identity.extensionId
            expectedNativeMessagingOrigin = [string] $identity.nativeMessagingOrigin
            archive = [ordered]@{
                fileName = $archiveName
                bytes = $archiveSize
                sha256 = $archiveHash
            }
            entries = @(
                "background.js",
                "content.js",
                "icons/plwc-icon-512.png",
                "manifest.json"
            )
        }
        $sidecarPath = Join-Path $OutputDirectory "PLwC-Chat-Bridge-$safeVersion-$($target.Name)-store-build-identity.json"
        Write-Utf8NoBom -Path $sidecarPath -Value (($sidecar | ConvertTo-Json -Depth 10) + [Environment]::NewLine)

        [PSCustomObject]@{
            Target = $target.Name
            ExtensionId = $identity.extensionId
            Archive = $archivePath
            Bytes = $archiveSize
            Sha256 = $archiveHash
            BuildIdentity = $sidecarPath
        }
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
