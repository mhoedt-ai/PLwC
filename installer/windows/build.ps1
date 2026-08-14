[CmdletBinding()]
param(
    [switch] $ValidateOnly,
    [switch] $Unsigned,
    [switch] $SkipNodeBuild,
    [switch] $NoMcpb,
    [string] $McpbPath,
    [string] $IsccPath,
    [string] $GeneratedOutputRoot,
    [string] $SignToolPath,
    [string] $SigningCertificateThumbprint,
    [string] $SigningTimestampUrl
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$installerRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$repoRoot = [IO.Path]::GetFullPath((Join-Path $installerRoot "..\.."))
$testOutputRoot = [IO.Path]::GetFullPath((Join-Path $installerRoot ".test-build"))
$unsignedOutputRoot = [IO.Path]::GetFullPath((Join-Path $installerRoot ".unsigned-build"))
$buildOutputRoot = if ([string]::IsNullOrWhiteSpace($GeneratedOutputRoot)) {
    if ($Unsigned) { $unsignedOutputRoot } else { $installerRoot }
}
else {
    [IO.Path]::GetFullPath($GeneratedOutputRoot)
}
if (-not $buildOutputRoot.Equals($installerRoot, [StringComparison]::OrdinalIgnoreCase) -and
    -not $buildOutputRoot.Equals($testOutputRoot, [StringComparison]::OrdinalIgnoreCase) -and
    -not ($Unsigned -and $buildOutputRoot.Equals($unsignedOutputRoot, [StringComparison]::OrdinalIgnoreCase))) {
    throw "Refusing unsafe generated output root '$buildOutputRoot'."
}
$stageRoot = [IO.Path]::GetFullPath((Join-Path $buildOutputRoot "stage"))
$distRoot = [IO.Path]::GetFullPath((Join-Path $buildOutputRoot "dist"))
$setupScript = Join-Path $installerRoot "PLwCSetup.iss"
$fixedTimestamp = [DateTime]::SpecifyKind([DateTime]::ParseExact("2000-01-01", "yyyy-MM-dd", [Globalization.CultureInfo]::InvariantCulture), [DateTimeKind]::Utc)

if ($ValidateOnly -and $Unsigned) {
    throw "Use either -ValidateOnly or -Unsigned, not both."
}
if ($Unsigned -and (
    -not [string]::IsNullOrWhiteSpace($SignToolPath) -or
    -not [string]::IsNullOrWhiteSpace($SigningCertificateThumbprint) -or
    -not [string]::IsNullOrWhiteSpace($SigningTimestampUrl)
)) {
    throw "Do not combine -Unsigned with explicit signing parameters."
}

function Assert-DirectChildPath {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Parent,
        [Parameter(Mandatory = $true)][string] $ExpectedName
    )

    $resolvedParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\', '/')
    $resolvedPath = [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $expected = Join-Path $resolvedParent $ExpectedName
    if (-not $resolvedPath.Equals($expected, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing unsafe build path '$resolvedPath'; expected '$expected'."
    }
}

function Reset-BuildDirectory {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $ExpectedName
    )

    Assert-DirectChildPath -Path $Path -Parent $buildOutputRoot -ExpectedName $ExpectedName
    if (Test-Path -LiteralPath $Path) {
        Remove-DirectoryWithRetry -Path $Path
    }
    [IO.Directory]::CreateDirectory($Path) | Out-Null
}

function Remove-DirectoryWithRetry {
    param([Parameter(Mandatory = $true)][string] $Path)

    for ($attempt = 1; $attempt -le 10; $attempt++) {
        try {
            [IO.Directory]::Delete($Path, $true)
            return
        }
        catch [IO.IOException] {
            if ($attempt -eq 10) {
                throw
            }
            Start-Sleep -Milliseconds 500
        }
        catch [UnauthorizedAccessException] {
            if ($attempt -eq 10) {
                throw
            }
            Start-Sleep -Milliseconds 500
        }
    }
}

function Write-Utf8File {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Content
    )

    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        [IO.Directory]::CreateDirectory($parent) | Out-Null
    }
    $normalized = $Content.Replace("`r`n", "`n").Replace("`r", "`n")
    [IO.File]::WriteAllText($Path, $normalized, [Text.UTF8Encoding]::new($false))
}

function Copy-BuildFile {
    param(
        [Parameter(Mandatory = $true)][string] $Source,
        [Parameter(Mandatory = $true)][string] $Destination
    )

    if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) {
        throw "Required build input not found: $Source"
    }
    $parent = Split-Path -Parent $Destination
    [IO.Directory]::CreateDirectory($parent) | Out-Null
    [IO.File]::Copy((Resolve-Path -LiteralPath $Source).Path, $Destination, $true)
}

