[CmdletBinding()]
param(
    [string] $ConfigPath,
    [string] $WorkspaceRoot,
    [string] $ProfileRoot,
    [string] $ActiveProfileName,
    [string] $SecurityConfig,
    [string] $McpbSettingsPath,
    [string] $NodePath,
    [switch] $Detached,
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $PSScriptRoot "..\config\plwc.example.json"
}

$resolvedConfig = Resolve-Path -LiteralPath $ConfigPath
$config = Get-Content -LiteralPath $resolvedConfig -Raw | ConvertFrom-Json

if ($config.bridge.host -ne "127.0.0.1") {
    throw "PLwC Chat Bridge must bind to 127.0.0.1 by default. Found: $($config.bridge.host)"
}

if ($config.tools.publicFacadeOnly -ne $true -or $config.tools.expectedPublicToolCount -ne 8) {
    throw "PLwC Chat Bridge must expose exactly the eight public PLwC facade tools."
}

Write-Host "PLwC Chat Bridge launcher"
Write-Host "Config: $resolvedConfig"
$healthEndpoint = "ws://$($config.bridge.host):$($config.bridge.port)$($config.bridge.path)"
Write-Host "Loopback endpoint: $healthEndpoint"
Write-Host "Gateway command: $($config.gateway.command) $($config.gateway.args -join ' ')"

$bridgeRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\bridge")
$bridgeEntry = Join-Path $bridgeRoot "dist\src\index.js"
$buildIdentityPath = Join-Path $PSScriptRoot "..\build-identity.json"
$extensionIdentityPath = Join-Path $PSScriptRoot "..\native\extension-identity.json"
if (-not (Test-Path -LiteralPath $buildIdentityPath -PathType Leaf)) {
    throw "PLwC Chat Bridge build identity was not found: $buildIdentityPath"
}
$expectedBuildId = [string] (
    Get-Content -LiteralPath $buildIdentityPath -Raw | ConvertFrom-Json
).buildId
$extensionIdentity = Get-Content -LiteralPath $extensionIdentityPath -Raw | ConvertFrom-Json
$healthOrigin = [string] $extensionIdentity.identities.development.webSocketOrigin
if ($extensionIdentity.schemaVersion -ne 2 -or
    $healthOrigin -notmatch '^chrome-extension://[a-p]{32}$') {
    throw "PLwC Chat Bridge extension identity contract is invalid: $extensionIdentityPath"
}
if ([string]::IsNullOrWhiteSpace($expectedBuildId)) {
    throw "PLwC Chat Bridge build identity does not contain a buildId: $buildIdentityPath"
}
Write-Host "Bridge entry: $bridgeEntry"
Write-Host "Expected bridge build: $expectedBuildId"

$mcpbUserConfig = $null
if ([string]::IsNullOrWhiteSpace($McpbSettingsPath) -and -not [string]::IsNullOrWhiteSpace($env:APPDATA)) {
    $candidateSettings = Join-Path $env:APPDATA "Claude\Claude Extensions Settings\local.mcpb.plwc.plwc-gateway.json"
    if (Test-Path -LiteralPath $candidateSettings) {
        $McpbSettingsPath = $candidateSettings
    }
}
if (-not [string]::IsNullOrWhiteSpace($McpbSettingsPath)) {
    $resolvedMcpbSettings = Resolve-Path -LiteralPath $McpbSettingsPath
    $mcpbSettings = Get-Content -LiteralPath $resolvedMcpbSettings -Raw | ConvertFrom-Json
    if ($mcpbSettings.isEnabled -eq $true -and $null -ne $mcpbSettings.userConfig) {
        $mcpbUserConfig = $mcpbSettings.userConfig
        Write-Host "PLwC MCPB settings: $resolvedMcpbSettings"
        $supportedMcpbSettings = @(
            "workspace_path",
            "profiles_path",
            "active_profile_name",
            "security_config",
            "memory_write_threshold",
            "persona_write_threshold",
            "temperament_write_threshold",
            "qdrant_enabled",
            "persona_layer_disabled"
        )
        $unsupportedMcpbSettings = @(
            $mcpbUserConfig.PSObject.Properties.Name |
                Where-Object { $_ -notin $supportedMcpbSettings }
        )
        if ($unsupportedMcpbSettings.Count -gt 0) {
            Write-Warning "Unsupported PLwC MCPB settings were found: $($unsupportedMcpbSettings -join ', ')"
        }
    }
}

if ($null -ne $mcpbUserConfig) {
    $env:PLWC_CHAT_BRIDGE_SETTINGS_SOURCE = "Claude PLwC configuration (launcher overrides take precedence)"
}
else {
    $env:PLWC_CHAT_BRIDGE_SETTINGS_SOURCE = "Bridge process / PLwC defaults"
}

