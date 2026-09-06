[CmdletBinding()]
param(
    [string] $ConfigPath,
    [string] $NodePath,

    [ValidateSet("de", "en")]
    [string] $Language = "de",

    [switch] $StartNow,
    [switch] $Remove,
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"

if (-not $IsWindows -and $null -ne $IsWindows) {
    throw "PLwC Chat Bridge autostart is only supported on Windows."
}

$integrationRoot = Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")
$startScript = Join-Path $PSScriptRoot "start-windows.ps1"
$bridgeEntry = Join-Path $integrationRoot "bridge\dist\src\index.js"
$taskName = "PLwC Chat Bridge"
$plwcRoot = Join-Path $env:APPDATA "PLwC"
$logRoot = Join-Path $plwcRoot "logs\chat-bridge"
$stateRoot = Join-Path $plwcRoot "state\chat-bridge"
$settingsPath = Join-Path $plwcRoot "config\chat-bridge-launcher.json"
$integrationLog = Join-Path $logRoot "windows-integration.log"
$pidPath = Join-Path $stateRoot "bridge.pid"
$powerShellPath = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe"
$previousStartScript = $null
$previousBridgeEntry = $null

if (Test-Path -LiteralPath $settingsPath -PathType Leaf) {
    try {
        $previousSettings = Get-Content -LiteralPath $settingsPath -Raw | ConvertFrom-Json
        if (-not [string]::IsNullOrWhiteSpace([string] $previousSettings.integrationRoot)) {
            $previousStartScript = Join-Path `
                ([string] $previousSettings.integrationRoot) `
                "scripts\start-windows.ps1"
            $previousBridgeEntry = Join-Path `
                ([string] $previousSettings.integrationRoot) `
                "bridge\dist\src\index.js"
        }
    }
    catch {
        $previousStartScript = $null
    }
}

function Quote-PLwCArgument {
    param([Parameter(Mandatory = $true)][string] $Value)
    return '"' + $Value.Replace('"', '\"') + '"'
}

function Write-PLwCIntegrationLog {
    param([Parameter(Mandatory = $true)][string] $Message)
    if ($DryRun) {
        return
    }
    New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
    Add-Content -LiteralPath $integrationLog -Encoding UTF8 -Value (
        "{0} {1}" -f [DateTime]::UtcNow.ToString("o"), $Message
    )
}

function Test-PLwCOwnedScheduledTask {
    param($Task)

    if ($null -eq $Task -or $null -eq $Task.Actions) {
        return $false
    }
    $taskArguments = (@($Task.Actions) | ForEach-Object { [string] $_.Arguments }) -join " "
    foreach ($ownedScript in @($startScript, $previousStartScript)) {
        if (
            -not [string]::IsNullOrWhiteSpace($ownedScript) -and
            $taskArguments.IndexOf(
                $ownedScript,
                [StringComparison]::OrdinalIgnoreCase
            ) -ge 0
        ) {
            return $true
        }
    }
    return $false
}

function Get-PLwCOwnedBridgeProcesses {
    $ownedEntries = @(
        @($bridgeEntry, $previousBridgeEntry) |
            Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
            Select-Object -Unique
    )
    if ($ownedEntries.Count -eq 0) {
        return @()
    }

    return @(
        Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $commandLine = [string] $_.CommandLine
                if ([string]::IsNullOrWhiteSpace($commandLine)) {
                    return $false
                }
                foreach ($ownedEntry in $ownedEntries) {
                    if ($commandLine.IndexOf(
                        $ownedEntry,
                        [StringComparison]::OrdinalIgnoreCase
                    ) -ge 0) {
                        return $true
                    }
                }
                return $false
            }
    )
}

function Stop-OwnedBridgeProcess {
    foreach ($process in @(Get-PLwCOwnedBridgeProcesses)) {
        $ownedPid = [int] $process.ProcessId
        Stop-Process -Id $ownedPid -Force -ErrorAction Stop
        Write-PLwCIntegrationLog "Stopped owned bridge process $ownedPid."
    }
    Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}

if (-not $Remove) {
    if (-not (Test-Path -LiteralPath $startScript -PathType Leaf)) {
        throw "PLwC Chat Bridge start script was not found: $startScript"
    }
    if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
        $ConfigPath = (Resolve-Path -LiteralPath $ConfigPath).Path
    }
    if (-not [string]::IsNullOrWhiteSpace($NodePath)) {
        $NodePath = (Resolve-Path -LiteralPath $NodePath).Path
    }
}