function Copy-FilteredTree {
    param(
        [Parameter(Mandatory = $true)][string] $Source,
        [Parameter(Mandatory = $true)][string] $Destination,
        [Parameter(Mandatory = $true)][scriptblock] $Include
    )

    $resolvedSource = (Resolve-Path -LiteralPath $Source).Path.TrimEnd('\', '/')
    $reparsePoints = @(Get-ChildItem -LiteralPath $resolvedSource -Recurse -Force | Where-Object {
        ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    })
    if ($reparsePoints.Count -gt 0) {
        throw "Build input contains a reparse point: $($reparsePoints[0].FullName)"
    }

    foreach ($file in Get-ChildItem -LiteralPath $resolvedSource -Recurse -File -Force) {
        $relativePath = $file.FullName.Substring($resolvedSource.Length).TrimStart('\', '/')
        if (& $Include $file $relativePath) {
            Copy-BuildFile -Source $file.FullName -Destination (Join-Path $Destination $relativePath)
        }
    }
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string] $FilePath,
        [Parameter(Mandatory = $true)][string[]] $ArgumentList,
        [Parameter(Mandatory = $true)][string] $WorkingDirectory
    )

    Push-Location -LiteralPath $WorkingDirectory
    try {
        & $FilePath @ArgumentList
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed with exit code $LASTEXITCODE`: $FilePath $($ArgumentList -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

function Get-PackageVersion {
    $manifestPath = Join-Path $repoRoot "manifest.json"
    $projectPath = Join-Path $repoRoot "pyproject.toml"
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $projectText = Get-Content -LiteralPath $projectPath -Raw
    $projectMatch = [regex]::Match($projectText, '(?m)^version\s*=\s*"([^"]+)"\s*$')
    if (-not $projectMatch.Success) {
        throw "Could not determine the gateway version from pyproject.toml."
    }

    $manifestVersion = [string] $manifest.version
    $projectVersion = $projectMatch.Groups[1].Value
    if ([string]::IsNullOrWhiteSpace($manifestVersion) -or
        (($manifestVersion -replace '-', '') -ne ($projectVersion -replace '-', ''))) {
        throw "Gateway version mismatch: manifest '$manifestVersion', project '$projectVersion'."
    }
    if ($manifestVersion -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
        throw "Gateway manifest version is not installer-safe: $manifestVersion"
    }
    return $manifestVersion
}

function Get-InstallerRevision {
    $setupSource = Get-Content -LiteralPath $setupScript -Raw
    $match = [regex]::Match(
        $setupSource,
        '(?m)^\s*#define\s+InstallerRevision\s+"(?<Revision>installer-r[1-9][0-9]*)"\s*$'
    )
    if (-not $match.Success) {
        throw "Could not determine a valid installer revision from PLwCSetup.iss."
    }
    return $match.Groups["Revision"].Value
}

function Assert-InstallerSafeVersion {
    param(
        [Parameter(Mandatory = $true)][string] $Name,
        [Parameter(Mandatory = $true)][string] $Version
    )

    if ($Version -notmatch '^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$') {
        throw "$Name version is not installer-safe: $Version"
    }
}

function Resolve-McpbArtifact {
    param([Parameter(Mandatory = $true)][string] $Version)

    if ($NoMcpb) {
        if (-not [string]::IsNullOrWhiteSpace($McpbPath)) {
            throw "Use either -NoMcpb or -McpbPath, not both."
        }
        return $null
    }

    if (-not [string]::IsNullOrWhiteSpace($McpbPath)) {
        if (-not (Test-Path -LiteralPath $McpbPath -PathType Leaf)) {
            throw "Explicit MCPB artifact not found: $McpbPath"
        }
        $resolved = (Resolve-Path -LiteralPath $McpbPath).Path
        if ([IO.Path]::GetExtension($resolved) -ne ".mcpb") {
            throw "Explicit MCPB artifact must use the .mcpb extension: $resolved"
        }
        return $resolved
    }

    $fileName = "plwc-gateway-$Version.mcpb"
    $candidates = @(@(
        (Join-Path $repoRoot "build\mcpb\$fileName"),
        (Join-Path $repoRoot "dist\$fileName")
    ) | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf })

    if ($candidates.Count -eq 0) {
        Write-Host "Optional MCPB artifact not present for version $Version. Claude MCPB payload will be omitted."
        return $null
    }
    if ($candidates.Count -gt 1) {
        $hashes = @($candidates | ForEach-Object { (Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash } | Select-Object -Unique)
        if ($hashes.Count -ne 1) {
            throw "Multiple different MCPB artifacts match version $Version. Select one with -McpbPath."
        }
    }
    return (Resolve-Path -LiteralPath $candidates[0]).Path
}

function Assert-McpbArtifact {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Version
    )

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $archive = [IO.Compression.ZipFile]::OpenRead($Path)
    try {
        $manifestEntry = $null
        foreach ($entry in $archive.Entries) {
            $entryName = $entry.FullName.Replace('\', '/')
            if ($entryName.StartsWith('/') -or $entryName -match '(^|/)\.\.(/|$)' -or $entryName -match '^[A-Za-z]:') {
                throw "MCPB contains an unsafe archive path: $entryName"
            }
            if ($entryName -match '(^|/)(private_evidence|logs?|workspace|\.env)(/|$)' -or
                $entryName -match '(?i)(install_pba2|setup-claude-server|track-installation|desktop-commander)') {
                throw "MCPB contains a forbidden legacy or private path: $entryName"
            }
            if ($entryName -eq "manifest.json") {
                $manifestEntry = $entry
            }
        }
        if ($null -eq $manifestEntry) {
            throw "MCPB artifact has no root manifest.json: $Path"
        }

        $reader = [IO.StreamReader]::new($manifestEntry.Open(), [Text.Encoding]::UTF8, $true)
        try {
            $manifest = $reader.ReadToEnd() | ConvertFrom-Json
        }
        finally {
            $reader.Dispose()
        }
        if ([string] $manifest.name -ne "plwc-gateway" -or [string] $manifest.version -ne $Version) {
            throw "MCPB identity mismatch; expected plwc-gateway $Version."
        }
    }
    finally {
        $archive.Dispose()
    }
}

function Find-CSharpCompiler {
    $command = Get-Command csc.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $command) {
        return $command.Source
    }

    foreach ($candidate in @(
        (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe")
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "A C# compiler is required to build the Chat Bridge native launcher."
}

function Build-NativeLauncher {
    param(
        [Parameter(Mandatory = $true)][string] $DestinationRoot,
        [Parameter(Mandatory = $true)][string] $BuildIdentityPath
    )

    $source = Join-Path $repoRoot "integrations\plwc-chat-bridge\native\launcher-host\Plwc.ChatBridge.NativeLauncher.cs"
    $sourceDestination = Join-Path $DestinationRoot "launcher-host\Plwc.ChatBridge.NativeLauncher.cs"
    $exeDestination = Join-Path $DestinationRoot "bin\plwc-chat-bridge-launcher.exe"
    Copy-BuildFile -Source $source -Destination $sourceDestination
    [IO.Directory]::CreateDirectory((Split-Path -Parent $exeDestination)) | Out-Null

    $compiler = Find-CSharpCompiler
    $buildIdentityResource = "/resource:$BuildIdentityPath,Plwc.ChatBridge.BuildIdentity.json"
    & $compiler /nologo /target:exe /reference:System.Web.Extensions.dll $buildIdentityResource "/out:$exeDestination" $source
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $exeDestination -PathType Leaf)) {
        throw "C# compiler failed to build the Chat Bridge native launcher."
    }
}

function Get-BuildSetting {
    param(
        [AllowEmptyString()][string] $ExplicitValue,
        [Parameter(Mandatory = $true)][string] $EnvironmentName
    )

    if (-not [string]::IsNullOrWhiteSpace($ExplicitValue)) {
        return $ExplicitValue.Trim()
    }
    foreach ($target in @("Process", "User")) {
        $value = [Environment]::GetEnvironmentVariable($EnvironmentName, $target)
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value.Trim()
        }
    }
    return ""
}

function Resolve-SignToolPath {
    param([AllowEmptyString()][string] $RequestedPath)

    $configuredPath = Get-BuildSetting `
        -ExplicitValue $RequestedPath `
        -EnvironmentName "PLWC_SIGNTOOL_PATH"
    $candidates = @()
    if (-not [string]::IsNullOrWhiteSpace($configuredPath)) {
        $candidates += $configuredPath
    }
    $localToolsRoot = Join-Path $env:LOCALAPPDATA "PLwC\tools\windows-sdk-build-tools"
    if (Test-Path -LiteralPath $localToolsRoot -PathType Container) {
        $candidates += @(
            Get-ChildItem -LiteralPath $localToolsRoot -Recurse -Filter "signtool.exe" -File |
                Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
                Sort-Object FullName -Descending |
                ForEach-Object { $_.FullName }
        )
    }
    $windowsKitsRoot = Join-Path ${env:ProgramFiles(x86)} "Windows Kits\10\bin"
    if (Test-Path -LiteralPath $windowsKitsRoot -PathType Container) {
        $candidates += @(
            Get-ChildItem -LiteralPath $windowsKitsRoot -Recurse -Filter "signtool.exe" -File |
                Where-Object { $_.FullName -match '\\x64\\signtool\.exe$' } |
                Sort-Object FullName -Descending |
                ForEach-Object { $_.FullName }
        )
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            continue
        }
        $resolved = (Resolve-Path -LiteralPath $candidate).Path
        $signature = Get-AuthenticodeSignature -LiteralPath $resolved
        if ($signature.Status -eq [System.Management.Automation.SignatureStatus]::Valid -and
            $null -ne $signature.SignerCertificate -and
            $signature.SignerCertificate.Subject -match '(^|,\s*)O=Microsoft Corporation(,|$)') {
            return $resolved
        }
    }
    throw "A Microsoft-signed x64 SignTool is required. Set PLWC_SIGNTOOL_PATH or use -SignToolPath."
}

function New-SigningContext {
    param(
        [AllowEmptyString()][string] $RequestedSignToolPath,
        [AllowEmptyString()][string] $RequestedCertificateThumbprint,
        [AllowEmptyString()][string] $RequestedTimestampUrl
    )

    $resolvedSignTool = Resolve-SignToolPath -RequestedPath $RequestedSignToolPath
    $thumbprint = Get-BuildSetting `
        -ExplicitValue $RequestedCertificateThumbprint `
        -EnvironmentName "PLWC_SIGNING_CERT_THUMBPRINT"
    $thumbprint = ($thumbprint -replace '\s', '').ToUpperInvariant()
    if ($thumbprint -notmatch '^[0-9A-F]{40}$') {
        throw "A CurrentUser code-signing certificate thumbprint is required. Set PLWC_SIGNING_CERT_THUMBPRINT or use -SigningCertificateThumbprint."
    }
    $certificatePath = "Cert:\CurrentUser\My\$thumbprint"
    if (-not (Test-Path -LiteralPath $certificatePath)) {
        throw "The configured code-signing certificate was not found in Cert:\CurrentUser\My: $thumbprint"
    }
    $certificate = Get-Item -LiteralPath $certificatePath
    if (-not $certificate.HasPrivateKey) {
        throw "The configured code-signing certificate has no accessible private key: $thumbprint"
    }
    if ($certificate.NotBefore.ToUniversalTime() -gt [DateTime]::UtcNow -or
        $certificate.NotAfter.ToUniversalTime() -le [DateTime]::UtcNow) {
        throw "The configured code-signing certificate is not currently valid: $thumbprint"
    }
    $codeSigningEkus = @(
        $certificate.EnhancedKeyUsageList |
            Where-Object { $_.ObjectId.Value -eq '1.3.6.1.5.5.7.3.3' }
    )
    if ($codeSigningEkus.Count -ne 1) {
        throw "The configured certificate is not valid for code signing: $thumbprint"
    }

    $timestampUrl = Get-BuildSetting `
        -ExplicitValue $RequestedTimestampUrl `
        -EnvironmentName "PLWC_SIGNING_TIMESTAMP_URL"
    $timestampUri = $null
    if (-not [Uri]::TryCreate($timestampUrl, [UriKind]::Absolute, [ref] $timestampUri) -or
        $timestampUri.Scheme -notin @("http", "https")) {
        throw "An HTTP(S) RFC 3161 timestamp URL is required. Set PLWC_SIGNING_TIMESTAMP_URL or use -SigningTimestampUrl."
    }

    return [pscustomobject]@{
        SignToolPath = $resolvedSignTool
        CertificateThumbprint = $thumbprint
        CertificateSubject = $certificate.Subject
        CertificateIssuer = $certificate.Issuer
        CertificateNotAfterUtc = $certificate.NotAfter.ToUniversalTime().ToString("o")
        TimestampUrl = $timestampUri.AbsoluteUri
    }
}

function Assert-AuthenticodeSignature {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)] $Context
    )

    Invoke-CheckedCommand `
        -FilePath $Context.SignToolPath `
        -ArgumentList @("verify", "/pa", "/all", "/tw", $Path) `
        -WorkingDirectory (Split-Path -Parent $Path)
    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::Valid -or
        $null -eq $signature.SignerCertificate -or
        $signature.SignerCertificate.Thumbprint -ne $Context.CertificateThumbprint -or
        $null -eq $signature.TimeStamperCertificate) {
        throw "Authenticode signature or RFC 3161 timestamp verification failed: $Path"
    }
    return [ordered]@{
        status = [string] $signature.Status
        subject = $signature.SignerCertificate.Subject
        issuer = $signature.SignerCertificate.Issuer
        certificateThumbprint = $signature.SignerCertificate.Thumbprint
        certificateNotAfterUtc = $signature.SignerCertificate.NotAfter.ToUniversalTime().ToString("o")
        timestampCertificateSubject = $signature.TimeStamperCertificate.Subject
        timestampCertificateThumbprint = $signature.TimeStamperCertificate.Thumbprint
        fileDigest = "SHA256"
        timestampDigest = "SHA256"
        timestampProtocol = "RFC3161"
    }
}

