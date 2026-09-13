[CmdletBinding()]
param(
    [string]$OutputDirectory = $PSScriptRoot
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version 2.0

$script:ProbeErrors = New-Object System.Collections.Generic.List[object]
$script:DiscoveredRoots = New-Object System.Collections.Generic.List[string]

function Add-ProbeError {
    param([string]$Probe, [System.Exception]$Exception)
    $script:ProbeErrors.Add([pscustomobject]@{
        probe = $Probe
        type = $Exception.GetType().FullName
        message = ConvertTo-SafeText $Exception.Message
    })
}

function ConvertTo-SafeText {
    param([AllowNull()][object]$Value)
    if ($null -eq $Value) { return $null }
    $text = [string]$Value
    $text = [regex]::Replace(
        $text,
        '(?i)(authorization|password|passwd|secret|session[_-]?token|access[_-]?token|api[_-]?key)(\s*[:=]\s*)([^\s,;]+)',
        '$1$2[REDACTED]'
    )
    $text = [regex]::Replace($text, '(?i)Bearer\s+[A-Za-z0-9._~+/=-]+', 'Bearer [REDACTED]')
    return $text
}

function Get-PropertyValue {
    param([AllowNull()][object]$InputObject, [string]$Name)
    if ($null -eq $InputObject) { return $null }
    if ($InputObject.PSObject.Properties.Name -contains $Name) {
        return $InputObject.$Name
    }
    return $null
}

function Add-DiscoveredRoot {
    param([AllowNull()][string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return }
    try {
        $candidate = [Environment]::ExpandEnvironmentVariables($Path.Trim('"'))
        if (-not [System.IO.Path]::IsPathRooted($candidate)) { return }
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $candidate = Split-Path -Parent $candidate
        }
        $resolved = [System.IO.Path]::GetFullPath($candidate)
        if (-not $script:DiscoveredRoots.Contains($resolved)) {
            $script:DiscoveredRoots.Add($resolved)
        }
    } catch {
        Add-ProbeError "discovered_root:$Path" $_.Exception
    }
}

function Get-FileFact {
    param([string]$Path, [switch]$Hash)
    $fact = [ordered]@{ path = $Path; exists = $false; kind = "missing" }
    try {
        if (Test-Path -LiteralPath $Path -PathType Container) {
            $fact.exists = $true
            $fact.kind = "directory"
        } elseif (Test-Path -LiteralPath $Path -PathType Leaf) {
            $item = Get-Item -LiteralPath $Path -Force
            $fact.exists = $true
            $fact.kind = "file"
            $fact.size = $item.Length
            $fact.last_write_utc = $item.LastWriteTimeUtc.ToString("o")
            if ($Hash -and $item.Length -le 52428800) {
                $fact.sha256 = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
            }
        }
    } catch {
        $fact.error = ConvertTo-SafeText $_.Exception.Message
    }
    return [pscustomobject]$fact
}

function Get-RegistryValueFact {
    param([string]$Path, [string]$Name = "")
    try {
        if (-not (Test-Path -LiteralPath $Path)) {
            return [pscustomobject]@{ path = $Path; name = $Name; exists = $false; value = $null }
        }
        $item = Get-ItemProperty -LiteralPath $Path
        $value = if ($Name) { $item.$Name } else { $item.'(default)' }
        if ($null -eq $value -and -not $Name) {
            $key = Get-Item -LiteralPath $Path
            $value = $key.GetValue("")
        }
        return [pscustomobject]@{
            path = $Path
            name = $Name
            exists = $true
            value = ConvertTo-SafeText $value
        }
    } catch {
        Add-ProbeError "registry:$Path" $_.Exception
        return [pscustomobject]@{ path = $Path; name = $Name; exists = $true; value = $null; error = ConvertTo-SafeText $_.Exception.Message }
    }
}

function Get-ShortcutFacts {
    $facts = New-Object System.Collections.Generic.List[object]
    $directories = @(
        [Environment]::GetFolderPath("Startup"),
        [Environment]::GetFolderPath("CommonStartup"),
        [Environment]::GetFolderPath("Desktop"),
        [Environment]::GetFolderPath("CommonDesktopDirectory"),
        [Environment]::GetFolderPath("StartMenu"),
        [Environment]::GetFolderPath("CommonStartMenu")
    ) | Where-Object { $_ }
    try {
        $shell = New-Object -ComObject WScript.Shell
        foreach ($directory in ($directories | Select-Object -Unique)) {
            if (-not (Test-Path -LiteralPath $directory)) { continue }
            foreach ($file in (Get-ChildItem -LiteralPath $directory -Filter *.lnk -File -Recurse -ErrorAction SilentlyContinue)) {
                try {
                    $shortcut = $shell.CreateShortcut($file.FullName)
                    $combined = "$($file.Name) $($shortcut.TargetPath) $($shortcut.Arguments)"
                    if ($combined -notmatch '(?i)plwc|chat.?bridge|installer.?maintenance') { continue }
                    Add-DiscoveredRoot $shortcut.TargetPath
                    $facts.Add([pscustomobject]@{
                        path = $file.FullName
                        target = ConvertTo-SafeText $shortcut.TargetPath
                        arguments = ConvertTo-SafeText $shortcut.Arguments
                        working_directory = ConvertTo-SafeText $shortcut.WorkingDirectory
                        icon = ConvertTo-SafeText $shortcut.IconLocation
                    })
                } catch {
                    Add-ProbeError "shortcut:$($file.FullName)" $_.Exception
                }
            }
        }
    } catch {
        Add-ProbeError "shortcuts" $_.Exception
    }
    return $facts.ToArray()
}

function Get-ClaudeMcpFacts {
    $facts = New-Object System.Collections.Generic.List[object]
    $paths = @(
        (Join-Path $env:APPDATA "Claude\claude_desktop_config.json"),
        (Join-Path $env:APPDATA "Claude\config.json"),
        (Join-Path $env:LOCALAPPDATA "Claude\claude_desktop_config.json")
    ) | Select-Object -Unique
    foreach ($path in $paths) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            $facts.Add([pscustomobject]@{ path = $path; exists = $false })
            continue
        }
        try {
            $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
            $config = $raw | ConvertFrom-Json
            $servers = New-Object System.Collections.Generic.List[object]
            if ($config.PSObject.Properties.Name -contains "mcpServers" -and $null -ne $config.mcpServers) {
                foreach ($property in $config.mcpServers.PSObject.Properties) {
                    $server = $property.Value
                    if ($null -eq $server) { continue }
                    $args = @()
                    if ($server.PSObject.Properties.Name -contains "args") {
                        $args = @($server.args | ForEach-Object { ConvertTo-SafeText $_ })
                    }
                    $command = if ($server.PSObject.Properties.Name -contains "command") { ConvertTo-SafeText $server.command } else { $null }
                    $serverIdentity = "$($property.Name) $command $($args -join ' ')"
                    if ($serverIdentity -match '(?i)plwc|plwc_gateway|chat.?bridge') {
                        Add-DiscoveredRoot $command
                        foreach ($argument in $args) { Add-DiscoveredRoot $argument }
                    }
                    $envNames = @()
                    if ($server.PSObject.Properties.Name -contains "env" -and $null -ne $server.env) {
                        $envNames = @($server.env.PSObject.Properties.Name | Sort-Object)
                    }
                    $servers.Add([pscustomobject]@{
                        name = $property.Name
                        command = $command
                        arguments = $args
                        environment_variable_names = $envNames
                    })
                }
            }
            $facts.Add([pscustomobject]@{
                path = $path
                exists = $true
                sha256 = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
                mcp_servers = $servers.ToArray()
            })
        } catch {
            Add-ProbeError "claude_config:$path" $_.Exception
            $facts.Add([pscustomobject]@{ path = $path; exists = $true; parse_error = ConvertTo-SafeText $_.Exception.Message })
        }
    }
    return $facts.ToArray()
}

