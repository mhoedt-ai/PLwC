[CmdletBinding()]
param(
    [string] $SetupPath = (
        Join-Path $PSScriptRoot (
            "..\.unsigned-build-r24\dist\PLwC-Setup-1.0.0-installer-r24.exe"
        )
    ),

    [ValidateSet("german", "english")]
    [string] $Language = "german",

    [ValidateRange(1, 20)]
    [int] $MaximumNextClicks = 8,

    [switch] $FixtureGuardsInstallation,

    [switch] $ExercisePrerequisiteSelection,

    [switch] $ExerciseDownload,

    [ValidateSet("gateway", "chatbridge")]
    [string] $ComponentPlan = "gateway",

    [switch] $ExerciseWorkspaceStructure,

    [switch] $ExpectSetupP002Diagnostics,

    [switch] $ExpectSetupP003BuildIdentity,

    [switch] $ExpectSetupP101SizeBreakdown,

    [switch] $ExpectSetupP002Fix01Flow
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

function Find-InnoSetupCompiler {
    $command = Get-Command ISCC.exe -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($null -ne $command) {
        return $command.Source
    }
    foreach ($candidate in @(
        (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
        (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
    )) {
        if (-not [string]::IsNullOrWhiteSpace($candidate) -and
            (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw "Inno Setup 6 compiler (ISCC.exe) was not found."
}

function Get-WorkspaceSnapshot {
    param([Parameter(Mandatory = $true)][string] $Path)

    $root = [IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $entries = @(
        Get-ChildItem -LiteralPath $root -Recurse -Force |
            Sort-Object FullName |
            ForEach-Object {
                $relativePath = $_.FullName.Substring($root.Length).
                    TrimStart('\', '/').Replace('\', '/')
                [ordered]@{
                    path = $relativePath
                    type = $(if ($_.PSIsContainer) { "directory" } else { "file" })
                    length = $(if ($_.PSIsContainer) { 0L } else { [long] $_.Length })
                    sha256 = $(if ($_.PSIsContainer) {
                        $null
                    }
                    else {
                        (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).
                            Hash.ToLowerInvariant()
                    })
                    lastWriteTimeUtc = $_.LastWriteTimeUtc.ToString("o")
                }
            }
    )
    return ($entries | ConvertTo-Json -Depth 4 -Compress)
}

function Invoke-WorkspaceFixtureSetup {
    param(
        [Parameter(Mandatory = $true)][string] $SetupPath,
        [Parameter(Mandatory = $true)][string] $WorkspacePath
    )

    $process = Start-Process `
        -FilePath $SetupPath `
        -ArgumentList @(
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/WORKSPACEROOT=$WorkspacePath"
        ) `
        -WindowStyle Hidden `
        -Wait `
        -PassThru
    if ($process.ExitCode -ne 0) {
        throw "Workspace fixture Setup failed with exit code $($process.ExitCode)."
    }
}

function Invoke-WorkspaceStructureSmoke {
    $systemTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $systemTemp = $systemTemp.TrimEnd('\', '/') +
        [IO.Path]::DirectorySeparatorChar
    $fixtureRoot = [IO.Path]::GetFullPath(
        (Join-Path $systemTemp ("plwc-workspace-smoke-" + [guid]::NewGuid().ToString("N")))
    )
    if (-not $fixtureRoot.StartsWith(
        $systemTemp,
        [StringComparison]::OrdinalIgnoreCase
    )) {
        throw "Unsafe workspace fixture root: $fixtureRoot"
    }

    $buildRoot = Join-Path $fixtureRoot "build"
    $workspaceRoot = Join-Path $fixtureRoot "workspace"
    $fixtureSource = Join-Path $PSScriptRoot "workspace-structure-fixture.iss"
    $setupFixture = Join-Path $buildRoot "plwc-workspace-structure-fixture.exe"
    $protectedTimestamp = [DateTime]::SpecifyKind(
        [DateTime]::ParseExact(
            "2020-01-02 03:04:05",
            "yyyy-MM-dd HH:mm:ss",
            [Globalization.CultureInfo]::InvariantCulture
        ),
        [DateTimeKind]::Utc
    )

    try {
        [IO.Directory]::CreateDirectory($buildRoot) | Out-Null
        $compiler = Find-InnoSetupCompiler
        & $compiler /Qp "/DOutputDir=$buildRoot" $fixtureSource
        if ($LASTEXITCODE -ne 0 -or
            -not (Test-Path -LiteralPath $setupFixture -PathType Leaf)) {
            throw "Workspace fixture Setup compilation failed."
        }

        Invoke-WorkspaceFixtureSetup `
            -SetupPath $setupFixture `
            -WorkspacePath $workspaceRoot

        $standardNames = @("Tagebuch", "Temp", "Trashcan")
        $cleanChildren = @(
            Get-ChildItem -LiteralPath $workspaceRoot -Directory |
                Select-Object -ExpandProperty Name |
                Sort-Object
        )
        if (@(Compare-Object $standardNames $cleanChildren).Count -ne 0) {
            throw "Clean Setup did not create exactly the three standard workspace directories."
        }
        if (Test-Path -LiteralPath (Join-Path $workspaceRoot "Inbox")) {
            throw "Clean Setup created the forbidden Inbox directory."
        }

        $currentUserSid = [Security.Principal.WindowsIdentity]::GetCurrent().
            User.Value
        $administratorSid = [Security.Principal.SecurityIdentifier]::new(
            [Security.Principal.WellKnownSidType]::BuiltinAdministratorsSid,
            $null
        ).Value
        $currentIdentity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $allowedOwnerSids = @($currentUserSid)
        if ($currentIdentity.Groups.Value -contains $administratorSid) {
            $allowedOwnerSids += $administratorSid
        }
        foreach ($name in $standardNames) {
            $acl = Get-Acl -LiteralPath (Join-Path $workspaceRoot $name)
            $ownerSid = $acl.GetOwner(
                [Security.Principal.SecurityIdentifier]
            ).Value
            if ($ownerSid -notin $allowedOwnerSids) {
                throw "Workspace directory '$name' has unexpected owner SID '$ownerSid'."
            }
        }

        $journalPath = Join-Path $workspaceRoot "Tagebuch"
        $sentinelPath = Join-Path $journalPath "existing-entry.txt"
        $customPath = Join-Path $workspaceRoot "CustomData"
        $customFile = Join-Path $customPath "keep.txt"
        [IO.Directory]::CreateDirectory($customPath) | Out-Null
        [IO.File]::WriteAllText(
            $sentinelPath,
            "existing journal content",
            [Text.UTF8Encoding]::new($false)
        )
        [IO.File]::WriteAllText(
            $customFile,
            "existing custom content",
            [Text.UTF8Encoding]::new($false)
        )
        (Get-Item -LiteralPath $sentinelPath).LastWriteTimeUtc = $protectedTimestamp
        (Get-Item -LiteralPath $customFile).LastWriteTimeUtc = $protectedTimestamp
        (Get-Item -LiteralPath $journalPath).LastWriteTimeUtc = $protectedTimestamp
        (Get-Item -LiteralPath $customPath).LastWriteTimeUtc = $protectedTimestamp
        $sentinelHash = (Get-FileHash -LiteralPath $sentinelPath -Algorithm SHA256).Hash
        $customHash = (Get-FileHash -LiteralPath $customFile -Algorithm SHA256).Hash

        [IO.Directory]::Delete((Join-Path $workspaceRoot "Temp"))
        [IO.Directory]::Delete((Join-Path $workspaceRoot "Trashcan"))

        Invoke-WorkspaceFixtureSetup `
            -SetupPath $setupFixture `
            -WorkspacePath $workspaceRoot

        if ((Get-FileHash -LiteralPath $sentinelPath -Algorithm SHA256).Hash -ne
            $sentinelHash -or
            (Get-FileHash -LiteralPath $customFile -Algorithm SHA256).Hash -ne
            $customHash) {
            throw "Repair changed existing workspace content."
        }
        if ((Get-Item -LiteralPath $sentinelPath).LastWriteTimeUtc -ne
            $protectedTimestamp -or
            (Get-Item -LiteralPath $customFile).LastWriteTimeUtc -ne
            $protectedTimestamp -or
            (Get-Item -LiteralPath $journalPath).LastWriteTimeUtc -ne
            $protectedTimestamp -or
            (Get-Item -LiteralPath $customPath).LastWriteTimeUtc -ne
            $protectedTimestamp) {
            throw "Repair changed existing workspace timestamps."
        }
        foreach ($name in $standardNames) {
            if (-not (Test-Path -LiteralPath (Join-Path $workspaceRoot $name) -PathType Container)) {
                throw "Repair did not restore the missing '$name' directory."
            }
        }
        if (Test-Path -LiteralPath (Join-Path $workspaceRoot "Inbox")) {
            throw "Repair created the forbidden Inbox directory."
        }

        $firstRepairSnapshot = Get-WorkspaceSnapshot -Path $workspaceRoot
        Start-Sleep -Milliseconds 1100
        Invoke-WorkspaceFixtureSetup `
            -SetupPath $setupFixture `
            -WorkspacePath $workspaceRoot
        $secondRepairSnapshot = Get-WorkspaceSnapshot -Path $workspaceRoot
        Start-Sleep -Milliseconds 1100
        Invoke-WorkspaceFixtureSetup `
            -SetupPath $setupFixture `
            -WorkspacePath $workspaceRoot
        $thirdRepairSnapshot = Get-WorkspaceSnapshot -Path $workspaceRoot
        if ($secondRepairSnapshot -ne $firstRepairSnapshot -or
            $thirdRepairSnapshot -ne $firstRepairSnapshot) {
            throw "Repeated Repair runs changed workspace data."
        }

        Write-Host "WORKSPACE_STRUCTURE_CLEAN_INSTALL_PASSED"
        Write-Host "WORKSPACE_STRUCTURE_FIRST_REPAIR_PASSED"
        Write-Host "WORKSPACE_STRUCTURE_REPEATED_REPAIR_PASSED"
        Write-Host "WORKSPACE_STRUCTURE_CURRENT_USER_OWNER_PASSED"
    }
    finally {
        if (Test-Path -LiteralPath $fixtureRoot) {
            $resolvedFixtureRoot = [IO.Path]::GetFullPath($fixtureRoot)
            if (-not $resolvedFixtureRoot.StartsWith(
                $systemTemp,
                [StringComparison]::OrdinalIgnoreCase
            )) {
                throw "Refusing unsafe workspace fixture cleanup: $resolvedFixtureRoot"
            }
            Remove-Item -LiteralPath $resolvedFixtureRoot -Recurse -Force
        }
    }
}

if ($ExerciseWorkspaceStructure) {
    Invoke-WorkspaceStructureSmoke
    return
}

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName System.Windows.Forms
Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class PlwcUiMouse {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr windowHandle);

    [DllImport("user32.dll")]
    public static extern IntPtr SetFocus(IntPtr windowHandle);

    [DllImport("user32.dll")]
    public static extern IntPtr SendMessage(
        IntPtr windowHandle, uint message, IntPtr word, IntPtr data);

    [DllImport("user32.dll")]
    public static extern void mouse_event(
        uint flags, uint dx, uint dy, uint data, UIntPtr extraInfo);

    public static void Click(int x, int y) {
        SetCursorPos(x, y);
        mouse_event(0x0002, 0, 0, 0, UIntPtr.Zero);
        mouse_event(0x0004, 0, 0, 0, UIntPtr.Zero);
    }
}
"@

$resolvedSetup = (Resolve-Path -LiteralPath $SetupPath).Path
if ($MaximumNextClicks -gt 8 -and -not $FixtureGuardsInstallation) {
    throw "More than eight Next clicks require an installation-guarded UI fixture."
}
$logPath = Join-Path $env:TEMP "plwc-installer-ui-smoke.log"
Remove-Item -LiteralPath $logPath -Force -ErrorAction SilentlyContinue

function Get-SetupWindows {
    param([int] $ProcessId)

    $condition = if ($ProcessId -gt 0) {
        New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
            $ProcessId
        )
    }
    else {
        [System.Windows.Automation.Condition]::TrueCondition
    }
    return @(
        [System.Windows.Automation.AutomationElement]::RootElement.FindAll(
            [System.Windows.Automation.TreeScope]::Children,
            $condition
        )
    )
}

function Get-Descendants {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Element
    )

    return @(
        $Element.FindAll(
            [System.Windows.Automation.TreeScope]::Descendants,
            [System.Windows.Automation.Condition]::TrueCondition
        )
    )
}

function Invoke-Button {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Button
    )

    try {
        $pattern = $Button.GetCurrentPattern(
            [System.Windows.Automation.InvokePattern]::Pattern
        )
        $pattern.Invoke()
    }
    catch {
        $handle = $Button.Current.NativeWindowHandle
        if ($handle -ne 0) {
            [void] [PlwcUiMouse]::SendMessage(
                [IntPtr] $handle,
                0x00F5,
                [IntPtr]::Zero,
                [IntPtr]::Zero
            )
            return
        }
        $bounds = $Button.Current.BoundingRectangle
        if ($bounds.IsEmpty) {
            throw
        }
        [PlwcUiMouse]::Click(
            [int] ($bounds.Left + ($bounds.Width / 2)),
            [int] ($bounds.Top + ($bounds.Height / 2))
        )
    }
}

function Invoke-Selection {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Element
    )

    $pattern = $Element.GetCurrentPattern(
        [System.Windows.Automation.SelectionItemPattern]::Pattern
    )
    $pattern.Select()
}

function Get-NextButton {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Wizard,
        [Parameter(Mandatory = $true)]
        [string[]] $Names
    )

    return Get-Descendants -Element $Wizard |
        Where-Object {
            $_.Current.ControlType -eq
                [System.Windows.Automation.ControlType]::Button -and
            $_.Current.Name -in $Names
        } |
        Select-Object -First 1
}

function Save-DiagnosticScreenshot {
    param([string] $Path)

    $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen
    $bitmap = [Drawing.Bitmap]::new($bounds.Width, $bounds.Height)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    try {
        $graphics.CopyFromScreen(
            $bounds.Left,
            $bounds.Top,
            0,
            0,
            $bounds.Size
        )
        $bitmap.Save($Path, [Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $graphics.Dispose()
        $bitmap.Dispose()
    }
}

function Test-InstallerRuntimeDialog {
    param([int] $ProcessId)

    Start-Sleep -Milliseconds 350
    $windows = Get-SetupWindows -ProcessId $ProcessId
    $runtimeWindow = $windows | Where-Object {
        @(
            Get-Descendants -Element $_ | Where-Object {
                $_.Current.Name -like "Runtime error*"
            }
        ).Count -gt 0
    } | Select-Object -First 1
    if ($null -eq $runtimeWindow) {
        return
    }

    $runtimeText = (
        Get-Descendants -Element $runtimeWindow |
            Where-Object {
                $_.Current.ControlType -eq
                    [System.Windows.Automation.ControlType]::Text
            } |
            ForEach-Object { $_.Current.Name }
    ) -join " "
    throw "Installer runtime dialog detected: $runtimeText"
}

function Get-ToggleState {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Element
    )

    $pattern = $null
    if (-not $Element.TryGetCurrentPattern(
        [System.Windows.Automation.TogglePattern]::Pattern,
        [ref] $pattern
    )) {
        throw "The prerequisite option '$($Element.Current.Name)' has no TogglePattern."
    }
    return $pattern.Current.ToggleState
}

function Get-ElementReadableText {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Element
    )

    $parts = @()
    if (-not [string]::IsNullOrWhiteSpace($Element.Current.Name)) {
        $parts += $Element.Current.Name
    }
    $valuePattern = $null
    if ($Element.TryGetCurrentPattern(
        [System.Windows.Automation.ValuePattern]::Pattern,
        [ref] $valuePattern
    )) {
        $value = $valuePattern.Current.Value
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            $parts += $value
        }
    }
    return ($parts -join "`n")
}

function Invoke-Toggle {
    param(
        [Parameter(Mandatory = $true)]
        [System.Windows.Automation.AutomationElement] $Element
    )

    $pattern = $null
    if ($Element.TryGetCurrentPattern(
        [System.Windows.Automation.TogglePattern]::Pattern,
        [ref] $pattern
    )) {
        $pattern.Toggle()
        return
    }

    $bounds = $Element.Current.BoundingRectangle
    if ($bounds.IsEmpty) {
        throw "The prerequisite option '$($Element.Current.Name)' has no bounds."
    }

    $wizard = Get-SetupWindows -ProcessId $Element.Current.ProcessId |
        Where-Object { $_.Current.ClassName -eq "TWizardForm" } |
        Select-Object -First 1
    if ($null -ne $wizard) {
        [void] [PlwcUiMouse]::SetForegroundWindow(
            [IntPtr] $wizard.Current.NativeWindowHandle
        )
    }

    $selectionPattern = $null
    if ($Element.TryGetCurrentPattern(
        [System.Windows.Automation.SelectionItemPattern]::Pattern,
        [ref] $selectionPattern
    )) {
        $selectionPattern.Select()
        $parent = [System.Windows.Automation.TreeWalker]::ControlViewWalker.
            GetParent($Element)
        while ($null -ne $parent -and
            $parent.Current.NativeWindowHandle -eq 0) {
            $parent = [System.Windows.Automation.TreeWalker]::ControlViewWalker.
                GetParent($parent)
        }
        if ($null -ne $parent) {
            $handle = [IntPtr] $parent.Current.NativeWindowHandle
            $listItems = @(
                Get-Descendants -Element $parent |
                    Where-Object {
                        $_.Current.ControlType -eq
                            [System.Windows.Automation.ControlType]::ListItem
                    } |
                    Sort-Object { $_.Current.BoundingRectangle.Top }
            )
            $itemIndex = [Array]::FindIndex(
                [object[]] $listItems,
                [Predicate[object]] {
                    param($candidate)
                    $candidate.Current.Name -eq $Element.Current.Name
                }
            )
            Write-Host (
                "Toggling '{0}' through {1} hwnd={2}, index={3}." -f
                    $Element.Current.Name,
                    $parent.Current.ClassName,
                    $parent.Current.NativeWindowHandle,
                    $itemIndex
            )
            [void] [PlwcUiMouse]::SendMessage(
                $handle, 0x0186, [IntPtr] $itemIndex, [IntPtr]::Zero
            )
            [void] [PlwcUiMouse]::SetFocus($handle)
            [void] [PlwcUiMouse]::SendMessage(
                $handle, 0x0100, [IntPtr] 0x20, [IntPtr]::Zero
            )
            [void] [PlwcUiMouse]::SendMessage(
                $handle, 0x0102, [IntPtr] 0x20, [IntPtr]::Zero
            )
            [void] [PlwcUiMouse]::SendMessage(
                $handle, 0x0101, [IntPtr] 0x20, [IntPtr]::Zero
            )
            return
        }
    }

    [PlwcUiMouse]::Click(
        [int] ($bounds.Left + 12),
        [int] ($bounds.Top + ($bounds.Height / 2))
    )
}

$process = $null
$uiProcessId = 0
$componentPlanConfigured = $false
$reachedReadyPage = $false
$setupP003BuildIdentityVisible = $false
$setupP101SizeBreakdownVisible = $false
$setupP002Fix01FlowObserved = $false
$setupP002Fix01BusyPageVisible = $false
$setupP002Fix01BusyDeadline = [DateTime]::UtcNow.AddMinutes(3)
try {
    $arguments = @(
        "/LANG=$Language",
        "/LOG=$logPath"
    )
    $process = Start-Process `
        -FilePath $resolvedSetup `
        -ArgumentList $arguments `
        -PassThru

    $nextNames = if ($Language -eq "german") {
        @("Weiter", "Installieren")
    }
    else {
        @("Next", "Install")
    }

    for ($click = 0; $click -lt $MaximumNextClicks; $click++) {
        Start-Sleep -Milliseconds 800
        if ($process.HasExited) {
            throw "Setup exited unexpectedly with code $($process.ExitCode)."
        }

        $windows = Get-SetupWindows -ProcessId $uiProcessId
        if ($uiProcessId -eq 0) {
            $windows = @(
                $windows | Where-Object {
                    $_.Current.ClassName -eq "TSelectLanguageForm" -or
                    (
                        $_.Current.ClassName -eq "TWizardForm" -and
                        $_.Current.Name -like "Setup - PLwC*"
                    )
                }
            )
            if ($windows.Count -gt 0) {
                $uiProcessId = $windows[0].Current.ProcessId
                $windows = Get-SetupWindows -ProcessId $uiProcessId
            }
        }
        $languageWindow = $windows | Where-Object {
            $_.Current.ClassName -eq "TSelectLanguageForm"
        } | Select-Object -First 1
        if ($null -ne $languageWindow) {
            $okButton = Get-Descendants -Element $languageWindow |
                Where-Object {
                    $_.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::Button -and
                    $_.Current.Name -eq "OK"
                } |
                Select-Object -First 1
            if ($null -eq $okButton) {
                throw "The language dialog OK button was not found."
            }
            Invoke-Button -Button $okButton
            continue
        }

        Test-InstallerRuntimeDialog -ProcessId $uiProcessId

        $wizard = $windows | Where-Object {
            $_.Current.ClassName -eq "TWizardForm"
        } | Select-Object -First 1
        if ($null -eq $wizard) {
            continue
        }

        $elements = Get-Descendants -Element $wizard
        $headings = @(
            $elements |
                Where-Object {
                    $_.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::Text -and
                    -not [string]::IsNullOrWhiteSpace($_.Current.Name)
                } |
                ForEach-Object { $_.Current.Name } |
                Select-Object -First 3
        )
        $visibleText = (
            $elements |
                Where-Object { -not $_.Current.IsOffscreen } |
                ForEach-Object { Get-ElementReadableText -Element $_ } |
                Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        ) -join "`n"
        if ($ExpectSetupP003BuildIdentity -and
            -not $setupP003BuildIdentityVisible -and
            $visibleText -match 'installer-r24') {
            $setupP003BuildIdentityVisible = $true
            Write-Host "SETUP_P0_03_BUILD_IDENTITY_VISIBLE"
        }
        if ($ExpectSetupP002Fix01Flow -and
            -not $setupP002Fix01FlowObserved -and
            (Test-Path -LiteralPath $logPath -PathType Leaf)) {
            $flowLogText = Get-Content -LiteralPath $logPath -Raw
            if ($flowLogText -match 'Prerequisite action controls locked' -and
                $flowLogText -match 'Prerequisite action controls unlocked') {
                $setupP002Fix01FlowObserved = $true
                Write-Host "SETUP_P0_02_FIX_01_CHECK_LOCK_OBSERVED"
            }
        }
        if ($ExpectSetupP101SizeBreakdown -and
            -not $setupP101SizeBreakdownVisible -and
            $visibleText -match 'PLwC payload|PLwC-Payload') {
            foreach ($requiredSizeText in @(
                'Python',
                'Node\.js',
                'Docker Desktop',
                'WSL',
                'first use|erste Nutzung',
                'unknown|unbekannt'
            )) {
                if ($visibleText -notmatch $requiredSizeText) {
                    throw "SETUP-P1-01 size text was not visible: $requiredSizeText"
                }
            }
            $setupP101SizeBreakdownVisible = $true
            Write-Host "SETUP_P1_01_SIZE_BREAKDOWN_VISIBLE"
        }
        if ($ExpectSetupP002Diagnostics -and
            ($visibleText -match "Status for the current component selection|Status f.r die aktuelle Komponentenauswahl")) {
            foreach ($requiredDiagnostic in @(
                "Docker Desktop",
                "Docker",
                "WSL2",
                "Virtualization|Virtualisierung"
            )) {
                if ($visibleText -notmatch $requiredDiagnostic) {
                    throw "SETUP-P0-02 diagnostic text was not visible: $requiredDiagnostic"
                }
            }
            Write-Host "SETUP_P0_02_DIAGNOSTICS_VISIBLE"
        }
        $nextButton = Get-NextButton -Wizard $wizard -Names $nextNames
        $prerequisiteBusyVisible = $ExpectSetupP002Fix01Flow -and
            $visibleText -match (
                'Setup is detecting installed components|Setup erkennt die installierten Komponenten|' +
                'The selection is locked until all selected downloads|' +
                'Die Auswahl bleibt gesperrt, bis alle .* Downloads'
            )
        if ($prerequisiteBusyVisible) {
            if ($null -ne $nextButton -and $nextButton.Current.IsEnabled) {
                throw "Next was enabled while prerequisite detection was busy."
            }
            $prerequisiteChoice = $elements | Where-Object {
                -not $_.Current.IsOffscreen -and
                $_.Current.Name -match 'Python|Node\.js|Docker'
            } | Select-Object -First 1
            if ($null -ne $prerequisiteChoice) {
                $prerequisiteList =
                    [System.Windows.Automation.TreeWalker]::RawViewWalker.
                        GetParent($prerequisiteChoice)
                if ($null -ne $prerequisiteList -and
                    $prerequisiteList.Current.IsEnabled) {
                    throw "Prerequisite choices were enabled while detection was busy."
                }
            }
            if ([DateTime]::UtcNow -gt $setupP002Fix01BusyDeadline) {
                throw "Prerequisite detection remained busy for more than three minutes."
            }
            if (-not $setupP002Fix01BusyPageVisible) {
                $setupP002Fix01BusyPageVisible = $true
                Write-Host "SETUP_P0_02_FIX_01_BUSY_PAGE_VISIBLE"
            }
            $click--
            continue
        }
        if ($null -eq $nextButton) {
            throw "The localized Next button was not found."
        }
        $choices = @(
            $elements |
                Where-Object {
                    $_.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::CheckBox -or
                    (
                        $_.Current.ControlType -eq
                            [System.Windows.Automation.ControlType]::ListItem -and
                        -not $_.Current.IsOffscreen
                    )
                } |
                ForEach-Object {
                    $patterns = @(
                        $_.GetSupportedPatterns() |
                            ForEach-Object { $_.ProgrammaticName }
                    )
                    "{0} (enabled={1}, type={2}, patterns={3}, bounds={4})" -f
                        $_.Current.Name,
                        $_.Current.IsEnabled,
                        $_.Current.ControlType.ProgrammaticName,
                        ($patterns -join ","),
                        $_.Current.BoundingRectangle
                }
        )
        Write-Host (
            "Page {0}: headings=[{1}] next='{2}' enabled={3} choices=[{4}]" -f
                ($click + 1),
                ($headings -join " | "),
                $nextButton.Current.Name,
                $nextButton.Current.IsEnabled,
                ($choices -join " | ")
        )
        if (($ExercisePrerequisiteSelection -or $ExerciseDownload) -and
            $ComponentPlan -eq "chatbridge" -and
            -not $componentPlanConfigured) {
            $customType = $elements |
                Where-Object {
                    $_.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::ListItem -and
                    $_.Current.Name -in @(
                        "Benutzerdefinierte Auswahl",
                        "Custom selection"
                    )
                } |
                Select-Object -First 1
            $chatBridgeComponent = $elements |
                Where-Object {
                    $_.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::ListItem -and
                    $_.Current.Name -eq "PLwC Chat Bridge"
                } |
                Select-Object -First 1
            if ($null -ne $customType -and $null -ne $chatBridgeComponent) {
                Invoke-Selection -Element $customType
                Invoke-Toggle -Element $chatBridgeComponent
                Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                $componentPlanConfigured = $true
                Write-Host "Configured the custom Chat Bridge component plan."
            }
        }
        if (-not $nextButton.Current.IsEnabled) {
            $prerequisiteOptions = @(
                $elements | Where-Object {
                    $_.Current.ControlType -eq
                        [System.Windows.Automation.ControlType]::ListItem -and
                    $_.Current.Name -match "Python|Node\.js|Docker"
                }
            )
            if (($ExercisePrerequisiteSelection -or $ExerciseDownload) -and
                $prerequisiteOptions.Count -eq 3) {
                $pythonOption = $prerequisiteOptions |
                    Where-Object { $_.Current.Name -match "Python" } |
                    Select-Object -First 1
                $nodeOption = $prerequisiteOptions |
                    Where-Object { $_.Current.Name -match "Node\.js" } |
                    Select-Object -First 1
                $dockerOption = $prerequisiteOptions |
                    Where-Object { $_.Current.Name -match "Docker" } |
                    Select-Object -First 1

                if (-not $ExerciseDownload) {
                    Invoke-Toggle -Element $dockerOption
                    Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                    $nextAfterDocker = Get-NextButton `
                        -Wizard $wizard `
                        -Names $nextNames
                    if ($nextAfterDocker.Current.IsEnabled) {
                        throw "Optional Docker alone enabled Next although Python is required."
                    }
                }

                Invoke-Toggle -Element $pythonOption
                Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                $nextAfterPython = Get-NextButton `
                    -Wizard $wizard `
                    -Names $nextNames
                if ($ComponentPlan -eq "gateway" -and
                    -not $nextAfterPython.Current.IsEnabled) {
                    Save-DiagnosticScreenshot -Path (
                        Join-Path $env:TEMP "plwc-installer-ui-selection-failure.png"
                    )
                    throw "Selecting required Python did not enable Next."
                }
                if ($ComponentPlan -eq "chatbridge" -and
                    $nextAfterPython.Current.IsEnabled) {
                    throw "Python alone enabled Next although Chat Bridge also requires Node.js."
                }

                if ($ExerciseDownload) {
                    if ($ComponentPlan -ne "gateway") {
                        throw "The download fixture currently supports the Gateway plan only."
                    }
                    Invoke-Button -Button $nextAfterPython
                    Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                    $batchDeadline = [DateTime]::UtcNow.AddSeconds(60)
                    $logText = ""
                    do {
                        Start-Sleep -Milliseconds 250
                        $logText = Get-Content -LiteralPath $logPath -Raw
                    } until (
                        $logText -match "Prerequisite batch finished" -or
                        [DateTime]::UtcNow -ge $batchDeadline
                    )
                    if ($logText -notmatch "UI_SMOKE_DOWNLOAD_VERIFIED" -or
                        $logText -notmatch "UI_SMOKE_POST_DOWNLOAD_PREPARED" -or
                        $logText -notmatch "UI_SMOKE_DOWNLOAD_PATH_COMPLETED" -or
                        $logText -notmatch "Prerequisite batch started" -or
                        $logText -notmatch "Prerequisite batch finished") {
                        throw "The guarded prerequisite post-download preparation did not complete."
                    }
                    Write-Host "SETUP_P0_02_FIX_01_BATCH_STABLE"
                    Write-Host "Guarded prerequisite post-download preparation completed."
                    break
                }

                if ($ComponentPlan -eq "chatbridge") {
                    Invoke-Toggle -Element $nodeOption
                    Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                    $nextAfterNode = Get-NextButton `
                        -Wizard $wizard `
                        -Names $nextNames
                    if (-not $nextAfterNode.Current.IsEnabled) {
                        throw "Selecting required Python and Node.js did not enable Next."
                    }

                    Invoke-Toggle -Element $nodeOption
                    Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                    $nextWithoutNode = Get-NextButton `
                        -Wizard $wizard `
                        -Names $nextNames
                    if ($nextWithoutNode.Current.IsEnabled) {
                        throw "Clearing required Node.js did not disable Next."
                    }
                    Invoke-Toggle -Element $nodeOption
                }
                else {
                    Invoke-Toggle -Element $pythonOption
                    Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                    $nextWithoutPython = Get-NextButton `
                        -Wizard $wizard `
                        -Names $nextNames
                    if ($nextWithoutPython.Current.IsEnabled) {
                        throw "Clearing required Python did not disable Next."
                    }
                    Invoke-Toggle -Element $pythonOption
                }

                Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                Write-Host (
                    "Prerequisite selection logic passed: Docker optional, " +
                    "required runtimes control the Next state."
                )
                $guardedNext = Get-NextButton `
                    -Wizard $wizard `
                    -Names $nextNames
                Invoke-Button -Button $guardedNext
                Test-InstallerRuntimeDialog -ProcessId $uiProcessId
                Start-Sleep -Milliseconds 300
                $logText = Get-Content -LiteralPath $logPath -Raw
                if ($logText -notmatch "UI_SMOKE_PREREQUISITE_PLAN_ACCEPTED") {
                    throw "The guarded Next path did not accept the selected prerequisite plan."
                }
                Write-Host "Guarded Next path accepted the prerequisite plan."
                break
            }
            Write-Host "Next is disabled on this prerequisite plan; UI smoke stops safely."
            break
        }
        if ($nextButton.Current.Name -in @("Installieren", "Install")) {
            $reachedReadyPage = $true
            Write-Host "Reached the ready page; UI smoke stops before installation."
            break
        }

        Invoke-Button -Button $nextButton
    }
}
finally {
    if ($uiProcessId -gt 0) {
        Stop-Process -Id $uiProcessId -Force -ErrorAction SilentlyContinue
    }
    if ($null -ne $process -and -not $process.HasExited) {
        Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    }
}

if ($FixtureGuardsInstallation -and
    $MaximumNextClicks -gt 8 -and
    -not $ExercisePrerequisiteSelection -and
    -not $ExerciseDownload -and
    -not $reachedReadyPage) {
    throw "The UI smoke did not reach the localized ready-page Install button."
}
if ($ExpectSetupP003BuildIdentity -and -not $setupP003BuildIdentityVisible) {
    throw "The installer revision was not visible in the guarded UI smoke."
}
if ($ExpectSetupP101SizeBreakdown -and -not $setupP101SizeBreakdownVisible) {
    throw "The SETUP-P1-01 size breakdown was not visible in the guarded UI smoke."
}
if ($ExpectSetupP002Fix01Flow -and -not $setupP002Fix01FlowObserved) {
    throw "The prerequisite detection lock was not observed in the UI smoke log."
}
if ($ExpectSetupP002Fix01Flow -and -not $setupP002Fix01BusyPageVisible) {
    Write-Host "SETUP_P0_02_FIX_01_FAST_CHECK_COMPLETED"
}

Write-Host "Installer UI smoke completed without starting installation."
Write-Host "Log: $logPath"