function Invoke-AuthenticodeSigning {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $Description,
        [Parameter(Mandatory = $true)] $Context
    )

    Invoke-CheckedCommand `
        -FilePath $Context.SignToolPath `
        -ArgumentList @(
            "sign",
            "/sha1", $Context.CertificateThumbprint,
            "/fd", "SHA256",
            "/tr", $Context.TimestampUrl,
            "/td", "SHA256",
            "/d", $Description,
            $Path
        ) `
        -WorkingDirectory (Split-Path -Parent $Path)
    return Assert-AuthenticodeSignature -Path $Path -Context $Context
}

function Assert-UnsignedArtifact {
    param([Parameter(Mandatory = $true)][string] $Path)

    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if ($signature.Status -ne [System.Management.Automation.SignatureStatus]::NotSigned) {
        throw "Explicit unsigned build expected an unsigned artifact: $Path (status: $($signature.Status))"
    }
    return [ordered]@{
        status = "NotSigned"
        fileDigest = $null
        timestampDigest = $null
        timestampProtocol = $null
    }
}

function Assert-StagedPayload {
    param([Parameter(Mandatory = $true)][string] $Path)

    $requiredFiles = @(
        "common\docs\getting-started-en.html",
        "common\docs\getting-started-de.html",
        "common\docs\getting-started.css",
        "common\configuration\plwc-config.py",
        "common\configuration\plwc-config-en.html",
        "common\configuration\plwc-config-de.html",
        "common\configuration\plwc-config.css",
        "common\configuration\plwc-config.js",
        "gateway\server.py",
        "gateway\src\plwc_gateway\mcp\server.py",
        "chat-bridge\bridge\dist\src\index.js",
        "chat-bridge\build-identity.json",
        "chat-bridge\bridge\scripts\healthcheck.mjs",
        "chat-bridge\bridge\scripts\launch-bridge.mjs",
        "chat-bridge\extension\manifest.json",
        "chat-bridge\scripts\install-autostart-windows.ps1",
        "chat-bridge\native\bin\plwc-chat-bridge-launcher.exe",
        "chat-bridge\native\extension-identity.json",
        "chat-bridge\config\plwc.example.json"
    )
    foreach ($relativePath in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $Path $relativePath) -PathType Leaf)) {
            throw "Staged payload is missing required file: $relativePath"
        }
    }

    $bridgeConfig = Get-Content -LiteralPath (Join-Path $Path "chat-bridge\config\plwc.example.json") -Raw | ConvertFrom-Json
    if ([string] $bridgeConfig.bridge.host -ne "127.0.0.1" -or [int] $bridgeConfig.tools.expectedPublicToolCount -ne 8 -or
        $bridgeConfig.tools.publicFacadeOnly -ne $true) {
        throw "Staged Chat Bridge must bind to loopback and expose exactly eight public PLwC tools."
    }

    $stagedBuildIdentityPath = Join-Path $Path "chat-bridge\build-identity.json"
    $stagedBuildIdentity = Get-Content -LiteralPath $stagedBuildIdentityPath -Raw | ConvertFrom-Json
    $launcherPath = Join-Path $Path "chat-bridge\native\bin\plwc-chat-bridge-launcher.exe"
    $launcherBuildIdentity = (& $launcherPath --build-identity) | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or
        [string] $launcherBuildIdentity.buildId -ne [string] $stagedBuildIdentity.buildId -or
        [string] $launcherBuildIdentity.components.nodeBridge -ne [string] $stagedBuildIdentity.components.nodeBridge -or
        [string] $launcherBuildIdentity.components.browserExtension -ne [string] $stagedBuildIdentity.components.browserExtension -or
        [string] $launcherBuildIdentity.components.nativeLauncher -ne [string] $stagedBuildIdentity.components.nativeLauncher) {
        throw "Staged native launcher build identity does not match the staged Chat Bridge identity."
    }

    $forbidden = @(
        Get-ChildItem -LiteralPath $Path -Recurse -File -Force | Where-Object {
            $relative = $_.FullName.Substring($Path.Length).TrimStart('\', '/').Replace('\', '/')
            $relative -match '(^|/)(private_evidence|logs?|workspace|\.git|\.env)(/|$)' -or
            $relative -match '(?i)(install_pba2|setup-claude-server|track-installation|desktop-commander)' -or
            $_.Extension -match '(?i)^\.(pem|key|pfx|p12)$'
        }
    )
    if ($forbidden.Count -gt 0) {
        throw "Forbidden file entered staged payload: $($forbidden[0].FullName)"
    }

    $reparsePoints = @(Get-ChildItem -LiteralPath $Path -Recurse -Force | Where-Object {
        ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    })
    if ($reparsePoints.Count -gt 0) {
        throw "Staged payload contains a reparse point: $($reparsePoints[0].FullName)"
    }
}

function Set-DeterministicTimestamps {
    param([Parameter(Mandatory = $true)][string] $Path)

    foreach ($item in Get-ChildItem -LiteralPath $Path -Recurse -Force) {
        $timestampSet = $false
        for ($attempt = 1; $attempt -le 5; $attempt++) {
            try {
                $item.LastWriteTimeUtc = $fixedTimestamp
                $timestampSet = $true
                break
            }
            catch [IO.IOException] {
                if ($attempt -eq 5) {
                    throw
                }
                Start-Sleep -Milliseconds 300
            }
            catch [UnauthorizedAccessException] {
                if ($attempt -eq 5) {
                    throw
                }
                Start-Sleep -Milliseconds 300
            }
        }
        if (-not $timestampSet) {
            throw "Failed to normalize build timestamp: $($item.FullName)"
        }
    }
}

function Write-PayloadManifest {
    param(
        [Parameter(Mandatory = $true)][string] $Path,
        [Parameter(Mandatory = $true)][string] $ProductVersion,
        [Parameter(Mandatory = $true)][string] $GatewayVersion,
        [Parameter(Mandatory = $true)][string] $InstallerRevision,
        [AllowNull()][string] $McpbArtifact,
        [Parameter(Mandatory = $true)] $BuildIdentity
    )

    $manifestPath = Join-Path $Path "payload-manifest.json"
    $relativePaths = @(
        Get-ChildItem -LiteralPath $Path -Recurse -File -Force |
            Where-Object { $_.FullName -ne $manifestPath } |
            ForEach-Object { $_.FullName.Substring($Path.Length).TrimStart('\', '/').Replace('\', '/') }
    )
    [Array]::Sort($relativePaths, [StringComparer]::Ordinal)

    $files = @($relativePaths | ForEach-Object {
        $file = Get-Item -LiteralPath (Join-Path $Path $_)
        [ordered]@{
            path = $_
            sha256 = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
            size = [long] $file.Length
        }
    })
    $payloadSizeBytes = [long] ((
        $files |
            ForEach-Object { [long] $_["size"] } |
            Measure-Object -Sum
    ).Sum)
    $payloadSizeMiB = [int] [Math]::Ceiling($payloadSizeBytes / 1MB)
    $mcpbAvailable = -not [string]::IsNullOrWhiteSpace($McpbArtifact)
    $components = @(
        [ordered]@{ id = "gateway"; required = $true; available = $true; version = $GatewayVersion },
        [ordered]@{ id = "claude-mcpb"; required = $false; available = $mcpbAvailable; version = $(if ($mcpbAvailable) { $GatewayVersion } else { $null }) },
        [ordered]@{ id = "stdio-codex"; required = $false; available = $true; version = $GatewayVersion },
        [ordered]@{ id = "stdio-odysseus"; required = $false; available = $true; version = $GatewayVersion },
        [ordered]@{
            id = "chat-bridge"
            required = $false
            available = $true
            version = [string] $BuildIdentity.releaseVersion
            buildId = [string] $BuildIdentity.buildId
            identityPath = "chat-bridge/build-identity.json"
            components = [ordered]@{
                nodeBridge = [string] $BuildIdentity.components.nodeBridge
                browserExtension = [string] $BuildIdentity.components.browserExtension
                nativeLauncher = [string] $BuildIdentity.components.nativeLauncher
            }
        }
    )
    $payloadManifest = [ordered]@{
        schemaVersion = 1
        product = "PLwC"
        version = $ProductVersion
        hashAlgorithm = "SHA256"
        payloadSizeBytes = $payloadSizeBytes
        payloadSizeMiB = $payloadSizeMiB
        installer = [ordered]@{
            revision = $InstallerRevision
            artifactName = "PLwC-Setup-$ProductVersion-$InstallerRevision.exe"
            buildIdentityArtifact = "PLwC-$ProductVersion-$InstallerRevision-build-identity.json"
            evidencePackage = "CHAT-BRIDGE-1.0"
            evidencePath = "docs/evidence/CHAT_BRIDGE_1_0_ACCEPTANCE_EN.md"
            components = [ordered]@{
                gateway = $GatewayVersion
                nodeBridge = [string] $BuildIdentity.components.nodeBridge
                browserExtension = [string] $BuildIdentity.components.browserExtension
                nativeLauncher = [string] $BuildIdentity.components.nativeLauncher
            }
        }
        components = $components
        files = $files
    }
    Write-Utf8File -Path $manifestPath -Content (($payloadManifest | ConvertTo-Json -Depth 8) + "`n")
    return $manifestPath
}

