[CmdletBinding()]
param(
    [string] $ConfigPath,
    [string] $WorkspaceRoot,
    [string] $ProfileRoot,
    [string] $ActiveProfileName,
    [string] $SecurityConfig,
    [string] $McpbSettingsPath,
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
Write-Host "Loopback endpoint: ws://$($config.bridge.host):$($config.bridge.port)$($config.bridge.path)"
Write-Host "Gateway command: $($config.gateway.command) $($config.gateway.args -join ' ')"

$bridgeRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\bridge")
$bridgeEntry = Join-Path $bridgeRoot "dist\src\index.js"
Write-Host "Bridge entry: $bridgeEntry"

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

if ($DryRun) {
    Write-Host "Bridge built: $(Test-Path -LiteralPath $bridgeEntry)"
    Write-Host "Dry run complete. No bridge or gateway process started."
    exit 0
}

if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    throw "Node.js 22.12 or newer is required to run PLwC Chat Bridge."
}
if (-not (Test-Path -LiteralPath $bridgeEntry)) {
    throw "Bridge build not found. Run npm install and npm run build in integrations/plwc-chat-bridge first."
}

& node $bridgeEntry --config $resolvedConfig
exit $LASTEXITCODE
