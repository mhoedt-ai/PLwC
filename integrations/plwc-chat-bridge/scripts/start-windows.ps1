[CmdletBinding()]
param(
    [string] $ConfigPath,
    [string] $WorkspaceRoot,
    [string] $ProfileRoot,
    [string] $ActiveProfileName,
    [string] $SecurityConfig,
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

if (-not [string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    $env:PLWC_WORKSPACE_ROOT = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}
if (-not [string]::IsNullOrWhiteSpace($ProfileRoot)) {
    $env:PLWC_PROFILE_ROOT = (Resolve-Path -LiteralPath $ProfileRoot).Path
}
if (-not [string]::IsNullOrWhiteSpace($ActiveProfileName)) {
    $env:PLWC_ACTIVE_PROFILE_NAME = $ActiveProfileName
}
if (-not [string]::IsNullOrWhiteSpace($SecurityConfig)) {
    $env:PLWC_CONFIG_FILE = (Resolve-Path -LiteralPath $SecurityConfig).Path
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