function Resolve-Iscc {
    if (-not [string]::IsNullOrWhiteSpace($IsccPath)) {
        if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) {
            throw "ISCC not found at explicit path: $IsccPath"
        }
        return (Resolve-Path -LiteralPath $IsccPath).Path
    }

    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -ne $command) {
        return $command.Source
    }
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Inno Setup 6 compiler (ISCC.exe) was not found. Use -IsccPath or install Inno Setup 6."
}

function Write-InstallerBuildIdentity {
    param(
        [Parameter(Mandatory = $true)][string] $InstallerPath,
        [Parameter(Mandatory = $true)][string] $PayloadManifestPath,
        [Parameter(Mandatory = $true)][string] $ProductVersion,
        [Parameter(Mandatory = $true)][string] $GatewayVersion,
        [Parameter(Mandatory = $true)][string] $InstallerRevision,
        [Parameter(Mandatory = $true)] $BridgeBuildIdentity,
        [Parameter(Mandatory = $true)] $InstallerSignature,
        [Parameter(Mandatory = $true)] $NativeLauncherSignature,
        [Parameter(Mandatory = $true)][bool] $UnsignedBuild
    )

    $installerName = [IO.Path]::GetFileName($InstallerPath)
    $payloadManifestName = [IO.Path]::GetFileName($PayloadManifestPath)
    $installerSha256 = (Get-FileHash -LiteralPath $InstallerPath -Algorithm SHA256).
        Hash.ToLowerInvariant()
    $payloadManifestSha256 = (
        Get-FileHash -LiteralPath $PayloadManifestPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    $identityPath = Join-Path $distRoot (
        "PLwC-$ProductVersion-$InstallerRevision-build-identity.json"
    )
    $identity = [ordered]@{
        schemaVersion = 1
        product = "PLwC Windows Setup"
        buildId = "plwc-windows-setup@$ProductVersion/$InstallerRevision#sha256:$installerSha256"
        installer = [ordered]@{
            version = $ProductVersion
            revision = $InstallerRevision
            artifact = $installerName
            sha256 = $installerSha256
        }
        payloadManifest = [ordered]@{
            artifact = $payloadManifestName
            sha256 = $payloadManifestSha256
        }
        components = [ordered]@{
            gateway = $GatewayVersion
            nodeBridge = [string] $BridgeBuildIdentity.components.nodeBridge
            browserExtension = [string] $BridgeBuildIdentity.components.browserExtension
            nativeLauncher = [string] $BridgeBuildIdentity.components.nativeLauncher
        }
        signing = $(if ($UnsignedBuild) {
            [ordered]@{
                required = $false
                mode = "explicit_unsigned"
                warning = "The Product Owner explicitly requested an unsigned Windows build. Windows may identify the publisher as unknown."
                installer = $InstallerSignature
                nativeLauncher = $NativeLauncherSignature
            }
        }
        else {
            [ordered]@{
                required = $true
                mode = "authenticode_sha256_rfc3161"
                installer = $InstallerSignature
                nativeLauncher = $NativeLauncherSignature
            }
        })
        evidence = [ordered]@{
            package = "CHAT-BRIDGE-1.0"
            acceptanceRecord = "docs/evidence/CHAT_BRIDGE_1_0_ACCEPTANCE_EN.md"
        }
    }
    Write-Utf8File -Path $identityPath -Content (($identity | ConvertTo-Json -Depth 8) + "`n")
    (Get-Item -LiteralPath $identityPath).LastWriteTimeUtc = $fixedTimestamp
    return $identityPath
}

function Write-DistChecksums {
    $checksumPath = Join-Path $distRoot "SHA256SUMS.txt"
    $relativePaths = @(
        Get-ChildItem -LiteralPath $distRoot -Recurse -File -Force |
            Where-Object { $_.FullName -ne $checksumPath } |
            ForEach-Object { $_.FullName.Substring($distRoot.Length).TrimStart('\', '/').Replace('\', '/') }
    )
    [Array]::Sort($relativePaths, [StringComparer]::Ordinal)
    $lines = @($relativePaths | ForEach-Object {
        $hash = (Get-FileHash -LiteralPath (Join-Path $distRoot $_) -Algorithm SHA256).Hash.ToLowerInvariant()
        "$hash  $_"
    })
    Write-Utf8File -Path $checksumPath -Content (($lines -join "`n") + "`n")
}

$buildMutex = [Threading.Mutex]::new($false, "Local\PLwC-Windows-Installer-Build")
$buildMutexAcquired = $false
try {
    try {
        $buildMutexAcquired = $buildMutex.WaitOne([TimeSpan]::FromMinutes(10))
    }
    catch [Threading.AbandonedMutexException] {
        $buildMutexAcquired = $true
    }
    if (-not $buildMutexAcquired) {
        throw "Timed out waiting for another PLwC Windows installer build to finish."
    }

    $gatewayVersion = Get-PackageVersion
    $installerRevision = Get-InstallerRevision
    $bridgeSource = Join-Path $repoRoot "integrations\plwc-chat-bridge"
    $buildIdentityPath = Join-Path $bridgeSource "build-identity.json"
    $buildIdentity = Get-Content -LiteralPath $buildIdentityPath -Raw | ConvertFrom-Json
    $bridgeWorkspacePackage = Get-Content -LiteralPath (Join-Path $bridgeSource "package.json") -Raw | ConvertFrom-Json
    $bridgePackage = Get-Content -LiteralPath (Join-Path $repoRoot "integrations\plwc-chat-bridge\bridge\package.json") -Raw | ConvertFrom-Json
    $extensionPackage = Get-Content -LiteralPath (Join-Path $bridgeSource "extension\package.json") -Raw | ConvertFrom-Json
    $extensionManifest = Get-Content -LiteralPath (Join-Path $bridgeSource "extension\src\manifest.json") -Raw | ConvertFrom-Json
    $productVersion = [string] $buildIdentity.releaseVersion
    if ([int] $buildIdentity.schemaVersion -ne 1 -or
        [string] $buildIdentity.product -ne "PLwC Chat Bridge" -or
        [string] $buildIdentity.buildId -ne "plwc-chat-bridge@$($buildIdentity.releaseVersion)" -or
        [string] $buildIdentity.installer.componentId -ne "chat-bridge" -or
        [string] $buildIdentity.installer.directoryName -ne "chat-bridge-$($buildIdentity.releaseVersion)" -or
        [string] $buildIdentity.releaseVersion -ne [string] $bridgeWorkspacePackage.version -or
        [string] $buildIdentity.components.nodeBridge -ne [string] $bridgePackage.version -or
        [string] $buildIdentity.components.browserExtension -ne [string] $extensionPackage.version -or
        [string] $buildIdentity.components.browserExtension -ne [string] $extensionManifest.version_name -or
        [string]::IsNullOrWhiteSpace([string] $buildIdentity.components.nativeLauncher)) {
        throw "PLwC Chat Bridge build identity is invalid or inconsistent: $buildIdentityPath"
    }
    Assert-InstallerSafeVersion -Name "PLwC Windows Setup" -Version $productVersion
    Assert-InstallerSafeVersion -Name "Gateway" -Version $gatewayVersion
    Assert-InstallerSafeVersion `
        -Name "Node Bridge" `
        -Version ([string] $buildIdentity.components.nodeBridge)
    Assert-InstallerSafeVersion `
        -Name "Browser Extension" `
        -Version ([string] $buildIdentity.components.browserExtension)
    Assert-InstallerSafeVersion `
        -Name "Native Launcher" `
        -Version ([string] $buildIdentity.components.nativeLauncher)
    $signingContext = $null
    $nativeLauncherSignature = $null
    $installerSignature = $null
    if (-not $ValidateOnly -and -not $Unsigned) {
        $signingContext = New-SigningContext `
            -RequestedSignToolPath $SignToolPath `
            -RequestedCertificateThumbprint $SigningCertificateThumbprint `
            -RequestedTimestampUrl $SigningTimestampUrl
    }
    elseif ($Unsigned) {
        Write-Warning "Building an explicitly unsigned Windows installer at the Product Owner's request."
    }
    $npm = Get-Command npm.cmd -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $npm) {
        throw "npm.cmd is required to build and stage PLwC Chat Bridge."
    }

    Reset-BuildDirectory -Path $stageRoot -ExpectedName "stage"
    Reset-BuildDirectory -Path $distRoot -ExpectedName "dist"

$gettingStartedSource = Join-Path $installerRoot "assets\getting-started"
$gettingStartedDestination = Join-Path $stageRoot "common\docs"
foreach ($file in @("getting-started-en.html", "getting-started-de.html", "getting-started.css")) {
    Copy-BuildFile -Source (Join-Path $gettingStartedSource $file) -Destination (Join-Path $gettingStartedDestination $file)
}

$configurationSource = Join-Path $installerRoot "assets\configuration"
$configurationDestination = Join-Path $stageRoot "common\configuration"
foreach ($file in @("plwc-config.py", "plwc-config-en.html", "plwc-config-de.html", "plwc-config.css", "plwc-config.js")) {
    Copy-BuildFile -Source (Join-Path $configurationSource $file) -Destination (Join-Path $configurationDestination $file)
}

$bridgeBuildRoot = Join-Path $bridgeSource "bridge"
$extensionBuildRoot = Join-Path $bridgeSource "extension"
$extensionIdentityPath = Join-Path $bridgeSource "native\extension-identity.json"
$extensionIdentity = Get-Content -LiteralPath $extensionIdentityPath -Raw | ConvertFrom-Json
$stableExtensionId = [string] $extensionIdentity.extensionId
$stableAllowedOrigin = [string] $extensionIdentity.allowedOrigin
if ($stableExtensionId -notmatch '^[a-p]{32}$' -or
    $stableAllowedOrigin -ne "chrome-extension://$stableExtensionId/") {
    throw "Chat Bridge extension identity is invalid or inconsistent: $extensionIdentityPath"
}
$nativeLauncherSource = Join-Path $bridgeSource "native\launcher-host\Plwc.ChatBridge.NativeLauncher.cs"
if ((Get-Content -LiteralPath $nativeLauncherSource -Raw) -notmatch [regex]::Escape($stableExtensionId)) {
    throw "Native launcher does not contain the stable extension ID '$stableExtensionId'."
}
if (-not $SkipNodeBuild) {
    $nodeBuildWorkRoot = Join-Path $stageRoot ".build-work"
    Copy-BuildFile -Source (Join-Path $bridgeSource "package.json") -Destination (Join-Path $nodeBuildWorkRoot "package.json")
    Copy-BuildFile -Source $buildIdentityPath -Destination (Join-Path $nodeBuildWorkRoot "build-identity.json")
    Copy-BuildFile -Source $extensionIdentityPath -Destination (Join-Path $nodeBuildWorkRoot "native\extension-identity.json")
    Copy-BuildFile -Source (Join-Path $bridgeSource "native\manifest\plwc.chat_bridge.launcher.json") -Destination (Join-Path $nodeBuildWorkRoot "native\manifest\plwc.chat_bridge.launcher.json")
    Copy-BuildFile -Source $nativeLauncherSource -Destination (Join-Path $nodeBuildWorkRoot "native\launcher-host\Plwc.ChatBridge.NativeLauncher.cs")
    foreach ($project in @("bridge", "extension")) {
        $sourceProjectRoot = Join-Path $bridgeSource $project
        $workProjectRoot = Join-Path $nodeBuildWorkRoot $project
        Copy-FilteredTree -Source $sourceProjectRoot -Destination $workProjectRoot -Include {
            param($file, $relativePath)
            $normalized = $relativePath.Replace('\', '/')
            $normalized -notmatch '(^|/)(node_modules|dist|\.test-dist|\.browser-fixture)(/|$)'
        }
        Invoke-CheckedCommand -FilePath $npm.Source -ArgumentList @("ci", "--ignore-scripts", "--no-audit", "--no-fund") -WorkingDirectory $workProjectRoot
        Invoke-CheckedCommand -FilePath $npm.Source -ArgumentList @("run", "build") -WorkingDirectory $workProjectRoot
    }
    $bridgeBuildRoot = Join-Path $nodeBuildWorkRoot "bridge"
    $extensionBuildRoot = Join-Path $nodeBuildWorkRoot "extension"
}

$gatewayRoot = Join-Path $stageRoot "gateway"
foreach ($file in @("server.py", "pyproject.toml", "requirements.txt", "manifest.json", "server.json", "LICENSE", "README.md")) {
    Copy-BuildFile -Source (Join-Path $repoRoot $file) -Destination (Join-Path $gatewayRoot $file)
}
Copy-BuildFile -Source (Join-Path $repoRoot "config\security.yaml.example") -Destination (Join-Path $gatewayRoot "config\security.yaml.example")
Copy-FilteredTree -Source (Join-Path $repoRoot "src\plwc_gateway") -Destination (Join-Path $gatewayRoot "src\plwc_gateway") -Include {
    param($file, $relativePath)
    $file.Extension -eq ".py" -or $file.Name -eq ".gitkeep"
}
Copy-FilteredTree -Source (Join-Path $repoRoot "profiles\template") -Destination (Join-Path $gatewayRoot "profiles\template") -Include {
    param($file, $relativePath)
    $file.Extension -in @(".md", ".yaml", ".yml")
}

$chatBridgeRoot = Join-Path $stageRoot "chat-bridge"
foreach ($file in @("README.md", "UPSTREAM.md", "package.json")) {
    Copy-BuildFile -Source (Join-Path $bridgeSource $file) -Destination (Join-Path $chatBridgeRoot $file)
}
Copy-BuildFile -Source $buildIdentityPath -Destination (Join-Path $chatBridgeRoot "build-identity.json")
$sourceBridgeConfig = Get-Content -LiteralPath (Join-Path $bridgeSource "config\plwc.example.json") -Raw | ConvertFrom-Json
$sourceBridgeConfig.gateway.args = @('${configDir}/../../gateway/server.py')
$sourceBridgeConfig.gateway.cwd = '${configDir}/../../gateway'
$stagedBridgeConfigPath = Join-Path $chatBridgeRoot "config\plwc.example.json"
Write-Utf8File -Path $stagedBridgeConfigPath -Content (($sourceBridgeConfig | ConvertTo-Json -Depth 12) + "`n")
Copy-BuildFile -Source (Join-Path $bridgeSource "scripts\start-windows.ps1") -Destination (Join-Path $chatBridgeRoot "scripts\start-windows.ps1")
Copy-BuildFile -Source (Join-Path $bridgeSource "scripts\install-native-launcher-windows.ps1") -Destination (Join-Path $chatBridgeRoot "scripts\install-native-launcher-windows.ps1")
Copy-BuildFile -Source (Join-Path $bridgeSource "scripts\install-autostart-windows.ps1") -Destination (Join-Path $chatBridgeRoot "scripts\install-autostart-windows.ps1")
Copy-FilteredTree -Source (Join-Path $bridgeSource "LICENSES") -Destination (Join-Path $chatBridgeRoot "LICENSES") -Include {
    param($file, $relativePath)
    $true
}

$stagedBridgeProject = Join-Path $chatBridgeRoot "bridge"
foreach ($file in @("package.json", "package-lock.json", "README.md")) {
    Copy-BuildFile -Source (Join-Path $bridgeSource "bridge\$file") -Destination (Join-Path $stagedBridgeProject $file)
}
foreach ($file in @("healthcheck.mjs", "launch-bridge.mjs")) {
    Copy-BuildFile -Source (Join-Path $bridgeSource "bridge\scripts\$file") -Destination (Join-Path $stagedBridgeProject "scripts\$file")
}
Copy-FilteredTree -Source (Join-Path $bridgeBuildRoot "dist\src") -Destination (Join-Path $stagedBridgeProject "dist\src") -Include {
    param($file, $relativePath)
    $file.Extension -in @(".js", ".map", ".ts")
}
Invoke-CheckedCommand -FilePath $npm.Source -ArgumentList @("ci", "--omit=dev", "--ignore-scripts", "--no-audit", "--no-fund") -WorkingDirectory $stagedBridgeProject

Copy-FilteredTree -Source (Join-Path $extensionBuildRoot "dist") -Destination (Join-Path $chatBridgeRoot "extension") -Include {
    param($file, $relativePath)
    $true
}
Build-NativeLauncher `
    -DestinationRoot (Join-Path $chatBridgeRoot "native") `
    -BuildIdentityPath $buildIdentityPath
$nativeLauncherPath = Join-Path $chatBridgeRoot "native\bin\plwc-chat-bridge-launcher.exe"
if ($null -ne $signingContext) {
    $nativeLauncherSignature = Invoke-AuthenticodeSigning `
        -Path $nativeLauncherPath `
        -Description "PLwC Chat Bridge Native Launcher $($buildIdentity.releaseVersion)" `
        -Context $signingContext
}
elseif ($Unsigned) {
    $nativeLauncherSignature = Assert-UnsignedArtifact -Path $nativeLauncherPath
}
Copy-BuildFile -Source $extensionIdentityPath -Destination (Join-Path $chatBridgeRoot "native\extension-identity.json")
if ($null -ne (Get-Variable -Name nodeBuildWorkRoot -ErrorAction SilentlyContinue) -and
    (Test-Path -LiteralPath $nodeBuildWorkRoot)) {
    Assert-DirectChildPath -Path $nodeBuildWorkRoot -Parent $stageRoot -ExpectedName ".build-work"
    Remove-DirectoryWithRetry -Path $nodeBuildWorkRoot
}

$mcpbArtifact = Resolve-McpbArtifact -Version $gatewayVersion
if ($null -ne $mcpbArtifact) {
    Assert-McpbArtifact -Path $mcpbArtifact -Version $gatewayVersion
    Copy-BuildFile -Source $mcpbArtifact -Destination (Join-Path $stageRoot "claude\$([IO.Path]::GetFileName($mcpbArtifact))")
    Write-Host "Included verified MCPB artifact: $mcpbArtifact"
}

Assert-StagedPayload -Path $stageRoot
Set-DeterministicTimestamps -Path $stageRoot
if ($null -ne $signingContext) {
    $nativeLauncherSignature = Assert-AuthenticodeSignature `
        -Path $nativeLauncherPath `
        -Context $signingContext
}
elseif ($Unsigned) {
    $nativeLauncherSignature = Assert-UnsignedArtifact -Path $nativeLauncherPath
}
$payloadManifest = Write-PayloadManifest `
    -Path $stageRoot `
    -ProductVersion $productVersion `
    -GatewayVersion $gatewayVersion `
    -InstallerRevision $installerRevision `
    -McpbArtifact $mcpbArtifact `
    -BuildIdentity $buildIdentity
(Get-Item -LiteralPath $payloadManifest).LastWriteTimeUtc = $fixedTimestamp

$distPayloadManifest = Join-Path $distRoot "PLwC-$productVersion-payload-manifest.json"
Copy-BuildFile -Source $payloadManifest -Destination $distPayloadManifest
(Get-Item -LiteralPath $distPayloadManifest).LastWriteTimeUtc = $fixedTimestamp
$payloadManifestData = Get-Content -LiteralPath $payloadManifest -Raw | ConvertFrom-Json
$plwcPayloadMiB = [int] $payloadManifestData.payloadSizeMiB
if ($plwcPayloadMiB -le 0) {
    throw "The staged PLwC payload size must be greater than zero."
}

    if ($ValidateOnly) {
        Write-DistChecksums
        Set-DeterministicTimestamps -Path $distRoot
        Write-Host "ValidateOnly complete. Payload staged and verified; ISCC was not invoked."
        Write-Host "Stage: $stageRoot"
        Write-Host "Dist:  $distRoot"
        return
    }

if (-not (Test-Path -LiteralPath $setupScript -PathType Leaf)) {
    throw "Inno Setup source not found: $setupScript"
}
$iscc = Resolve-Iscc
$mcpbAvailable = if ($null -ne $mcpbArtifact) { "1" } else { "0" }
$isccArguments = @(
    "/Qp",
    "/O$distRoot",
    "/DAppVersion=$productVersion",
    "/DPLWC_VERSION=$productVersion",
    "/DInstallerRevision=$installerRevision",
    "/DGatewayVersion=$gatewayVersion",
    "/DNodeBridgeVersion=$($buildIdentity.components.nodeBridge)",
    "/DBrowserExtensionVersion=$($buildIdentity.components.browserExtension)",
    "/DNativeLauncherVersion=$($buildIdentity.components.nativeLauncher)",
    "/DPlwcPayloadMiB=$plwcPayloadMiB",
    "/DStageDir=$stageRoot",
    "/DSTAGE_DIR=$stageRoot",
    "/DOutputDir=$distRoot",
    "/DOUTPUT_DIR=$distRoot",
    "/DMcpbAvailable=$mcpbAvailable",
    "/DMCPB_AVAILABLE=$mcpbAvailable",
    "/DBridgeDirectoryName=$($buildIdentity.installer.directoryName)",
    "/DStableChatBridgeExtensionId=$stableExtensionId",
    $setupScript
)
Invoke-CheckedCommand -FilePath $iscc -ArgumentList $isccArguments -WorkingDirectory $installerRoot

$installerPath = Join-Path $distRoot "PLwC-Setup-$productVersion-$installerRevision.exe"
if (-not (Test-Path -LiteralPath $installerPath -PathType Leaf)) {
    throw "ISCC did not produce the expected installer executable: $installerPath"
}
if ($null -ne $signingContext) {
    $installerSignature = Invoke-AuthenticodeSigning `
        -Path $installerPath `
        -Description "PLwC Windows Setup with Chat Bridge $($buildIdentity.releaseVersion)" `
        -Context $signingContext
}
elseif ($Unsigned) {
    $installerSignature = Assert-UnsignedArtifact -Path $installerPath
}
else {
    throw "Internal build error: neither signed nor explicit unsigned mode is active."
}
$installerBuildIdentity = Write-InstallerBuildIdentity `
    -InstallerPath $installerPath `
    -PayloadManifestPath $distPayloadManifest `
    -ProductVersion $productVersion `
    -GatewayVersion $gatewayVersion `
    -InstallerRevision $installerRevision `
    -BridgeBuildIdentity $buildIdentity `
    -InstallerSignature $installerSignature `
    -NativeLauncherSignature $nativeLauncherSignature `
    -UnsignedBuild ([bool] $Unsigned)
Write-DistChecksums
Write-Host "PLwC Windows installer build complete: $installerPath"
Write-Host "Build identity: $installerBuildIdentity"
}
finally {
    if ($buildMutexAcquired) {
        $buildMutex.ReleaseMutex()
    }
    $buildMutex.Dispose()
}