$startArguments = @(
    "-NoLogo",
    "-NoProfile",
    "-NonInteractive",
    "-WindowStyle", "Hidden",
    "-ExecutionPolicy", "Bypass",
    "-File", (Quote-PLwCArgument $startScript),
    "-Detached"
)
if (-not [string]::IsNullOrWhiteSpace($ConfigPath)) {
    $startArguments += @("-ConfigPath", (Quote-PLwCArgument $ConfigPath))
}
if (-not [string]::IsNullOrWhiteSpace($NodePath)) {
    $startArguments += @("-NodePath", (Quote-PLwCArgument $NodePath))
}
$scheduledArguments = $startArguments -join " "

if ($Remove) {
    if ($DryRun) {
        Write-Output "Would remove scheduled task '$taskName' when owned by $startScript"
        exit 0
    }

    Stop-OwnedBridgeProcess
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (Test-PLwCOwnedScheduledTask -Task $existingTask) {
        Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-PLwCIntegrationLog "Removed per-user bridge scheduled task."
    }
    Remove-Item -LiteralPath $settingsPath -Force -ErrorAction SilentlyContinue
    exit 0
}

if ($DryRun) {
    Write-Output "Would register scheduled task '$taskName' for the current user."
    Write-Output "$powerShellPath $scheduledArguments"
    exit 0
}

$existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($null -ne $existingTask -and -not (Test-PLwCOwnedScheduledTask -Task $existingTask)) {
    throw "A scheduled task named '$taskName' exists but is not owned by PLwC."
}

$previousTaskXml = if ($null -ne $existingTask) {
    Export-ScheduledTask -TaskName $taskName
}
else {
    $null
}
$previousSettingsBytes = if (Test-Path -LiteralPath $settingsPath -PathType Leaf) {
    [IO.File]::ReadAllBytes($settingsPath)
}
else {
    $null
}

$settings = [ordered]@{
    nodePath = $NodePath
    configPath = $ConfigPath
    integrationRoot = $integrationRoot.Path
}

$currentUser = [Security.Principal.WindowsIdentity]::GetCurrent().Name
$taskAction = New-ScheduledTaskAction `
    -Execute $powerShellPath `
    -Argument $scheduledArguments
$taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $currentUser
$taskTrigger.Delay = "PT20S"
$taskPrincipal = New-ScheduledTaskPrincipal `
    -UserId $currentUser `
    -LogonType Interactive `
    -RunLevel Limited
$taskSettings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -StartWhenAvailable
$taskDescription = if ($Language -eq "de") {
    "Startet und prüft die lokale PLwC Chat Bridge nach der Windows-Anmeldung."
}
else {
    "Starts and verifies the local PLwC Chat Bridge after Windows sign-in."
}

try {
    Register-ScheduledTask `
        -TaskName $taskName `
        -Action $taskAction `
        -Trigger $taskTrigger `
        -Principal $taskPrincipal `
        -Settings $taskSettings `
        -Description $taskDescription `
        -Force | Out-Null

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $settingsPath) | Out-Null
    [IO.File]::WriteAllText(
        $settingsPath,
        ($settings | ConvertTo-Json),
        [Text.UTF8Encoding]::new($false)
    )
    Write-PLwCIntegrationLog (
        "Registered per-user bridge scheduled task for ${currentUser}: " +
        "$powerShellPath $scheduledArguments"
    )

    if ($StartNow) {
        Stop-OwnedBridgeProcess
        & $startScript -ConfigPath $ConfigPath -NodePath $NodePath -Detached
        Write-PLwCIntegrationLog "Bridge started and verified during setup."
    }
}
catch {
    $failure = $_
    Stop-OwnedBridgeProcess
    if ($null -ne $previousTaskXml) {
        Register-ScheduledTask `
            -TaskName $taskName `
            -Xml $previousTaskXml `
            -Force `
            -ErrorAction SilentlyContinue | Out-Null
    }
    else {
        Unregister-ScheduledTask `
            -TaskName $taskName `
            -Confirm:$false `
            -ErrorAction SilentlyContinue
    }
    if ($null -ne $previousSettingsBytes) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $settingsPath) | Out-Null
        [IO.File]::WriteAllBytes($settingsPath, $previousSettingsBytes)
    }
    else {
        Remove-Item -LiteralPath $settingsPath -Force -ErrorAction SilentlyContinue
    }
    if ($null -ne $previousTaskXml) {
        Start-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    }
    Write-PLwCIntegrationLog "Bridge integration failed; previous task and settings were restored: $($failure.Exception.Message)"
    throw $failure
}