function Get-ProcessFacts {
    $facts = New-Object System.Collections.Generic.List[object]
    try {
        $rows = @(Get-CimInstance Win32_Process -ErrorAction Stop)
        foreach ($row in $rows) {
            $combined = "$($row.Name) $($row.ExecutablePath) $($row.CommandLine)"
            if ($combined -notmatch '(?i)plwc|plwc_gateway|chat.?bridge|installer.?maintenance') { continue }
            Add-DiscoveredRoot $row.ExecutablePath
            $facts.Add([pscustomobject]@{
                pid = [int]$row.ProcessId
                name = $row.Name
                executable = ConvertTo-SafeText $row.ExecutablePath
                command_line = ConvertTo-SafeText $row.CommandLine
                source = "Win32_Process"
            })
        }
    } catch {
        Add-ProbeError "processes.win32_process" $_.Exception
    }
    if ($facts.Count -eq 0) {
        try {
            foreach ($row in (Get-Process -ErrorAction Stop)) {
                if ($row.ProcessName -notmatch '(?i)plwc') { continue }
                $path = $null
                try { $path = $row.Path } catch { }
                Add-DiscoveredRoot $path
                $facts.Add([pscustomobject]@{
                    pid = $row.Id
                    name = $row.ProcessName
                    executable = ConvertTo-SafeText $path
                    command_line = $null
                    source = "Get-Process fallback"
                })
            }
        } catch {
            Add-ProbeError "processes.get_process" $_.Exception
        }
    }
    return $facts.ToArray()
}

