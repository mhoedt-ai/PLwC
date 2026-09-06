[CmdletBinding()]
param(
    [ValidatePattern("^[a-p]{32}$")]
    [string[]] $ExtensionId = @(
        "nlogfcafjdfdoknpkbehjgihpafpipdb",
        "feceodobnhefdbfgmbinkndhogpfkicb",
        "nncomjknhhlgcmkmlaljhkiojcnpmflb"
    ),

    [ValidateSet("Chrome", "Edge", "Brave", "Both", "All")]
    [string] $Browser = "All",

    [ValidateSet("de", "en")]
    [string] $Language = "de",

    [switch] $BuildOnly,

    [switch] $SkipBuild,

    [switch] $Uninstall
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $null -ne $IsWindows) {
    throw "PLwC Chat Bridge native launcher installation is only supported on Windows."
}

$integrationRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$buildIdentityPath = Join-Path $integrationRoot "build-identity.json"
$extensionIdentityPath = Join-Path $integrationRoot "native\extension-identity.json"
$sourcePath = Join-Path $integrationRoot "native\launcher-host\Plwc.ChatBridge.NativeLauncher.cs"
$binRoot = Join-Path $integrationRoot "native\bin"
$exePath = Join-Path $binRoot "plwc-chat-bridge-launcher.exe"

if ($BuildOnly -and ($SkipBuild -or $Uninstall)) {
    throw "BuildOnly cannot be combined with SkipBuild or Uninstall."
}

$extensionIdentity = Get-Content -LiteralPath $extensionIdentityPath -Raw | ConvertFrom-Json
$approvedExtensionIds = @(
    $extensionIdentity.identities.development.extensionId,
    $extensionIdentity.identities.chromeStore.extensionId,
    $extensionIdentity.identities.edgeStore.extensionId
)
if (
    $extensionIdentity.schemaVersion -ne 2 -or
    $approvedExtensionIds.Count -ne 3 -or
    ($approvedExtensionIds | Select-Object -Unique).Count -ne 3 -or
    @($ExtensionId | Where-Object { $_ -notin $approvedExtensionIds }).Count -ne 0
) {
    throw "The requested extension identity is not approved by $extensionIdentityPath."
}

function Find-CSharpCompiler {
    $candidates = @(
        (Get-Command csc.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source),
        (Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"),
        (Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe")
    )
    foreach ($candidate in $candidates) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and (Test-Path -LiteralPath $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

if (-not $SkipBuild -and -not $Uninstall) {
    if (-not (Test-Path -LiteralPath $buildIdentityPath -PathType Leaf)) {
        throw "PLwC Chat Bridge build identity was not found: $buildIdentityPath"
    }
    New-Item -ItemType Directory -Force -Path $binRoot | Out-Null
    Write-Host "Compiling PLwC Chat Bridge native launcher..."
    Remove-Item -LiteralPath $exePath -Force -ErrorAction SilentlyContinue
    $csc = Find-CSharpCompiler
    $buildIdentityResource = "/resource:$buildIdentityPath,Plwc.ChatBridge.BuildIdentity.json"
    if ($null -ne $csc) {
        & $csc /nologo /target:exe /reference:System.Web.Extensions.dll $buildIdentityResource /out:$exePath $sourcePath
        if ($LASTEXITCODE -ne 0) {
            throw "C# compiler failed to build the PLwC Chat Bridge native launcher."
        }
    }
    else {
        Add-Type `
            -Path $sourcePath `
            -OutputAssembly $exePath `
            -OutputType ConsoleApplication `
            -ReferencedAssemblies @("System.dll", "System.Web.Extensions.dll") `
            -CompilerOptions $buildIdentityResource
    }
}

if ($Uninstall -and -not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    $registryRoots = switch ($Browser) {
        "Chrome" { @("HKCU:\Software\Google\Chrome\NativeMessagingHosts") }
        "Edge" { @("HKCU:\Software\Microsoft\Edge\NativeMessagingHosts") }
        "Brave" { @("HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts") }
        "Both" {
            @(
                "HKCU:\Software\Google\Chrome\NativeMessagingHosts",
                "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts"
            )
        }
        default {
            @(
                "HKCU:\Software\Google\Chrome\NativeMessagingHosts",
                "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts",
                "HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts"
            )
        }
    }
    foreach ($registryRoot in $registryRoots) {
        Remove-Item `
            -LiteralPath (Join-Path $registryRoot "plwc.chat_bridge.launcher") `
            -Recurse `
            -Force `
            -ErrorAction SilentlyContinue
    }
    $manifestPath = Join-Path $env:APPDATA "PLwC\config\native-messaging\plwc.chat_bridge.launcher.json"
    Remove-Item -LiteralPath $manifestPath -Force -ErrorAction SilentlyContinue
    exit 0
}

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "PLwC Chat Bridge native launcher was not found: $exePath"
}

if ($BuildOnly) {
    Write-Host "Native launcher built: $exePath"
    exit 0
}

$registrationArguments = @(
    $(if ($Uninstall) { "--unregister" } else { "--register" }),
    "--browser",
    $Browser.ToLowerInvariant(),
    "--lang",
    $Language
)
foreach ($id in $approvedExtensionIds) {
    $registrationArguments += @("--extension-id", $id.ToLowerInvariant())
}

& $exePath @registrationArguments
if ($LASTEXITCODE -ne 0) {
    $operation = if ($Uninstall) { "unregistration" } else { "registration" }
    throw "PLwC Chat Bridge native launcher $operation failed with exit code $LASTEXITCODE."
}

if ($Uninstall) {
    $manifestPath = Join-Path $env:APPDATA "PLwC\config\native-messaging\plwc.chat_bridge.launcher.json"
    Remove-Item -LiteralPath $manifestPath -Force -ErrorAction SilentlyContinue
}
else {
    & $exePath --status --browser $Browser.ToLowerInvariant()
    if ($LASTEXITCODE -ne 0) {
        throw "PLwC Chat Bridge native launcher registration verification failed."
    }
}
