[CmdletBinding()]
param(
    [string] $ConfigPath,
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

Write-Host "PLwC Chat Bridge launcher scaffold"
Write-Host "Config: $resolvedConfig"
Write-Host "Loopback endpoint: ws://$($config.bridge.host):$($config.bridge.port)$($config.bridge.path)"
Write-Host "Gateway command: $($config.gateway.command) $($config.gateway.args -join ' ')"

if ($DryRun) {
    Write-Host "Dry run complete. No bridge process started."
    exit 0
}

throw "Bridge implementation is not pinned or vendored yet; refusing to start an unpinned proxy."