function Get-PortFacts {
    $facts = New-Object System.Collections.Generic.List[object]
    try {
        foreach ($connection in @(Get-NetTCPConnection -LocalPort 3007 -ErrorAction Stop)) {
            $process = $null
            $cim = $null
            try { $process = Get-Process -Id $connection.OwningProcess -ErrorAction Stop } catch { }
            try { $cim = Get-CimInstance Win32_Process -Filter "ProcessId=$($connection.OwningProcess)" -ErrorAction Stop } catch { }
            if ($null -ne $cim) { Add-DiscoveredRoot $cim.ExecutablePath }
            $facts.Add([pscustomobject]@{
                local_address = $connection.LocalAddress
                local_port = $connection.LocalPort
                state = [string]$connection.State
                owning_pid = $connection.OwningProcess
                process_name = if ($null -ne $process) { $process.ProcessName } else { $null }
                executable = if ($null -ne $cim) { ConvertTo-SafeText $cim.ExecutablePath } else { $null }
                command_line = if ($null -ne $cim) { ConvertTo-SafeText $cim.CommandLine } else { $null }
            })
        }
    } catch {
        Add-ProbeError "port_3007" $_.Exception
    }
    return $facts.ToArray()
}

function Invoke-ReadOnlyCommand {
    param([string]$FilePath, [string[]]$Arguments)
    try {
        $output = @(& $FilePath @Arguments 2>&1 | ForEach-Object { ConvertTo-SafeText $_ })
        return [pscustomobject]@{ available = $true; exit_code = $LASTEXITCODE; output = $output }
    } catch {
        return [pscustomobject]@{ available = $false; exit_code = $null; error = ConvertTo-SafeText $_.Exception.Message; output = @() }
    }
}

function Get-DockerFacts {
    $version = Invoke-ReadOnlyCommand "docker.exe" @("version", "--format", "{{json .}}")
    $imagesRaw = Invoke-ReadOnlyCommand "docker.exe" @("image", "ls", "--digests", "--no-trunc", "--format", "{{json .}}")
    $containersRaw = Invoke-ReadOnlyCommand "docker.exe" @("ps", "-a", "--no-trunc", "--format", "{{json .}}")
    $images = @($imagesRaw.output | Where-Object { $_ -match '(?i)plwc|qdrant' })
    $containers = @($containersRaw.output | Where-Object { $_ -match '(?i)plwc|qdrant' })
    return [pscustomobject]@{
        version = $version
        relevant_images = $images
        relevant_containers = $containers
        image_query_exit_code = $imagesRaw.exit_code
        container_query_exit_code = $containersRaw.exit_code
    }
}