if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $env:PLWC_WORKSPACE_ROOT = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
    Write-Host "Workspace root (explicit): $env:PLWC_WORKSPACE_ROOT"
}
elseif (-not [string]::IsNullOrWhiteSpace($env:PLWC_WORKSPACE_ROOT)) {
    $env:PLWC_WORKSPACE_ROOT = (Resolve-Path -LiteralPath $env:PLWC_WORKSPACE_ROOT).Path
    Write-Host "Workspace root (environment): $env:PLWC_WORKSPACE_ROOT"
}
elseif ($null -ne $mcpbUserConfig -and -not [string]::IsNullOrWhiteSpace([string] $mcpbUserConfig.workspace_path)) {
    $env:PLWC_WORKSPACE_ROOT = (Resolve-Path -LiteralPath ([string] $mcpbUserConfig.workspace_path)).Path
    Write-Host "Workspace root (PLwC MCPB settings): $env:PLWC_WORKSPACE_ROOT"
}
else {
    Write-Host "Workspace root: PLwC configured/default root"
}
if (-not [string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $env:PLWC_PROFILE_ROOT = (Resolve-Path -LiteralPath $ProfileRoot).Path
    Write-Host "Profile root (explicit): $env:PLWC_PROFILE_ROOT"
}
elseif (-not [string]::IsNullOrWhiteSpace($env:PLWC_PROFILE_ROOT)) {
    $env:PLWC_PROFILE_ROOT = (Resolve-Path -LiteralPath $env:PLWC_PROFILE_ROOT).Path
    Write-Host "Profile root (environment): $env:PLWC_PROFILE_ROOT"
}
elseif ($null -ne $mcpbUserConfig -and -not [string]::IsNullOrWhiteSpace([string] $mcpbUserConfig.profiles_path)) {
    $env:PLWC_PROFILE_ROOT = (Resolve-Path -LiteralPath ([string] $mcpbUserConfig.profiles_path)).Path
    Write-Host "Profile root (PLwC MCPB settings): $env:PLWC_PROFILE_ROOT"
}
else {
    Write-Host "Profile root: PLwC configured/default root"
}
if (-not [string]::IsNullOrWhiteSpace($ActiveProfileName)) {
    $env:PLWC_ACTIVE_PROFILE_NAME = $ActiveProfileName
    Write-Host "Active profile (explicit): $env:PLWC_ACTIVE_PROFILE_NAME"
}
elseif (-not [string]::IsNullOrWhiteSpace($env:PLWC_ACTIVE_PROFILE_NAME)) {
    Write-Host "Active profile (environment): $env:PLWC_ACTIVE_PROFILE_NAME"
}
elseif ($null -ne $mcpbUserConfig -and -not [string]::IsNullOrWhiteSpace([string] $mcpbUserConfig.active_profile_name)) {
    $env:PLWC_ACTIVE_PROFILE_NAME = [string] $mcpbUserConfig.active_profile_name
    Write-Host "Active profile (PLwC MCPB settings): $env:PLWC_ACTIVE_PROFILE_NAME"
}
else {
    Write-Host "Active profile: PLwC configured/default profile"
}
if (-not [string]::IsNullOrWhiteSpace($SecurityConfig)) {
    $env:PLWC_CONFIG_FILE = (Resolve-Path -LiteralPath $SecurityConfig).Path
    Write-Host "Security config (explicit): $env:PLWC_CONFIG_FILE"
}
elseif (-not [string]::IsNullOrWhiteSpace($env:PLWC_CONFIG_FILE)) {
    $env:PLWC_CONFIG_FILE = (Resolve-Path -LiteralPath $env:PLWC_CONFIG_FILE).Path
    Write-Host "Security config (environment): $env:PLWC_CONFIG_FILE"
}
elseif ($null -ne $mcpbUserConfig -and -not [string]::IsNullOrWhiteSpace([string] $mcpbUserConfig.security_config)) {
    $env:PLWC_CONFIG_FILE = (Resolve-Path -LiteralPath ([string] $mcpbUserConfig.security_config)).Path
    Write-Host "Security config (PLwC MCPB settings): $env:PLWC_CONFIG_FILE"
}
else {
    Write-Host "Security config: PLwC defaults"
}

$scalarMcpbMappings = @(
    @{
        Property = "memory_write_threshold"
        Environment = "PLWC_MEMORY_WRITE_THRESHOLD"
        Label = "Memory write threshold"
    },
    @{
        Property = "persona_write_threshold"
        Environment = "PLWC_PERSONA_WRITE_THRESHOLD"
        Label = "Persona write threshold"
    },
    @{
        Property = "temperament_write_threshold"
        Environment = "PLWC_TEMPERAMENT_WRITE_THRESHOLD"
        Label = "Temperament write threshold"
    },
    @{
        Property = "qdrant_enabled"
        Environment = "PLWC_QDRANT_ENABLED"
        Label = "Qdrant enabled"
    },
    @{
        Property = "persona_layer_disabled"
        Environment = "PLWC_PERSONA_LAYER_DISABLED"
        Label = "Persona layer disabled"
    }
)

foreach ($mapping in $scalarMcpbMappings) {
    $environmentValue = [Environment]::GetEnvironmentVariable($mapping.Environment, "Process")
    if (-not [string]::IsNullOrWhiteSpace($environmentValue)) {
        Write-Host "$($mapping.Label) (environment): $environmentValue"
        continue
    }

    $property = $null
    if ($null -ne $mcpbUserConfig) {
        $property = $mcpbUserConfig.PSObject.Properties[$mapping.Property]
    }
    if ($null -ne $property -and $null -ne $property.Value) {
        if ($property.Value -is [bool]) {
            $settingValue = $property.Value.ToString().ToLowerInvariant()
        }
        else {
            $settingValue = ([string] $property.Value).Trim()
        }
        if (-not [string]::IsNullOrWhiteSpace($settingValue)) {
            [Environment]::SetEnvironmentVariable($mapping.Environment, $settingValue, "Process")
            Write-Host "$($mapping.Label) (PLwC MCPB settings): $settingValue"
            continue
        }
    }

    Write-Host "$($mapping.Label): PLwC configured/default value"
}

function Resolve-PLwCDockerExecutable {
    $candidates = @(
        $env:PLWC_DOCKER_EXE,
        $(if ($env:ProgramFiles) {
            Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe"
        }),
        $(if (${env:ProgramW6432}) {
            Join-Path ${env:ProgramW6432} "Docker\Docker\resources\bin\docker.exe"
        }),
        $(if ($env:LOCALAPPDATA) {
            Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\resources\bin\docker.exe"
        }),
        $(if ($env:LOCALAPPDATA) {
            Join-Path $env:LOCALAPPDATA "Programs\Docker\Docker\resources\bin\docker.exe"
        }),
        $(Get-Command docker.exe -ErrorAction SilentlyContinue |
            Select-Object -First 1 -ExpandProperty Source)
    )
    foreach ($candidate in $candidates) {
        if (
            -not [string]::IsNullOrWhiteSpace($candidate) -and
            [System.IO.Path]::IsPathRooted($candidate) -and
            (Test-Path -LiteralPath $candidate -PathType Leaf)
        ) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

$resolvedDocker = Resolve-PLwCDockerExecutable
if (-not [string]::IsNullOrWhiteSpace($resolvedDocker)) {
    $env:PLWC_DOCKER_EXE = $resolvedDocker
    $dockerBin = Split-Path -Parent $resolvedDocker
    $pathParts = @($env:PATH -split ";" | Where-Object {
        -not [string]::IsNullOrWhiteSpace($_)
    })
    if ($dockerBin -notin $pathParts) {
        $env:PATH = "$dockerBin;$env:PATH"
    }
    Write-Host "Docker executable: $env:PLWC_DOCKER_EXE"
}
else {
    Remove-Item Env:PLWC_DOCKER_EXE -ErrorAction SilentlyContinue
    Write-Host "Docker executable: not detected; PLwC starts in Safe Mode"
}

if ($DryRun) {
    Write-Host "Bridge built: $(Test-Path -LiteralPath $bridgeEntry)"
    Write-Host "Dry run complete. No bridge or gateway process started."
    return
}

function Resolve-PLwCNodeExecutable {
    param([string] $ExplicitPath)

    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($candidate in @(
        $ExplicitPath,
        $env:PLWC_NODE_EXE,
        (Join-Path $env:ProgramFiles "nodejs\node.exe"),
        $(if (${env:ProgramFiles(x86)}) { Join-Path ${env:ProgramFiles(x86)} "nodejs\node.exe" }),
        $(if ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA "Programs\nodejs\node.exe" }),
        $(Get-Command node.exe -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty Source)
    )) {
        if (
            -not [string]::IsNullOrWhiteSpace($candidate) -and
            [System.IO.Path]::IsPathRooted($candidate) -and
            (Test-Path -LiteralPath $candidate) -and
            -not $candidates.Contains($candidate)
        ) {
            $candidates.Add((Resolve-Path -LiteralPath $candidate).Path)
        }
    }

    $launcherSettingsPath = Join-Path $env:APPDATA "PLwC\config\chat-bridge-launcher.json"
    if (Test-Path -LiteralPath $launcherSettingsPath) {
        try {
            $configuredNode = (Get-Content -LiteralPath $launcherSettingsPath -Raw | ConvertFrom-Json).nodePath
            if (
                -not [string]::IsNullOrWhiteSpace($configuredNode) -and
                [System.IO.Path]::IsPathRooted($configuredNode) -and
                (Test-Path -LiteralPath $configuredNode)
            ) {
                $candidates.Insert(0, (Resolve-Path -LiteralPath $configuredNode).Path)
            }
        }
        catch {
            Write-Warning "PLwC Chat Bridge launcher settings could not be read: $launcherSettingsPath"
        }
    }

    foreach ($candidate in $candidates) {
        $versionText = (& $candidate --version 2>$null)
        if ($LASTEXITCODE -eq 0 -and $versionText -match "^v(?<major>\d+)\.(?<minor>\d+)") {
            $major = [int] $Matches.major
            $minor = [int] $Matches.minor
            if ($major -gt 22 -or ($major -eq 22 -and $minor -ge 12)) {
                return $candidate
            }
        }
    }
    return $null
}

$resolvedNode = Resolve-PLwCNodeExecutable -ExplicitPath $NodePath
if ([string]::IsNullOrWhiteSpace($resolvedNode)) {
    throw "Node.js 22.12 or newer is required to run PLwC Chat Bridge."
}
if (-not (Test-Path -LiteralPath $bridgeEntry)) {
    throw "Bridge build not found. Run npm install and npm run build in integrations/plwc-chat-bridge first."
}

Write-Host "Node executable: $resolvedNode"

if ($Detached) {
    $launchScript = Join-Path $bridgeRoot "scripts\launch-bridge.mjs"
    $healthScript = Join-Path $bridgeRoot "scripts\healthcheck.mjs"
    if (-not (Test-Path -LiteralPath $launchScript -PathType Leaf)) {
        throw "Bridge launch script not found: $launchScript"
    }
    if (-not (Test-Path -LiteralPath $healthScript -PathType Leaf)) {
        throw "Bridge health-check script not found: $healthScript"
    }

    $plwcRoot = Join-Path $env:APPDATA "PLwC"
    $logRoot = Join-Path $plwcRoot "logs\chat-bridge"
    $stateRoot = Join-Path $plwcRoot "state\chat-bridge"
    $stdoutPath = Join-Path $logRoot "bridge.out.log"
    $stderrPath = Join-Path $logRoot "bridge.err.log"
    $pidPath = Join-Path $stateRoot "bridge.pid"
    New-Item -ItemType Directory -Force -Path $logRoot, $stateRoot | Out-Null

    function Test-PLwCBridgeHealth {
        & $resolvedNode `
            $healthScript `
            --endpoint $healthEndpoint `
            --origin $healthOrigin `
            --expected-build-id $expectedBuildId `
            --timeout-ms 3000
        return ($LASTEXITCODE -eq 0)
    }

    function Stop-PLwCOwnedBridgeProcess {
        if (-not (Test-Path -LiteralPath $pidPath -PathType Leaf)) {
            return
        }
        $ownedPid = 0
        if ([int]::TryParse((Get-Content -LiteralPath $pidPath -Raw).Trim(), [ref] $ownedPid)) {
            $ownedProcess = Get-CimInstance `
                Win32_Process `
                -Filter "ProcessId = $ownedPid" `
                -ErrorAction SilentlyContinue
            if (
                $null -ne $ownedProcess -and
                -not [string]::IsNullOrWhiteSpace([string] $ownedProcess.CommandLine) -and
                $ownedProcess.CommandLine.IndexOf(
                    $bridgeEntry,
                    [StringComparison]::OrdinalIgnoreCase
                ) -ge 0
            ) {
                Stop-Process -Id $ownedPid -Force -ErrorAction Stop
            }
        }
        Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
    }

    if (Test-PLwCBridgeHealth) {
        Write-Host "PLwC Chat Bridge is already ready with 8 of 8 tools."
        return
    }

    if (Test-Path -LiteralPath $pidPath -PathType Leaf) {
        Stop-PLwCOwnedBridgeProcess
    }

    & $resolvedNode `
        $launchScript `
        --entry $bridgeEntry `
        --config $resolvedConfig.Path `
        --stdout $stdoutPath `
        --stderr $stderrPath `
        --pid $pidPath
    if ($LASTEXITCODE -ne 0) {
        throw "PLwC Chat Bridge detached start failed with exit code $LASTEXITCODE."
    }

    $deadline = [DateTime]::UtcNow.AddSeconds(30)
    do {
        Start-Sleep -Milliseconds 500
        if (Test-PLwCBridgeHealth) {
            Write-Host "PLwC Chat Bridge is ready with 8 of 8 tools."
            return
        }
    } while ([DateTime]::UtcNow -lt $deadline)

    Stop-PLwCOwnedBridgeProcess
    throw "PLwC Chat Bridge started but did not reach the 8 of 8 ready state. Check $stderrPath"
}

& $resolvedNode $bridgeEntry --config $resolvedConfig
if ($LASTEXITCODE -ne 0) {
    throw "PLwC Chat Bridge exited with code $LASTEXITCODE."
}