function Get-RelevantFileInventory {
    param([string[]]$Roots)
    $facts = New-Object System.Collections.Generic.List[object]
    $extensions = @('.exe', '.cmd', '.bat', '.ps1', '.py', '.js', '.json', '.ini', '.yaml', '.yml', '.toml')
    foreach ($root in ($Roots | Select-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        try {
            $count = 0
            foreach ($file in (Get-ChildItem -LiteralPath $root -File -Recurse -Force -ErrorAction SilentlyContinue)) {
                if ($file.FullName -match '(?i)\\(?:node_modules|\.venv|venv|profiles|workspace|Tagebuch|Temp|Trashcan)\\') { continue }
                if ($extensions -notcontains $file.Extension.ToLowerInvariant()) { continue }
                $facts.Add((Get-FileFact -Path $file.FullName -Hash))
                $count++
                if ($count -ge 2500) {
                    $facts.Add([pscustomobject]@{ path = $root; truncated = $true; limit = 2500 })
                    break
                }
            }
        } catch {
            Add-ProbeError "file_inventory:$root" $_.Exception
        }
    }
    return $facts.ToArray()
}

function Get-ToolCountLogMatches {
    $matches = New-Object System.Collections.Generic.List[object]
    $roots = @(
        (Join-Path $env:APPDATA "PLwC\logs"),
        (Join-Path $env:LOCALAPPDATA "PLwC\logs")
    ) | Select-Object -Unique
    foreach ($root in $roots) {
        if (-not (Test-Path -LiteralPath $root -PathType Container)) { continue }
        $files = @(Get-ChildItem -LiteralPath $root -File -Recurse -ErrorAction SilentlyContinue |
            Where-Object { $_.Length -le 5242880 } |
            Sort-Object LastWriteTimeUtc -Descending |
            Select-Object -First 150)
        foreach ($file in $files) {
            try {
                foreach ($match in @(Select-String -LiteralPath $file.FullName -Pattern '19\s*/\s*19|19\s+tools|tool_count.{0,20}19|Werkzeuge.{0,20}19|tools.{0,20}19' -AllMatches -ErrorAction Stop)) {
                    $matches.Add([pscustomobject]@{
                        path = $file.FullName
                        line_number = $match.LineNumber
                        line = ConvertTo-SafeText $match.Line.Trim()
                    })
                    if ($matches.Count -ge 200) { return $matches.ToArray() }
                }
            } catch {
                Add-ProbeError "log_scan:$($file.FullName)" $_.Exception
            }
        }
    }
    return $matches.ToArray()
}

if (-not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
    New-Item -ItemType Directory -Path $OutputDirectory | Out-Null
}
$OutputDirectory = (Resolve-Path -LiteralPath $OutputDirectory).Path

$knownRoots = @(
    (Join-Path $env:APPDATA "PLwC"),
    (Join-Path $env:LOCALAPPDATA "PLwC"),
    (Join-Path $env:LOCALAPPDATA "Programs\PLwC"),
    (Join-Path $env:ProgramFiles "PLwC")
)
if (${env:ProgramFiles(x86)}) { $knownRoots += (Join-Path ${env:ProgramFiles(x86)} "PLwC") }
foreach ($root in $knownRoots) { Add-DiscoveredRoot $root }

$uninstallFacts = New-Object System.Collections.Generic.List[object]
foreach ($base in @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
)) {
    try {
        foreach ($key in (Get-ChildItem -LiteralPath $base -ErrorAction SilentlyContinue)) {
            $item = Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction SilentlyContinue
            $displayName = Get-PropertyValue $item "DisplayName"
            $displayVersion = Get-PropertyValue $item "DisplayVersion"
            $installLocation = Get-PropertyValue $item "InstallLocation"
            $uninstallString = Get-PropertyValue $item "UninstallString"
            $publisher = Get-PropertyValue $item "Publisher"
            if ("$displayName $installLocation $uninstallString" -notmatch '(?i)plwc') { continue }
            Add-DiscoveredRoot $installLocation
            $uninstallFacts.Add([pscustomobject]@{
                registry_path = $key.Name
                display_name = $displayName
                display_version = $displayVersion
                install_location = ConvertTo-SafeText $installLocation
                uninstall_string = ConvertTo-SafeText $uninstallString
                publisher = $publisher
            })
        }
    } catch {
        Add-ProbeError "uninstall_registry:$base" $_.Exception
    }
}

$claude = Get-ClaudeMcpFacts
$shortcuts = Get-ShortcutFacts
$processes = Get-ProcessFacts
$port3007 = Get-PortFacts

$nativeMessaging = @()
foreach ($browserPath in @(
    "HKCU:\Software\Google\Chrome\NativeMessagingHosts\plwc.chat_bridge.launcher",
    "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\plwc.chat_bridge.launcher",
    "HKCU:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\plwc.chat_bridge.launcher",
    "HKLM:\Software\Google\Chrome\NativeMessagingHosts\plwc.chat_bridge.launcher",
    "HKLM:\Software\Microsoft\Edge\NativeMessagingHosts\plwc.chat_bridge.launcher",
    "HKLM:\Software\BraveSoftware\Brave-Browser\NativeMessagingHosts\plwc.chat_bridge.launcher"
)) {
    $fact = Get-RegistryValueFact -Path $browserPath
    $nativeMessaging += $fact
    if ($fact.exists -and $fact.value) { Add-DiscoveredRoot $fact.value }
}

$runKeys = @()
foreach ($path in @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
)) {
    try {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $item = Get-ItemProperty -LiteralPath $path
        foreach ($property in $item.PSObject.Properties) {
            if ($property.Name -match '^PS' -or "$($property.Name) $($property.Value)" -notmatch '(?i)plwc|chat.?bridge') { continue }
            $runKeys += [pscustomobject]@{ path = $path; name = $property.Name; value = ConvertTo-SafeText $property.Value }
        }
    } catch {
        Add-ProbeError "run_key:$path" $_.Exception
    }
}

$scheduledTasks = @()
try {
    foreach ($task in @(Get-ScheduledTask -ErrorAction Stop)) {
        $actionText = @($task.Actions | ForEach-Object {
            $execute = Get-PropertyValue $_ "Execute"
            $arguments = Get-PropertyValue $_ "Arguments"
            "$execute $arguments"
        }) -join " | "
        if ("$($task.TaskName) $($task.TaskPath) $actionText" -notmatch '(?i)plwc|chat.?bridge') { continue }
        $scheduledTasks += [pscustomobject]@{
            task_name = $task.TaskName
            task_path = $task.TaskPath
            state = [string]$task.State
            actions = ConvertTo-SafeText $actionText
        }
    }
} catch {
    Add-ProbeError "scheduled_tasks" $_.Exception
}

$roots = @($script:DiscoveredRoots | Where-Object { Test-Path -LiteralPath $_ -PathType Container } | Select-Object -Unique)
$report = [ordered]@{
    schema_version = "1.0.0"
    purpose = "Read-only r27 legacy and mixed-installation inventory"
    generated_utc = [DateTime]::UtcNow.ToString("o")
    computer = $env:COMPUTERNAME
    user_domain = $env:USERDOMAIN
    user_name = $env:USERNAME
    powershell = $PSVersionTable.PSVersion.ToString()
    os = [Environment]::OSVersion.VersionString
    known_and_discovered_roots = $roots
    uninstall_entries = $uninstallFacts.ToArray()
    claude_mcp = $claude
    processes = $processes
    port_3007 = $port3007
    shortcuts = $shortcuts
    run_keys = $runKeys
    scheduled_tasks = $scheduledTasks
    native_messaging = $nativeMessaging
    docker = Get-DockerFacts
    tool_count_log_matches = Get-ToolCountLogMatches
    relevant_file_inventory = Get-RelevantFileInventory -Roots $roots
    probe_errors = $script:ProbeErrors.ToArray()
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$diagnosticTempRoot = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$work = [System.IO.Path]::GetFullPath((Join-Path $diagnosticTempRoot "PLwC-r27-legacy-diagnostic-$stamp-$PID"))
if (-not $work.StartsWith($diagnosticTempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "The diagnostic temporary path is outside the Windows temporary directory."
}
$zip = Join-Path $OutputDirectory "PLwC-r27-legacy-diagnostic-$env:COMPUTERNAME-$stamp.zip"
New-Item -ItemType Directory -Path $work | Out-Null
try {
    $reportPath = Join-Path $work "report.json"
    $readmePath = Join-Path $work "README.txt"
    $report | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $reportPath -Encoding UTF8
    @(
        "PLwC r27 legacy/mixed-installation diagnostic"
        ""
        "This collector is read-only except for its own temporary directory and this ZIP file."
        "Configuration files are not copied. Secret-like values are redacted; Claude environment values are omitted."
        "The report may contain local user names and filesystem paths needed for migration diagnosis."
    ) | Set-Content -LiteralPath $readmePath -Encoding UTF8
    Compress-Archive -LiteralPath $reportPath,$readmePath -DestinationPath $zip -CompressionLevel Optimal
} finally {
    if (
        $work.StartsWith($diagnosticTempRoot, [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $work -PathType Container)
    ) {
        Remove-Item -LiteralPath $work -Recurse -Force
    }
}

$zipHash = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash
Write-Host "Diagnose abgeschlossen (nur lesende Bestandsaufnahme)." -ForegroundColor Green
Write-Host "ZIP: $zip"
Write-Host "SHA256: $zipHash"
