Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$testsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$installerRoot = [IO.Path]::GetFullPath((Join-Path $testsRoot ".."))
$repoRoot = [IO.Path]::GetFullPath((Join-Path $installerRoot "..\.."))
$buildScript = Join-Path $installerRoot "build.ps1"
$setupScript = Join-Path $installerRoot "PLwCSetup.iss"
$assetsRoot = Join-Path $installerRoot "assets"
$mcpLockPath = Join-Path $assetsRoot "mcp-runtime-lock.txt"
$runtimeRequirementsPath = Join-Path $assetsRoot "runtime-requirements.in"
$prerequisiteSizesPath = Join-Path $assetsRoot "prerequisite-sizes.iss"
$pythonRuntimeProbePath = Join-Path $assetsRoot "python-runtime-probe.py"
$bridgeIdentityPath = Join-Path $repoRoot "integrations\plwc-chat-bridge\native\extension-identity.json"
$bridgeBuildIdentityPath = Join-Path $repoRoot "integrations\plwc-chat-bridge\build-identity.json"
$bridgeScriptsRoot = Join-Path $repoRoot "integrations\plwc-chat-bridge\scripts"
$nativeInstallScriptPath = Join-Path $bridgeScriptsRoot "install-native-launcher-windows.ps1"
$autostartInstallScriptPath = Join-Path $bridgeScriptsRoot "install-autostart-windows.ps1"
$bridgeStartScriptPath = Join-Path $bridgeScriptsRoot "start-windows.ps1"
$nativeLauncherSourcePath = Join-Path $repoRoot "integrations\plwc-chat-bridge\native\launcher-host\Plwc.ChatBridge.NativeLauncher.cs"
$bridgeLaunchScriptPath = Join-Path $repoRoot "integrations\plwc-chat-bridge\bridge\scripts\launch-bridge.mjs"
$installerUiSmokePath = Join-Path $testsRoot "installer-ui-smoke.ps1"
$windowsInstallerGuidePath = Join-Path $repoRoot "docs\WINDOWS_INSTALLER_GUIDE.md"
$workOrderPath = Join-Path $repoRoot "docs\ARBEITSAUFTRAG_PLWC_BRIDGE_SETUP.md"
$windowsInstallerPlanPath = Join-Path $repoRoot "docs\WINDOWS_INSTALLER_PLAN.md"
$gettingStartedRoot = Join-Path $assetsRoot "getting-started"
$gettingStartedEnglishPath = Join-Path $gettingStartedRoot "getting-started-en.html"
$gettingStartedGermanPath = Join-Path $gettingStartedRoot "getting-started-de.html"
$gettingStartedStylesPath = Join-Path $gettingStartedRoot "getting-started.css"
$configurationRoot = Join-Path $assetsRoot "configuration"
$configurationFiles = @(
    "plwc-config.py",
    "plwc-config-en.html",
    "plwc-config-de.html",
    "plwc-config.css",
    "plwc-config.js"
)
$componentsManifestPath = Join-Path $installerRoot "manifests\components.json"
$workspaceStructurePath = Join-Path $assetsRoot "workspace-structure.iss"
$workspaceFixturePath = Join-Path $testsRoot "workspace-structure-fixture.iss"
$testGeneratedOutputRoot = Join-Path $installerRoot ".test-build"
$unsignedGeneratedOutputRoot = Join-Path $installerRoot ".unsigned-build"
$stageRoot = Join-Path $testGeneratedOutputRoot "stage"
$distRoot = Join-Path $testGeneratedOutputRoot "dist"
$testScriptPath = [IO.Path]::GetFullPath($MyInvocation.MyCommand.Path)

function Get-InnoSection {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Source,

        [Parameter(Mandatory = $true)]
        [string] $Name
    )

    $escapedName = [regex]::Escape($Name)
    $match = [regex]::Match(
        $Source,
        "(?ms)^\[$escapedName\]\s*(?<Body>.*?)(?=^\[[^\]]+\]|\z)"
    )
    if (-not $match.Success) {
        return ""
    }
    return $match.Groups["Body"].Value
}

function Get-PascalCalls {
    param(
        [Parameter(Mandatory = $true)]
        [string] $Source,

        [Parameter(Mandatory = $true)]
        [string] $FunctionPattern
    )

    return @(
        [regex]::Matches(
            $Source,
            "(?is)\b(?:$FunctionPattern)\s*\((?<Arguments>.*?)\);"
        )
    )
}

Describe "PLwC Windows installer source contracts" {
    It "keeps the maintainer harness inside installer/windows" {
        (Test-Path -LiteralPath $buildScript -PathType Leaf) | Should Be $true
        ([IO.Path]::GetFullPath($buildScript).StartsWith($installerRoot, [StringComparison]::OrdinalIgnoreCase)) | Should Be $true
    }

    It "does not make the build harness an end-user APPDATA installer" {
        $source = Get-Content -LiteralPath $buildScript -Raw
        $source | Should Not Match '(?i)env:APPDATA|SpecialFolder\]::ApplicationData|HKCU:'
        $source | Should Match 'ValidateOnly'
        $source | Should Match 'ISCC'
    }

    It "defines the selectable component surface in the Inno source" {
        (Test-Path -LiteralPath $setupScript -PathType Leaf) | Should Be $true
        $source = Get-Content -LiteralPath $setupScript -Raw -Encoding UTF8
        $source | Should Match '(?i)gateway'
        $source | Should Match '(?i)claude.*mcpb|mcpb.*claude'
        $source | Should Match '(?i)codex'
        $source | Should Match '(?i)odysseus'
        $source | Should Match '(?i)chat.?bridge'
        $source | Should Match '(?i)Components'
    }

    It "keeps workspace, profiles and runtime-wide roots distinct" {
        (Test-Path -LiteralPath $setupScript -PathType Leaf) | Should Be $true
        $source = Get-Content -LiteralPath $setupScript -Raw -Encoding UTF8
        $source | Should Match '(?i)\{userappdata\}\\PLwC\\app'
        foreach ($rootName in @("workspace", "profiles", "config", "state", "logs", "profile_backups")) {
            $escapedSuffix = [regex]::Escape("\$rootName")
            $source | Should Match ("(?i)GetDataRoot\s*\+\s*'{0}'" -f $escapedSuffix)
        }
    }

    It "uses one non-destructive workspace structure function for install, upgrade, and repair" {
        (Test-Path -LiteralPath $workspaceStructurePath -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath $workspaceFixturePath -PathType Leaf) | Should Be $true
        $source = Get-Content -LiteralPath $setupScript -Raw -Encoding UTF8
        $workspaceSource = Get-Content -LiteralPath $workspaceStructurePath -Raw -Encoding UTF8
        $fixtureSource = Get-Content -LiteralPath $workspaceFixturePath -Raw -Encoding UTF8

        $source | Should Match '(?im)^#include\s+"assets\\workspace-structure\.iss"\s*$'
        $source | Should Match '(?is)procedure\s+SaveGeneratedFiles.*?EnsureWorkspaceStructureAt\(GetWorkspacePath\(''''\)\)'
        $source | Should Match '(?is)procedure\s+CurStepChanged.*?CurStep\s*=\s*ssPostInstall.*?SaveGeneratedFiles\s*;'
        $workspaceSource | Should Match '(?i)procedure\s+EnsureWorkspaceStructureAt'
        $workspaceSource | Should Match "'Tagebuch'"
        $workspaceSource | Should Match "'Temp'"
        $workspaceSource | Should Match "'Trashcan'"
        $workspaceSource | Should Not Match '(?i)Inbox|DeleteFile|DelTree|RemoveDir|Clear|Clean'

        $directoryLiterals = @(
            [regex]::Matches(
                $workspaceSource,
                "(?i)AddBackslash\(WorkspacePath\)\s*\+\s*'(?<Name>[^']+)'"
            ) |
                ForEach-Object { $_.Groups["Name"].Value } |
                Select-Object -Unique
        )
        ($directoryLiterals -join ",") | Should Be "Tagebuch,Temp,Trashcan"
        ([regex]::Matches(
            $source,
            '(?i)EnsureWorkspaceStructureAt\(GetWorkspacePath\(''''\)\)'
        ).Count) | Should Be 1

        $setupSection = Get-InnoSection -Source $source -Name "Setup"
        $setupSection | Should Match '(?im)^\s*PrivilegesRequired\s*=\s*lowest\s*$'
        $fixtureSource | Should Match '(?im)^\s*PrivilegesRequired\s*=\s*lowest\s*$'
    }

    It "preserves workspace data across the first and repeated Repair runs" {
        $output = @(
            & $installerUiSmokePath -ExerciseWorkspaceStructure *>&1
        )
        $text = $output -join "`n"
        $text | Should Match 'WORKSPACE_STRUCTURE_CLEAN_INSTALL_PASSED'
        $text | Should Match 'WORKSPACE_STRUCTURE_FIRST_REPAIR_PASSED'
        $text | Should Match 'WORKSPACE_STRUCTURE_REPEATED_REPAIR_PASSED'
        $text | Should Match 'WORKSPACE_STRUCTURE_CURRENT_USER_OWNER_PASSED'
    }

    It "does not reference forbidden legacy installers" {
        $generatedRoots = @(
            $testGeneratedOutputRoot,
            $unsignedGeneratedOutputRoot,
            (Join-Path $installerRoot "stage"),
            (Join-Path $installerRoot "dist"),
            (Join-Path $installerRoot "output")
        )
        $installerSources = @(
            Get-ChildItem -LiteralPath $installerRoot -Recurse -File | Where-Object {
                $candidatePath = $_.FullName
                $_.Extension -in @(".iss", ".ps1") -and
                (@($generatedRoots | Where-Object {
                    $candidatePath.StartsWith($_, [StringComparison]::OrdinalIgnoreCase)
                }).Count -eq 0)
            }
        )
        foreach ($file in $installerSources) {
            if ($file.FullName -eq $buildScript -or $file.FullName -eq $testScriptPath) {
                continue
            }
            $source = Get-Content -LiteralPath $file.FullName -Raw
            $source | Should Not Match '(?i)install_pba2|setup-claude-server|track-installation|desktop-commander'
        }
    }
}

Describe "PLwC Windows clean-machine prerequisite and UI contracts" {
    $source = Get-Content -LiteralPath $setupScript -Raw -Encoding UTF8
    $setupSection = Get-InnoSection -Source $source -Name "Setup"
    $languageSection = Get-InnoSection -Source $source -Name "Languages"
    $typeSection = Get-InnoSection -Source $source -Name "Types"
    $componentSection = Get-InnoSection -Source $source -Name "Components"
    $customMessageSection = Get-InnoSection -Source $source -Name "CustomMessages"
    $runSection = Get-InnoSection -Source $source -Name "Run"
    $codeSection = Get-InnoSection -Source $source -Name "Code"

    It "defaults a clean installation to Gateway only" {
        $typeEntries = @([regex]::Matches($typeSection, '(?im)^\s*Name:\s*"(?<Name>[^"]+)"'))
        ($typeEntries.Count -gt 0) | Should Be $true
        $typeEntries[0].Groups["Name"].Value | Should Be "compact"

        $gatewayEntry = [regex]::Match($componentSection, '(?im)^\s*Name:\s*"gateway";[^\r\n]*$').Value
        $gatewayEntry | Should Match '(?i)Types:\s*[^\r\n;]*compact'
        foreach ($optionalComponent in @("claude", "codex", "odysseus", "chatbridge")) {
            $entry = [regex]::Match(
                $componentSection,
                ('(?im)^\s*Name:\s*"{0}";[^\r\n]*$' -f [regex]::Escape($optionalComponent))
            ).Value
            if ($entry -ne "") {
                $entry | Should Not Match '(?i)Types:\s*[^\r\n;]*compact'
            }
        }
    }

    It "shows a prerequisite page immediately after component selection" {
        $codeSection | Should Match '(?im)^\s*Prerequisite\w*\s*:\s*T\w*WizardPage\s*;'
        $codeSection | Should Match '(?is)Prerequisite\w*\s*:=\s*Create\w+Page\s*\(\s*wpSelectComponents\s*,'
        $codeSection | Should Match '(?is)CurPageID\s*=\s*Prerequisite\w*\.ID'
    }

    It "blocks Gateway setup unless Python 3.11 and all PLwC runtime modules are available" {
        $codeSection | Should Match '(?i)python(?:\.exe)?'
        $codeSection | Should Match '(?i)(?:3\s*[\.,]\s*11|Python\w*Minor\s*=\s*11)'
        $codeSection | Should Match '(?i)import\s+mcp'
        $codeSection | Should Match '(?i)fastembed'
        $codeSection | Should Match '(?i)qdrant_client'
        $codeSection | Should Match "(?is)if\s+not\s+PythonVersionOK\s+then.*?AppendPrerequisiteBlocker\(CustomMessage\('PrereqPythonMissing'\)\)"
        $codeSection | Should Match "(?is)if\s+PythonRuntimeOK\s+then.*?else.*?AppendPrerequisiteBlocker\(CustomMessage\('PrereqMcpMissing'\)\)"
        $codeSection | Should Match "(?is)function\s+PrepareToInstall.*?if\s+PrerequisiteBlockers\s*<>\s*''\s+then\s+Result\s*:="
    }

    It "treats Docker as optional and reports Safe Mode instead of blocking" {
        $codeSection | Should Match '(?i)docker(?:\.exe)?'
        $source | Should Match '(?i)Safe[ -]?Mode'
        foreach ($stateName in @(
            "DockerDesktopInstalled",
            "DockerCliOK",
            "DockerDaemonOK",
            "DockerImagesOK",
            "Wsl2OK",
            "VirtualizationCapabilityOK",
            "VirtualMachineDetected",
            "NestedVirtualizationOK"
        )) {
            $codeSection | Should Match "(?i)\b$stateName\b"
        }
        $codeSection | Should Match '(?i)DockerImagesOK'
        foreach ($image in @('python:3.12-slim', 'plwc-node-runner:0.1.0', 'plwc-document-worker:0.1.0')) {
            $codeSection | Should Match ([regex]::Escape($image))
        }
        $codeSection | Should Match '(?is)procedure\s+RunPrerequisiteChecks.*?ProbeDocker\s*;.*?ProbeWsl2\s*;.*?ProbeVirtualization\s*;'
        $codeSection | Should Match '(?is)DockerDesktopInstalled\s*:=.*?RegistryHasUninstallName\(''Docker Desktop''\)'
        $codeSection | Should Match '(?is)DockerDaemonOK\s*:=\s*RunProbeWithTimeout\s*\([^;]*docker_engine info'
        $codeSection | Should Match '(?is)DockerImagesOK\s*:=\s*DockerDaemonOK\s+and\s+RunProbeWithTimeout\s*\('
        $codeSection | Should Match '(?is)PrereqDockerDesktopOK.*?PrereqDockerCliMissing.*?PrereqDockerDaemonMissing.*?PrereqDockerImagesMissing'
        $codeSection | Should Match '(?is)PrereqWsl2OK.*?PrereqWsl2Missing.*?PrereqVirtualizationOK.*?PrereqVirtualizationMissing'
        $codeSection | Should Match '(?is)PrereqVmNestedMissing.*?PrereqSafeModeExplanation'
        $source | Should Match '(?is)#ifdef\s+UiSmokeVmNoNested.*?DockerDesktopInstalled\s*:=\s*True.*?DockerCliOK\s*:=\s*True.*?DockerDaemonOK\s*:=\s*False.*?VirtualMachineDetected\s*:=\s*True.*?NestedVirtualizationOK\s*:=\s*False.*?#endif'
        $uiSmokeSource = Get-Content -LiteralPath $installerUiSmokePath -Raw -Encoding UTF8
        $uiSmokeSource | Should Match '(?i)ExpectSetupP002Diagnostics'
        $uiSmokeSource | Should Match 'SETUP_P0_02_DIAGNOSTICS_VISIBLE'
        $codeSection | Should Match '(?i)WaitForSingleObject\s*\('
        $codeSection | Should Match '(?i)TerminateProcess\s*\('
        foreach ($nativeFunction in @(
            "WaitNamedPipe",
            "ShellExecuteEx",
            "GetExitCodeProcess",
            "TerminateProcess",
            "CloseHandle"
        )) {
            $nativeDeclaration = [regex]::Match(
                $codeSection,
                '(?is)function\s+{0}\b.*?external\s+''[^'']+''\s*;' -f
                    [regex]::Escape($nativeFunction)
            ).Value
            $nativeDeclaration | Should Match '(?is)\)\s*:\s*BOOL\s*;'
            $nativeDeclaration | Should Not Match '(?is)\)\s*:\s*Boolean\s*;'
        }
        $codeSection | Should Match "(?is)SetIniString\(\s*'PLwC'\s*,\s*'SafeModeExpected'"
        foreach ($diagnosticName in @(
            "DockerDesktopInstalled",
            "DockerCliPath",
            "DockerDaemonReachable",
            "DockerImagesAvailable",
            "Wsl2Available",
            "VirtualizationCapability",
            "VirtualMachineDetected",
            "NestedVirtualizationAvailable"
        )) {
            $codeSection | Should Match "(?is)SetIniString\(\s*'Diagnostics'\s*,\s*'$diagnosticName'"
        }
        $codeSection | Should Not Match "(?is)AppendPrerequisiteBlocker\([^;]*PrereqDocker"
        $codeSection | Should Not Match "(?is)AppendPrerequisiteBlocker\([^;]*PrereqWsl"
        $codeSection | Should Not Match "(?is)AppendPrerequisiteBlocker\([^;]*PrereqVirtual"
    }

    It "blocks the Claude component when Claude Desktop is absent" {
        $codeSection | Should Match '(?i)claude(?:\.exe)?'
        $codeSection | Should Match "(?is)WizardIsComponentSelected\(\s*'claude'\s*\).*?if\s+ClaudeDetected\s+then.*?else.*?AppendManualPrerequisiteBlocker\(CustomMessage\('PrereqClaudeMissing'\)\)"
        $codeSection | Should Match "(?i)FindRegisteredPackageExecutable\(\s*'claude_'"
        $codeSection | Should Match "(?im)^\s*ClaudeDetected\s*:=\s*DetectedClaudePath\s*<>\s*''\s*;"
        $codeSection | Should Not Match "(?im)^\s*DetectedClaudePath\s*:=\s*FindExecutable\(\s*'claude\.exe'\s*\)"
    }

    It "blocks Chat Bridge without Node 22.12 or a supported browser" {
        $codeSection | Should Match '(?i)node(?:\.exe)?'
        $codeSection | Should Match '(?is)(?:22\s*[\.,]\s*12|v\[0\].{0,20}22.{0,60}v\[1\].{0,20}12|Node\w*Major\s*=\s*22)'
        $codeSection | Should Match '(?i)(?:chrome\.exe|Google\\Chrome)'
        $codeSection | Should Match '(?i)(?:msedge\.exe|Microsoft\\Edge)'
        $codeSection | Should Match '(?i)(?:brave\.exe|BraveSoftware\\Brave-Browser)'
        $codeSection | Should Match '(?is)BrowserDetected\s*:=\s*ChromeDetected\s+or\s+EdgeDetected\s+or\s+BraveDetected'
        $codeSection | Should Match "(?is)WizardIsComponentSelected\(\s*'chatbridge'\s*\).*?if\s+NodeVersionOK\s+then.*?else.*?AppendPrerequisiteBlocker\(CustomMessage\('PrereqNodeMissing'\)\)"
        $codeSection | Should Match "(?is)WizardIsComponentSelected\(\s*'chatbridge'\s*\).*?if\s+BrowserDetected\s+then.*?else.*?AppendManualPrerequisiteBlocker\(CustomMessage\('PrereqBrowserMissing'\)\)"
    }

    It "does not let a missing browser block pure STDIO components" {
        $chatBridgeBlock = [regex]::Match(
            $codeSection,
            "(?is)if\s+WizardIsComponentSelected\(\s*'chatbridge'\s*\)\s+then.*?(?=if\s+WizardIsComponentSelected\(\s*'codex'\s*\))"
        ).Value
        $chatBridgeBlock | Should Match "PrereqBrowserMissing"
        $chatBridgeBlock | Should Match "AppendManualPrerequisiteBlocker"

        $stdioBlock = [regex]::Match(
            $codeSection,
            "(?is)if\s+WizardIsComponentSelected\(\s*'codex'\s*\).*?if\s+WizardIsComponentSelected\(\s*'odysseus'\s*\).*?(?=PrerequisiteReport\s*:=)"
        ).Value
        $stdioBlock | Should Not Match "PrereqBrowserMissing"
        $stdioBlock | Should Not Match "AppendManualPrerequisiteBlocker"
    }

    It "reports missing Codex and Odysseus as prepared-only warnings" {
        $codeSection | Should Match '(?i)codex(?:\.exe)?'
        $codeSection | Should Match '(?i)odysseus(?:\.exe)?'
        $codeSection | Should Match "(?i)FindRegisteredPackageExecutable\(\s*'openai\.codex_'"
        $source | Should Match '(?i)(?:Codex|Odysseus).*?(?:prepared|vorbereitet)'
        $source | Should Match '(?i)(?:prepared|vorbereitet).*?(?:Codex|Odysseus)'
        $codeSection | Should Not Match "(?is)WizardIsComponentSelected\(\s*'(?:codex|odysseus)'\s*\).*?(?:not\s+(?:Codex|Odysseus)\w*(?:Ready|Available|Found)).*?Result\s*:=\s*False"
    }

    It "offers explicit Python, Node and Docker acquisition without opting in by default" {
        $codeSection | Should Match '(?im)^\s*PrerequisiteActionsPage\s*:\s*TInputOptionWizardPage\s*;'
        $codeSection | Should Match '(?im)^\s*PrerequisiteActionsPage\.Values\[0\]\s*:=\s*False\s*;'
        $codeSection | Should Match '(?im)^\s*PrerequisiteActionsPage\.Values\[1\]\s*:=\s*False\s*;'
        $codeSection | Should Match '(?im)^\s*PrerequisiteActionsPage\.Values\[2\]\s*:=\s*False\s*;'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?PrerequisiteActionsPage\.Values\[0\].*?InstallPythonPrerequisite'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?PrerequisiteActionsPage\.Values\[1\].*?InstallNodePrerequisite'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?PrerequisiteActionsPage\.Values\[2\].*?InstallDockerPrerequisite'
    }

    It "stops on the prerequisite report before installing anything when selected hosts are unresolved" {
        $codeSection | Should Match '(?im)^\s*PrerequisiteManualBlockers\s*:\s*String\s*;'
        $codeSection | Should Match "(?is)WizardIsComponentSelected\(\s*'claude'\s*\).*?AppendManualPrerequisiteBlocker\(CustomMessage\('PrereqClaudeMissing'\)\)"
        $codeSection | Should Match "(?is)WizardIsComponentSelected\(\s*'chatbridge'\s*\).*?AppendPrerequisiteBlocker\(CustomMessage\('PrereqNodeMissing'\)\)"
        $codeSection | Should Match "(?is)WizardIsComponentSelected\(\s*'chatbridge'\s*\).*?AppendManualPrerequisiteBlocker\(CustomMessage\('PrereqBrowserMissing'\)\)"

        $nextFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+NextButtonClick.*?(?=function\s+UpdateReadyMemo)'
        ).Value
        $reportGate = [regex]::Match(
            $nextFunction,
            '(?is)if\s+CurPageID\s*=\s*PrerequisitesPage\.ID\s+then.*?(?=if\s+CurPageID\s*=\s*PrerequisiteActionsPage\.ID)'
        ).Value
        $reportGate | Should Match '(?is)PrerequisiteManualBlockers\s*<>\s*''''.*?Result\s*:=\s*False\s*;.*?Exit\s*;'
        $reportGate | Should Not Match '(?i)Install(?:Python|Node|Docker)Prerequisite'
        $reportGate | Should Not Match "(?i)PrereqNodeMissing.*?PrerequisiteManualBlockers"
    }

    It "locks and preserves one complete acquisition plan until postflight" {
        $nextFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+NextButtonClick.*?(?=function\s+UpdateReadyMemo)'
        ).Value
        $actionGate = [regex]::Match(
            $nextFunction,
            '(?is)if\s+CurPageID\s*=\s*PrerequisiteActionsPage\.ID\s+then.*?(?=if\s+CurPageID\s*=\s*RuntimeDirsPage\.ID)'
        ).Value
        $actionGate | Should Match '(?is)DependencyRestartRequired\s+then\s+begin.*?Exit\s*;\s+end\s*;.*?BeginPrerequisiteCheck.*?RunPrerequisiteChecks\s*;.*?finally\s+EndPrerequisiteCheck\s*;.*?PrerequisiteManualBlockers\s*<>\s*''''.*?Exit\s*;.*?not\s+PythonPrerequisitesOK.*?PrerequisiteActionsPage\.Values\[0\].*?NodeVersionOK.*?PrerequisiteActionsPage\.Values\[1\].*?Exit\s*;.*?InstallSelectedPrerequisites'

        $curPageChanged = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+CurPageChanged.*?(?=function\s+ShouldSkipPage)'
        ).Value
        $curPageChanged | Should Not Match '(?i)\bResult\s*:='

        $installFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallSelectedPrerequisites.*?(?=function\s+NeedRestart)'
        ).Value
        $pythonInstall = $installFunction.IndexOf('InstallPythonPrerequisite', [StringComparison]::OrdinalIgnoreCase)
        $nodeInstall = $installFunction.IndexOf('InstallNodePrerequisite', [StringComparison]::OrdinalIgnoreCase)
        $dockerInstall = $installFunction.IndexOf('InstallDockerPrerequisite', [StringComparison]::OrdinalIgnoreCase)
        $batchStart = $installFunction.IndexOf('BeginPrerequisiteBatch', [StringComparison]::OrdinalIgnoreCase)
        $batchEnd = $installFunction.IndexOf('EndPrerequisiteBatch', [StringComparison]::OrdinalIgnoreCase)
        ($batchStart -ge 0 -and $batchStart -lt $pythonInstall) | Should Be $true
        ($batchEnd -gt $dockerInstall) | Should Be $true
        $installFunction | Should Not Match '(?im)PrerequisiteActionsPage\.Values\[[0-2]\]\s*:=\s*False\s*;'
        ($pythonInstall -lt $nodeInstall -and $nodeInstall -lt $dockerInstall) | Should Be $true
        $installFunction | Should Match '(?is)if\s+InstallPythonSelected\s+then.*?if\s+not\s+InstallPythonPrerequisite\s+then.*?Result\s*:=\s*False\s*;\s+Exit\s*;.*?if\s+InstallNodeSelected\s+then.*?if\s+not\s+InstallNodePrerequisite\s+then.*?Result\s*:=\s*False\s*;\s+Exit\s*;.*?if\s+InstallDockerSelected'
        $installFunction | Should Match '(?is)if\s+\(not\s+Result\).*?PrerequisiteActionsPage\.Values\[0\].*?InstallPythonSelected.*?PrerequisiteActionsPage\.Values\[1\].*?InstallNodeSelected.*?PrerequisiteActionsPage\.Values\[2\].*?InstallDockerSelected.*?PrerequisiteAcquisitionFailed\s*:=\s*True'

        $restartNotice = $actionGate.IndexOf('if DependencyRestartRequired then', [StringComparison]::OrdinalIgnoreCase)
        $postflightGate = $actionGate.IndexOf("if PrerequisiteBlockers <> '' then", [StringComparison]::OrdinalIgnoreCase)
        $acquisitionResult = $actionGate.IndexOf('if not AcquisitionSucceeded then', [StringComparison]::OrdinalIgnoreCase)
        ($restartNotice -ge 0 -and $restartNotice -lt $acquisitionResult) | Should Be $true
        ($acquisitionResult -ge 0 -and $acquisitionResult -lt $postflightGate) | Should Be $true
        $actionGate | Should Match '(?is)AcquisitionSucceeded\s*:=\s*InstallSelectedPrerequisites\s*;.*?if\s+DependencyRestartRequired\s+then\s+begin.*?Result\s*:=\s*False\s*;\s+Exit\s*;\s+end\s*;\s+if\s+not\s+AcquisitionSucceeded\s+then.*?Exit\s*;.*?if\s+PrerequisiteBlockers'

        $pythonFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallPythonPrerequisite.*?(?=function\s+InstallDockerPrerequisite)'
        ).Value
        $pythonFunction | Should Match '(?is)IsSuccessfulInstallerExitCode\(ResultCode\).*?if\s+DependencyRestartRequired\s+then\s+begin\s+Result\s*:=\s*True\s*;\s+Exit\s*;\s+end\s*;\s+ProbePython'
    }

    It "keeps one dedicated progress page visible for the complete selected batch" {
        $codeSection | Should Match '(?im)^\s*DependencyInstallPage\s*:\s*TOutputMarqueeProgressWizardPage\s*;'
        $codeSection | Should Match '(?i)CreateOutputMarqueeProgressPage\s*\('
        $runner = [regex]::Match(
            $codeSection,
            '(?is)function\s+ExecutePrerequisiteInstaller.*?(?=function\s+InstallPythonPrerequisite)'
        ).Value
        $runner | Should Match '(?is)StandaloneProgress\s*:=\s*not\s+PrerequisiteBatchActive.*?if\s+StandaloneProgress\s+then.*?DependencyInstallPage\.Show\s*;.*?DependencyInstallPage\.Animate\s*;.*?Exec\s*\(.*?ewWaitUntilTerminated'
        $runner | Should Match '(?is)finally\s+if\s+StandaloneProgress\s+then\s+DependencyInstallPage\.Hide\s*;'
        $runner | Should Not Match '(?i)TerminateProcess\s*\('
        $codeSection | Should Match '(?is)procedure\s+BeginPrerequisiteBatch.*?PrerequisiteBatchActive\s*:=\s*True.*?DependencyInstallPage\.Show\s*;.*?DependencyInstallPage\.Animate\s*;'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?BeginPrerequisiteBatch.*?InstallPythonPrerequisite.*?InstallNodePrerequisite.*?InstallDockerPrerequisite.*?finally.*?EndPrerequisiteBatch'
        $codeSection | Should Match '(?is)function\s+InstallPythonPrerequisite.*?ExecutePrerequisiteInstaller\s*\('
        $codeSection | Should Match '(?is)function\s+InstallNodePrerequisite.*?ExecutePrerequisiteInstaller\s*\('
        $codeSection | Should Match '(?is)function\s+InstallDockerPrerequisite.*?ExecutePrerequisiteInstaller\s*\('
    }

    It "locks prerequisite selection and navigation until detection completes" {
        $codeSection | Should Match '(?im)^\s*PrerequisiteOperationBusy\s*:\s*Boolean\s*;'
        $controls = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+SetPrerequisiteActionControlsEnabled.*?(?=procedure\s+BeginPrerequisiteCheck)'
        ).Value
        $controls | Should Match '(?i)PrerequisiteActionsPage\.CheckListBox\.Enabled\s*:=\s*Enabled'
        $controls | Should Match '(?i)RecheckPrerequisitesButton\.Enabled\s*:=\s*Enabled'
        $controls | Should Match '(?i)WizardForm\.BackButton\.Enabled\s*:=\s*Enabled'
        $controls | Should Match '(?is)if\s+not\s+Enabled\s+then\s+WizardForm\.NextButton\.Enabled\s*:=\s*False'

        $beginCheck = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+BeginPrerequisiteCheck.*?(?=procedure\s+EndPrerequisiteCheck)'
        ).Value
        $beginCheck | Should Match '(?is)PrerequisiteOperationBusy\s*:=\s*True.*?SetPrerequisiteActionControlsEnabled\(False\).*?PrerequisitesPage\.RichEditViewer\.Lines\.Text\s*:=.*?PrereqProgressCheckingLocked.*?PrerequisiteActionStatusLabel\.Caption\s*:=.*?PrereqProgressCheckingLocked'
        $endCheck = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+EndPrerequisiteCheck.*?(?=procedure\s+BeginPrerequisiteBatch)'
        ).Value
        $endCheck | Should Match '(?is)PrerequisiteOperationBusy\s*:=\s*False.*?SetPrerequisiteActionControlsEnabled\(True\)'
        $endCheck | Should Not Match '(?i)DependencyInstallPage\.(?:Show|Hide)'

        $navigation = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+UpdatePrerequisiteActionNavigation.*?(?=procedure\s+UpdatePrerequisiteActionState)'
        ).Value
        $navigation | Should Match '(?is)if\s+PrerequisiteOperationBusy\s+then.*?WizardForm\.NextButton\.Enabled\s*:=\s*False.*?Exit'
        $codeSection | Should Match '(?is)procedure\s+PrerequisiteOptionClick.*?if\s+PrerequisiteOperationBusy\s+then\s+Exit'
        $curPageChanged = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+CurPageChanged.*?(?=function\s+ShouldSkipPage)'
        ).Value
        $curPageChanged | Should Match '(?is)^.*?if\s+PrerequisiteOperationBusy\s+then\s+begin.*?Exit\s*;.*?end\s*;.*?BeginPrerequisiteCheck.*?RunPrerequisiteChecks.*?finally\s+EndPrerequisiteCheck'
        $uiSmokeSource = Get-Content -LiteralPath $installerUiSmokePath -Raw -Encoding UTF8
        $uiSmokeSource | Should Match 'ExpectSetupP002Fix01Flow'
        $uiSmokeSource | Should Match 'SETUP_P0_02_FIX_01_CHECK_LOCK_OBSERVED'
        $uiSmokeSource | Should Match 'SETUP_P0_02_FIX_01_BUSY_PAGE_VISIBLE'
        $uiSmokeSource | Should Match 'SETUP_P0_02_FIX_01_FAST_CHECK_COMPLETED'
        $uiSmokeSource | Should Match 'SETUP_P0_02_FIX_01_BATCH_STABLE'
    }

    It "bounds external Python and Node detection processes" {
        $pythonCandidate = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+CheckPythonCandidate.*?(?=procedure\s+CheckPythonRegistryRoot)'
        ).Value
        $pythonCandidate | Should Match '(?is)if\s+PythonVersionOK\s+then\s+Exit'
        $pythonCandidate | Should Match '(?is)RunProbeWithTimeout\(.*?sys\.version_info.*?,\s*5000\s*\)'
        $pythonCandidate | Should Match '(?is)RunProbeWithTimeout\(.*?import\s+mcp,\s*qdrant_client,\s*onnxruntime,\s*fastembed.*?,\s*30000\s*\)'
        $pythonCandidate | Should Not Match '(?i)\bRunProbe\s*\('

        $nodeCandidate = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+CheckNodeCandidate.*?(?=procedure\s+ProbeNode)'
        ).Value
        $nodeCandidate | Should Match '(?is)RunProbeWithTimeout\(.*?process\.versions\.node.*?,\s*5000\s*\)'
        $nodeCandidate | Should Not Match '(?i)\bRunProbe\s*\('
    }

    It "uses pinned official HTTPS packages and manual download pages" {
        $source | Should Match ([regex]::Escape('https://www.python.org/ftp/python/3.13.14/python-3.13.14-amd64.exe'))
        $source | Should Match 'c54d9b9bbb8a36e6489363ddd01139707fd781d72f1f9e90c7ec65d0061368e0'
        $source | Should Match ([regex]::Escape('https://aka.ms/vs/18/release/14.51.36247/VC_redist.x64.exe'))
        $source | Should Match '843068991daaa1f73ad9f6239bce4d0f6a07a51f18c37ea2a867e9beca71295c'
        $source | Should Match ([regex]::Escape('https://learn.microsoft.com/cpp/windows/latest-supported-vc-redist'))
        $source | Should Match ([regex]::Escape('https://nodejs.org/dist/v24.18.0/node-v24.18.0-x64.msi'))
        $source | Should Match 'e30cd4ca15529583afe0efc978f1ae3ab3a93c2400c222d0752d17900552ebb3'
        $source | Should Match ([regex]::Escape('https://desktop.docker.com/win/main/amd64/233772/Docker%20Desktop%20Installer.exe'))
        $source | Should Match 'a5b5837542f2f57fadbb09db90a60c84f8efc0a65f8d6dcd2e5b9fca3a2b87e6'
        $source | Should Match ([regex]::Escape('https://www.python.org/downloads/windows/'))
        $source | Should Match ([regex]::Escape('https://nodejs.org/en/download'))
        $source | Should Match ([regex]::Escape('https://docs.docker.com/desktop/setup/install/windows-install/'))
        $codeSection | Should Match '(?i)CreateDownloadPage'
        $codeSection | Should Match '(?i)DependencyDownloadPage\.Add\(Url,\s*FileName,\s*Sha256\)'
        $codeSection | Should Match '(?is)DownloadVerifiedInstaller\(\s*PythonInstallerUrl,\s*PythonInstallerFileName,\s*PythonInstallerSha256,'
        $codeSection | Should Match '(?is)DownloadVerifiedInstaller\(\s*VCRuntimeInstallerUrl,\s*VCRuntimeInstallerFileName,\s*VCRuntimeInstallerSha256,'
        $codeSection | Should Match '(?is)DownloadVerifiedInstaller\(\s*NodeInstallerUrl,\s*NodeInstallerFileName,\s*NodeInstallerSha256,'
        $codeSection | Should Match '(?is)DownloadVerifiedInstaller\(\s*DockerInstallerUrl,\s*DockerInstallerFileName,\s*DockerInstallerSha256,'
    }

    It "installs the required Visual C++ runtime and logs individual Python imports" {
        (Test-Path -LiteralPath $pythonRuntimeProbePath -PathType Leaf) | Should Be $true
        $probeSource = Get-Content -LiteralPath $pythonRuntimeProbePath -Raw -Encoding UTF8
        foreach ($moduleName in @("mcp", "qdrant_client", "onnxruntime", "fastembed")) {
            $probeSource | Should Match ([regex]::Escape('"' + $moduleName + '"'))
        }
        $probeSource | Should Match 'site\.ENABLE_USER_SITE'
        $probeSource | Should Match 'site\.getusersitepackages'
        $probeSource | Should Match 'traceback\.print_exc'
        $probeSource | Should Match 'buffering=1'
        $probeSource | Should Match 'status=starting'
        $probeSource | Should Match 'log\.flush\(\)'

        $codeSection | Should Match '(?is)procedure\s+CheckVCRuntimeRegistryRoot.*?VC\\Runtimes\\x64.*?procedure\s+ProbeVCRuntime'
        $codeSection | Should Match '(?is)function\s+InstallVCRuntimePrerequisite\(ForceInstall:\s*Boolean\).*?VCRuntimeOK\s+and\s+\(not\s+ForceInstall\).*?DownloadVerifiedInstaller.*?ExecutePrerequisiteInstaller.*?True,\s*ResultCode.*?ProbeVCRuntime'
        $pythonFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallPythonPrerequisite.*?(?=function\s+InstallNodePrerequisite)'
        ).Value
        $saveInterpreter = $pythonFunction.IndexOf(
            'PythonPathForRuntime := DetectedPythonPath',
            [StringComparison]::OrdinalIgnoreCase
        )
        $installRuntime = $pythonFunction.IndexOf(
            'InstallVCRuntimePrerequisite(False)',
            [StringComparison]::OrdinalIgnoreCase
        )
        $runRuntimeProbe = $pythonFunction.IndexOf(
            'RunPythonRuntimeProbe(PythonPathForRuntime, LogPath)',
            [StringComparison]::OrdinalIgnoreCase
        )
        $pipMatch = [regex]::Match(
            $pythonFunction,
            '(?is)ExecutePrerequisiteInstaller\(\s*PythonPathForRuntime,'
        )
        $pipMatch.Success | Should Be $true
        $pipWithInterpreter = $pipMatch.Index
        ($saveInterpreter -ge 0 -and $saveInterpreter -lt $installRuntime) | Should Be $true
        ($installRuntime -lt $runRuntimeProbe -and $runRuntimeProbe -lt $pipWithInterpreter) | Should Be $true
        $pythonFunction | Should Match '(?is)InstallVCRuntimePrerequisite\(True\).*?python-runtime-repair-probe.*?RunPythonRuntimeProbe\(PythonPathForRuntime,\s*LogPath\)'
        $pythonFunction | Should Match '(?is)\(not\s+PythonRuntimeOK\)\s+and\s+\(not\s+VCRuntimeRepairAttempted\).*?VCRuntimeRepairAttempted\s*:=\s*True.*?InstallVCRuntimePrerequisite\(True\)'
        $codeSection | Should Match '(?is)CheckPythonCandidate.*?import\s+mcp,\s*qdrant_client,\s*onnxruntime,\s*fastembed'
        $codeSection | Should Match '(?is)function\s+RunPythonRuntimeProbe.*?python-runtime-probe\.py.*?RunProbeWithTimeout'

        $python = Get-Command python.exe -ErrorAction Stop | Select-Object -First 1
        $testId = [guid]::NewGuid().ToString("N")
        $successLog = Join-Path $env:TEMP "plwc-python-probe-success-$testId.log"
        $failureLog = Join-Path $env:TEMP "plwc-python-probe-failure-$testId.log"

        & $python.Source $pythonRuntimeProbePath $successLog json pathlib
        $LASTEXITCODE | Should Be 0
        (Get-Content -LiteralPath $successLog -Raw) | Should Match 'runtime_probe=ok'

        & $python.Source $pythonRuntimeProbePath $failureLog plwc_missing_test_module
        $LASTEXITCODE | Should Be 1
        $failureText = Get-Content -LiteralPath $failureLog -Raw
        $failureText | Should Match 'import=plwc_missing_test_module status=failed'
        $failureText | Should Match 'failed_modules=plwc_missing_test_module'
        $failureText | Should Match 'Traceback'
    }

    It "falls back to Windows curl while retaining SHA256 verification and useful DNS diagnostics" {
        $findCurlFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+FindWindowsCurl.*?(?=function\s+DownloadVerifiedInstallerWithCurl)'
        ).Value
        $systemCurl = $findCurlFunction.IndexOf("ExpandConstant('{sysnative}\curl.exe')", [StringComparison]::OrdinalIgnoreCase)
        $pathCurl = $findCurlFunction.IndexOf("FindExecutable('curl.exe')", [StringComparison]::OrdinalIgnoreCase)
        ($systemCurl -ge 0 -and $systemCurl -lt $pathCurl) | Should Be $true
        $curlFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+DownloadVerifiedInstallerWithCurl.*?(?=function\s+DownloadVerifiedInstaller\()'
        ).Value
        $curlFunction | Should Match '(?is)--fail.*?--location.*?--retry\s+2.*?--output'
        $curlFunction | Should Match '(?is)CompareText\(GetSHA256OfFile\(DownloadedPath\),\s*Sha256\)'
        $codeSection | Should Match "(?i)Pos\(\s*'12007'\s*,\s*PrimaryError\s*\)"
        $customMessageSection | Should Match '(?im)^\s*german\.PrereqDownloadDnsHint=.*\bDNS\b'
        $customMessageSection | Should Match '(?im)^\s*english\.PrereqDownloadRetryHint=.*click Next to retry'

        $downloadFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+DownloadVerifiedInstaller\(.*?(?=function\s+IsSuccessfulInstallerExitCode)'
        ).Value
        $abortExit = $downloadFunction.IndexOf('if Result or AbortedByUser then', [StringComparison]::OrdinalIgnoreCase)
        $fallbackStart = $downloadFunction.IndexOf('if DownloadVerifiedInstallerWithCurl', [StringComparison]::OrdinalIgnoreCase)
        ($abortExit -ge 0 -and $abortExit -lt $fallbackStart) | Should Be $true
        $downloadFunction | Should Match '(?is)if\s+Result\s+or\s+AbortedByUser\s+then\s+Exit\s*;.*?if\s+DownloadVerifiedInstallerWithCurl'
        [regex]::Matches($downloadFunction, '(?i)\bMsgBox\s*\(').Count | Should Be 1
    }

    It "installs Node LTS only after explicit Bridge opt-in and administrator approval" {
        $nodeFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallNodePrerequisite.*?(?=function\s+InstallDockerPrerequisite)'
        ).Value
        $nodeFunction | Should Match '(?i)NodeInstallerUrl'
        $nodeFunction | Should Match '(?i)msiexec\.exe'
        $nodeFunction | Should Match '(?i)/i\s+"''\s*\+\s*InstallerPath'
        $nodeFunction | Should Match '(?i)/passive\s+/norestart\s+ALLUSERS=1'
        $nodeFunction | Should Match '(?i)/L\*v\s+"''\s*\+\s*LogPath'
        $nodeFunction | Should Match '(?is)ExecutePrerequisiteInstaller\(.*?True,\s*ResultCode'
        $nodeFunction | Should Match '(?is)IsSuccessfulInstallerExitCode\(ResultCode\).*?DependencyRestartRequired.*?ProbeNode'
        $codeSection | Should Match '(?is)ItemEnabled\[1\].*?WizardIsComponentSelected\(\s*''chatbridge''\s*\).*?not\s+NodeVersionOK'
        $runner = [regex]::Match(
            $codeSection,
            '(?is)function\s+ExecutePrerequisiteInstaller\(.*?(?=function\s+InstallPythonPrerequisite)'
        ).Value
        $runner | Should Match '(?is)if\s+Elevated\s+then\s+Result\s*:=\s*ShellExec\(\s*''runas'''
    }

    It "keeps Next short while status text explains selection and retry states" {
        $navigationFunction = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+UpdatePrerequisiteActionNavigation.*?(?=procedure\s+UpdatePrerequisiteActionState)'
        ).Value
        $navigationFunction | Should Match '(?is)RequiredPlanComplete.*?PrerequisiteActionsPage\.Values\[0\].*?PrerequisiteActionsPage\.Values\[1\]'
        $navigationFunction | Should Match '(?i)WizardForm\.NextButton\.Enabled\s*:=\s*RequiredPlanComplete'
        $navigationFunction | Should Match '(?i)WizardForm\.NextButton\.Caption\s*:=\s*DefaultNextButtonCaption'
        $navigationFunction | Should Not Match '(?i)WizardForm\.NextButton\.Caption\s*:=\s*CustomMessage'
        $navigationFunction | Should Match "(?i)PrerequisiteActionStatusLabel\.Caption\s*:=\s*CustomMessage\('ActionSelectRequired'\)"
        $navigationFunction | Should Match "(?i)PrerequisiteActionStatusLabel\.Caption\s*:=\s*CustomMessage\('ActionRetrySelected'\)"
        $navigationFunction | Should Match "(?i)PrerequisiteActionStatusLabel\.Caption\s*:=\s*CustomMessage\('ActionInstallSelected'\)"
        $codeSection | Should Match '(?is)RecheckPrerequisitesButtonClick.*?RunPrerequisiteChecks.*?UpdatePrerequisiteActionState'
        $codeSection | Should Match '(?i)PrerequisiteActionsPage\.CheckListBox\.OnClickCheck\s*:='
        $codeSection | Should Not Match '(?i)PrerequisiteActionsPage\.CheckListBox\.OnClick\s*:='
        $codeSection | Should Match '(?i)DefaultNextButtonCaption\s*:=\s*SetupMessage\(msgButtonNext\)'
        $codeSection | Should Not Match '(?i)DefaultNextButtonCaption\s*:=\s*WizardForm\.NextButton\.Caption'
        $curPageChanged = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+CurPageChanged.*?(?=function\s+ShouldSkipPage)'
        ).Value
        $curPageChanged | Should Not Match '(?i)NextButton\.Caption\s*:='
        $curPageChanged | Should Not Match '(?is)CurPageID\s*<>\s*PrerequisiteActionsPage\.ID.*?NextButton\.Enabled\s*:='
    }

    It "shows each versioned download and runtime storage class separately" {
        (Test-Path -LiteralPath $prerequisiteSizesPath -PathType Leaf) | Should Be $true
        $sizes = Get-Content -LiteralPath $prerequisiteSizesPath -Raw -Encoding UTF8
        foreach ($name in @(
            "PlwcPayloadMiB",
            "PythonDownloadMiB",
            "PythonDiskMinMiB",
            "PythonDiskMaxMiB",
            "QdrantModelMinMiB",
            "QdrantModelMaxMiB",
            "NodeDownloadMiB",
            "DockerDownloadMiB",
            "DockerDiskMinMiB",
            "SizeEstimateDate"
        )) {
            $sizes | Should Match ("(?im)^\s*#define\s+{0}\s+" -f [regex]::Escape($name))
        }
        $sizes | Should Match '(?is)#ifndef\s+PlwcPayloadMiB.*?#define\s+PlwcPayloadMiB'
        $source | Should Match '(?im)^\s*#include\s+"assets\\prerequisite-sizes\.iss"\s*$'
        $codeSection | Should Match '(?im)^\s*PrerequisiteSizeMemo\s*:\s*TNewMemo\s*;'
        $codeSection | Should Match '(?is)BuildPrerequisiteSizeText.*?SizePlwc.*?SizePython.*?SizeNode.*?SizeDocker.*?SizeWslImages.*?SizeFirstUse.*?SizeSelected.*?SizeSelectedVariable.*?SizeLogLocation'
        $codeSection | Should Match '(?is)SelectedPrerequisiteDownloadMiB.*?Values\[0\].*?PythonDownloadMiB.*?Values\[1\].*?NodeDownloadMiB.*?Values\[2\].*?DockerDownloadMiB'
        $customMessageSection | Should Match '(?im)^\s*english\.SizePlwc=PLwC payload:.*included in Setup.*installed'
        $customMessageSection | Should Match '(?im)^\s*german\.SizePlwc=PLwC-Payload:.*im Setup enthalten.*installiert'
        $customMessageSection | Should Match '(?im)^\s*english\.SizeWslImages=WSL runtime and Docker image storage:'
        $customMessageSection | Should Match '(?im)^\s*english\.SizeFirstUse=Variable first use:'
        $buildSource = Get-Content -LiteralPath $buildScript -Raw
        $buildSource | Should Match '(?is)payloadSizeBytes.*?\$_\["size"\].*?Measure-Object\s+-Sum'
        $buildSource | Should Match '(?is)payloadSizeMiB.*?Math\]::Ceiling'
        $buildSource | Should Match '/DPlwcPayloadMiB=\$plwcPayloadMiB'
        $guide = Get-Content -LiteralPath $windowsInstallerGuidePath -Raw -Encoding UTF8
        $guide | Should Match '(?i)PLwC payload.*calculated from the staged payload'
        $guide | Should Match '(?i)WSL runtime and Docker images.*unknown'
        $guide | Should Match '(?i)First-use model cache.*additional model caches are unknown'
    }

    It "renders unknown variable sizes explicitly instead of zero or null" {
        $customMessageSection | Should Match '(?im)^\s*english\.SizeUnknown=unknown\s*$'
        $customMessageSection | Should Match '(?im)^\s*german\.SizeUnknown=unbekannt\s*$'
        foreach ($variableMessage in @(
            "SizeWslImages",
            "SizeFirstUse",
            "SizeSelectedVariable"
        )) {
            $codeSection | Should Match (
                "(?is)BuildPrerequisiteSizeText.*?{0}.*?SizeUnknown" -f $variableMessage
            )
            $customMessageSection | Should Not Match (
                "(?im)^\s*(?:english|german)\.{0}=.*(?:null|\b0\s*(?:MB|GB))" -f $variableMessage
            )
        }
        $uiSmokeSource = Get-Content -LiteralPath $installerUiSmokePath -Raw -Encoding UTF8
        $uiSmokeSource | Should Match 'ExpectSetupP101SizeBreakdown'
        $uiSmokeSource | Should Match 'SETUP_P1_01_SIZE_BREAKDOWN_VISIBLE'
    }

    It "records actionable diagnostics for Python Node and Docker failures" {
        $codeSection | Should Match '(?is)function\s+GetPrerequisiteLogRoot.*?GetDataRoot\s*\+\s*''\\logs\\setup\\prerequisites'''
        $codeSection | Should Match '(?is)function\s+CreatePrerequisiteLogPath.*?EnsureDirectory\(GetPrerequisiteLogRoot\)'
        $codeSection | Should Match '(?is)function\s+CreatePrerequisiteLogPath.*?GetDateTimeString\(''yyyymmdd-hhnnss'',\s*#0,\s*#0\)'
        $codeSection | Should Not Match 'GetDateTimeString\(''yyyymmdd-hhnnss'',\s*'''',\s*''''\)'
        $codeSection | Should Match '(?is)procedure\s+ShowPrerequisiteFailure.*?PrereqFailureComponent.*?PrereqFailureExitCode.*?PrereqFailureLog'
        $codeSection | Should Match '(?is)PrerequisiteExitCodeHint.*?ResultCode\s*=\s*1223.*?ResultCode\s*=\s*1602.*?PrereqFailureUacCancelled'
        foreach ($exitCode in @(1603, 1618)) {
            $codeSection | Should Match ("(?m)^\s*{0}(?:,|:)" -f $exitCode)
        }

        $pythonFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallPythonPrerequisite.*?(?=function\s+InstallNodePrerequisite)'
        ).Value
        $pythonFunction | Should Match '(?i)/log\s+"''\s*\+\s*LogPath'
        $pythonFunction | Should Match '(?i)--log\s+"''\s*\+\s*LogPath'
        $pythonFunction | Should Match '(?is)AppendPrerequisiteStatusLog.*?ShowPrerequisiteFailure'

        $nodeFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallNodePrerequisite.*?(?=function\s+InstallDockerPrerequisite)'
        ).Value
        $nodeFunction | Should Match '(?i)/L\*v\s+"''\s*\+\s*LogPath'
        $nodeFunction | Should Match '(?is)AppendPrerequisiteStatusLog.*?ShowPrerequisiteFailure'

        $dockerFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallDockerPrerequisite.*?(?=function\s+SelectedPrerequisiteDownloadMiB)'
        ).Value
        $dockerFunction | Should Match '(?is)AppendPrerequisiteStatusLog.*?ShowPrerequisiteFailure'
        $codeSection | Should Match '(?is)function\s+GetInstallerDiagnosticPath.*?installer-diagnostic\.log'
        $codeSection | Should Match '(?is)procedure\s+ReportPrerequisiteException.*?GetInstallerDiagnosticPath'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?PrereqPhaseFinalCheck.*?RunPrerequisiteChecks'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?except.*?OriginalExceptionPhase\s*:=\s*CurrentPrerequisitePhase.*?if\s+not\s+HadException\s+then.*?PrereqPhaseFinalCheck.*?if\s+HadException\s+then.*?CurrentPrerequisitePhase\s*:=\s*OriginalExceptionPhase'
        foreach ($phase in @(
            "PrereqPhasePythonDownload",
            "PrereqPhasePythonPrepare",
            "PrereqPhasePythonInstall",
            "PrereqPhasePythonModules",
            "PrereqPhaseNodeDownload",
            "PrereqPhaseNodePrepare",
            "PrereqPhaseNodeInstall",
            "PrereqPhaseDockerDownload",
            "PrereqPhaseDockerPrepare",
            "PrereqPhaseDockerInstall"
        )) {
            $codeSection | Should Match ([regex]::Escape($phase))
        }
    }

    It "installs the fully hash-locked PLwC runtime for the current user and rechecks" {
        (Test-Path -LiteralPath $mcpLockPath -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath $runtimeRequirementsPath -PathType Leaf) | Should Be $true
        $mcpLock = Get-Content -LiteralPath $mcpLockPath -Raw
        $mcpLock | Should Match '(?m)^mcp==1\.27\.0\s+\\$'
        $mcpLock | Should Match '(?m)^fastembed==0\.8\.0\s+\\$'
        $mcpLock | Should Match '(?m)^qdrant-client==1\.18\.0\s+\\$'
        $mcpLock | Should Not Match '(?i)https?://|index-url|Users\\|AppData'

        $requirements = @(
            [regex]::Split($mcpLock, '(?m)(?=^[A-Za-z0-9_.-]+==)') |
                Where-Object { $_.Trim() -ne '' }
        )
        ($requirements.Count -gt 1) | Should Be $true
        foreach ($requirement in $requirements) {
            $requirement | Should Match '(?m)^[A-Za-z0-9_.-]+==[^\s\\]+\s+\\$'
            $requirement | Should Match '--hash=sha256:[0-9a-f]{64}'
        }

        $source | Should Match '(?im)^\s*Source:\s*"assets\\mcp-runtime-lock\.txt";\s*Flags:\s*dontcopy\s*$'
        $codeSection | Should Match "(?i)ExtractTemporaryFile\('mcp-runtime-lock\.txt'\)"
        $pythonInstallFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallPythonPrerequisite.*?(?=function\s+InstallDockerPrerequisite)'
        ).Value
        $pythonInstallFunction | Should Match '(?i)DetectedPythonPath'
        $pythonInstallFunction | Should Match '(?i)--user'
        $pythonInstallFunction | Should Match '(?i)--only-binary=:all:'
        $pythonInstallFunction | Should Match '(?i)--require-hashes'
        $pythonInstallFunction | Should Match '(?i)-r\s+"''\s*\+\s*LockPath\s*\+\s*''"'
        $codeSection | Should Not Match '(?i)pip\s+install[^\r\n]*mcp=='
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?RunPrerequisiteChecks\s*;'
        $codeSection | Should Match '(?is)function\s+PrepareToInstall.*?RunPrerequisiteChecks\s*;'
    }

    It "detects and installs Docker Desktop in per-user mode" {
        $codeSection | Should Match ([regex]::Escape("{localappdata}\Programs\DockerDesktop\resources\bin\docker.exe"))
        $codeSection | Should Match "(?i)'install --user --quiet --backend=wsl-2 --no-windows-containers'"
        $codeSection | Should Match '(?is)function\s+InstallDockerPrerequisite.*?DockerInstalledBySetup\s*:=\s*True.*?ProbeDocker'
        $codeSection | Should Match '(?is)procedure\s+StartDockerDesktopAfterSetup.*?ExecAsOriginalUser.*?ewNoWait'
        $codeSection | Should Match '(?is)procedure\s+CurStepChanged.*?StartDockerDesktopAfterSetup.*?ConfigureChatBridgeWindowsIntegration'
    }

    It "re-probes actual paths and runtime state after third-party installers" {
        $pythonFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallPythonPrerequisite.*?(?=function\s+InstallNodePrerequisite)'
        ).Value
        $nodeFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallNodePrerequisite.*?(?=function\s+InstallDockerPrerequisite)'
        ).Value
        $dockerFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallDockerPrerequisite.*?(?=function\s+SelectedPrerequisiteDownloadMiB)'
        ).Value

        $pythonFunction | Should Match '(?is)ProbePython\s*;.*?PythonPathForRuntime\s*:=\s*DetectedPythonPath.*?RunPythonRuntimeProbe\(PythonPathForRuntime'
        $nodeFunction | Should Match '(?is)ProbeNode\s*;.*?Result\s*:=\s*NodeVersionOK'
        $dockerFunction | Should Match '(?is)DockerInstalledBySetup\s*:=\s*True\s*;.*?ProbeDocker\s*;'
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?PrereqPhaseFinalCheck.*?RunPrerequisiteChecks'
        foreach ($diagnosticName in @("PythonPath", "NodePath", "DockerCliPath", "DockerDaemonReachable")) {
            $codeSection | Should Match "(?is)SetIniString\(\s*'Diagnostics'\s*,\s*'$diagnosticName'"
        }
    }

    It "does not infer prerequisite consent in silent mode" {
        $codeSection | Should Match '(?is)function\s+InstallSelectedPrerequisites.*?if\s+WizardSilent\s+then\s+Exit'
        $codeSection | Should Not Match '(?is)function\s+PrepareToInstall.*?Install(?:Python|Node|Docker)Prerequisite'
    }

    It "does not accept Docker terms or automatically install unrelated host applications" {
        $source | Should Not Match '(?i)\b(?:winget|choco(?:latey)?|scoop)\b'
        $source | Should Not Match '(?i)--accept-license'
        $codeSection | Should Not Match '(?i)\bInstall(?:Claude|Chrome|Edge|Brave|Browser)Prerequisite\b'
        $runSection | Should Not Match '(?i)(?:python|node|docker|chrome|edge|brave|claude)[^\r\n]*(?:/quiet|/silent|/verysilent|/qn)'
    }

    It "uses the PLwC icon and small wizard image from repository assets" {
        $setupSection | Should Match '(?im)^\s*SetupIconFile\s*=\s*assets\\plwc\.ico\s*$'
        $setupSection | Should Match '(?im)^\s*WizardSmallImageFile\s*=\s*\.\.\\\.\.\\plwc-icon-512\.png\s*$'
        (Test-Path -LiteralPath (Join-Path $assetsRoot "plwc.ico") -PathType Leaf) | Should Be $true
        $wizardImagePath = [IO.Path]::GetFullPath((Join-Path $installerRoot "..\..\plwc-icon-512.png"))
        (Test-Path -LiteralPath $wizardImagePath -PathType Leaf) | Should Be $true
    }

    It "provides English and German languages with localized custom messages" {
        $languageSection | Should Match '(?im)^\s*Name:\s*"english";'
        $languageSection | Should Match '(?im)^\s*Name:\s*"german";'
        $customMessageSection | Should Match '(?im)^\s*english\.[A-Za-z0-9_]+\s*='
        $customMessageSection | Should Match '(?im)^\s*german\.[A-Za-z0-9_]+\s*='

        $englishKeys = @([regex]::Matches($customMessageSection, '(?im)^\s*english\.(?<Key>[A-Za-z0-9_]+)\s*=') | ForEach-Object { $_.Groups["Key"].Value })
        $germanKeys = @([regex]::Matches($customMessageSection, '(?im)^\s*german\.(?<Key>[A-Za-z0-9_]+)\s*=') | ForEach-Object { $_.Groups["Key"].Value })
        ($englishKeys.Count -gt 0) | Should Be $true
        (($englishKeys | Sort-Object) -join "`n") | Should Be (($germanKeys | Sort-Object) -join "`n")
        $customMessageSection | Should Match '(?im)^\s*german\.FieldMemoryThreshold\s*=Speicher-Schreibschwelle:'
        $customMessageSection | Should Match '(?im)^\s*german\.ValueYes\s*=Ja\s*$'
        $customMessageSection | Should Match '(?im)^\s*german\.ValueNo\s*=Nein\s*$'
        $codeSection | Should Match '(?i)LocalizedBoolean\s*\('
    }

    It "always presents an explicit German or English language choice" {
        $setupSection | Should Match '(?im)^\s*ShowLanguageDialog\s*=\s*yes\s*$'
        $setupSection | Should Match '(?im)^\s*UsePreviousLanguage\s*=\s*no\s*$'
        $setupSection | Should Match '(?im)^\s*LanguageDetectionMethod\s*=\s*uilanguage\s*$'
        $languageSection | Should Match '(?im)^\s*Name:\s*"english";'
        $languageSection | Should Match '(?im)^\s*Name:\s*"german";'
    }

    It "installs and opens a localized Getting Started guide before Store distribution" {
        foreach ($path in @($gettingStartedEnglishPath, $gettingStartedGermanPath, $gettingStartedStylesPath)) {
            (Test-Path -LiteralPath $path -PathType Leaf) | Should Be $true
        }

        $englishGuide = Get-Content -LiteralPath $gettingStartedEnglishPath -Raw -Encoding UTF8
        $germanGuide = Get-Content -LiteralPath $gettingStartedGermanPath -Raw -Encoding UTF8
        $guideStyles = Get-Content -LiteralPath $gettingStartedStylesPath -Raw -Encoding UTF8
        foreach ($guide in @($englishGuide, $germanGuide)) {
            $guide | Should Match 'SETUP-P1-04-FIX-02;COMPONENT-PATHS;GATEWAY-ONLY;CLAUDE-MCPB;CODEX-STDIO;ODYSSEUS-STDIO;CHAT-BRIDGE;CONFIGURATION;PROFILE-CREATION;PRIMER;NATURAL-LANGUAGE;COMPILE;REFLECTION;GOVERNOR;DIARY;TRASHCAN;PERSONA-PROMOTION;FORCE;RESTART'
            $guide | Should Match '%APPDATA%\\PLwC\\config\\installer\\installation-summary\.txt'
            $guide | Should Match 'plwc-gateway-1\.0\.0\.mcpb'
            $guide | Should Match 'plwc-gateway\.generated\.toml'
            $guide | Should Match '%USERPROFILE%\\\.codex\\config\.toml'
            $guide | Should Match 'plwc-gateway\.generated\.json'
            $guide | Should Match '(?i)Gateway only|Nur PLwC Gateway'
            $guide | Should Match '(?i)In plain language|Einfach erkl.rt'
            $guide | Should Match '(?i)Use it when|When to use it|Wann verwenden'
            $guide | Should Match '(?i)What changes|Was wird ver.ndert'
            $guide | Should Match '(?i)read-only|rein lesend'
            $guide | Should Match '(?i)does not compile program code|kompiliert keinen Programmcode'
            $guide | Should Match '(?i)active profile|aktive[sn]? Profil'
            $guide | Should Match '(?i)context layer|Kontextschicht'
            $guide | Should Match 'Generate'
            $guide | Should Match 'Insert Bridge Primer'
            $guide | Should Match 'plwc_describe'
            $guide | Should Match 'plwc_status\(scope="first_run"\)'
            $guide | Should Match 'plwc_profile\(operation="compile"'
            $guide | Should Match 'plwc_profile\(operation="scan_tagebuch"\)'
            $guide | Should Match 'plwc_reflection\(operation="write"'
            $guide | Should Match 'plwc_governor\(operation="plan"'
            $guide | Should Match 'plan_type="persona_promotion"'
            $guide | Should Match 'plwc_workspace_operation\(operation="move"'
            $guide | Should Match 'force=true'
            $guide | Should Match 'confirmed=true'
            $guide | Should Match 'insufficient_evidence'
            $guide | Should Match '(?i)semantic|semantisch'
            $guide | Should Match 'Trashcan/'
            $guide | Should Match 'Save &amp; Restart'
            $guide | Should Not Match '(?i)https?://|<script\b'
        }
        $englishGuide | Should Match '(?i)normal language'
        $englishGuide | Should Match '(?i)inserted.*not sent.*send it manually'
        $englishGuide | Should Match 'Load unpacked'
        $englishGuide | Should Match '(?i)native MCP clients receive the tool schemas directly'
        $germanGuide | Should Match '(?i)normale Sprache|normaler Sprache'
        $germanGuide | Should Match '(?i)eingef.gt.*nicht.*abgeschickt.*manuell'
        $germanGuide | Should Match 'Entpackte Erweiterung laden'
        $germanGuide | Should Match '(?i)native MCP-Clients erhalten die Werkzeugschemas direkt'
        $guideStyles | Should Match '(?i)@media\s*\(max-width:\s*720px\)'
        $guideStyles | Should Not Match '(?i)https?://|url\('

        $iconSection = Get-InnoSection -Source $source -Name "Icons"
        $runSection | Should Match '(?im)^Filename:\s*"\{code:GetConfigurationPythonPath\}";.*GetGettingStartedArguments.*RunOpenGettingStarted.*postinstall.*skipifsilent(?!.*unchecked)'
        $runSection | Should Match '(?im)^Filename:\s*"\{sys\}\\notepad\.exe";.*RunOpenSummary.*unchecked'
        $iconSection | Should Match '(?im)^Name:\s*"\{group\}\\\{cm:IconGettingStarted\}";\s*Filename:\s*"\{code:GetConfigurationPythonPath\}";.*GetGettingStartedArguments'
        $codeSection | Should Match '(?is)function\s+GetGettingStartedPath.*?ActiveLanguage.*?getting-started-de\.html.*?getting-started-en\.html'
        $codeSection | Should Match '(?is)function\s+GettingStartedExists.*?FileExists\(GetGettingStartedPath'
        $customMessageSection | Should Match '(?im)^english\.RunOpenGettingStarted=Open PLwC Getting Started$'
        $customMessageSection | Should Match '(?im)^german\.RunOpenGettingStarted=Erste Schritte mit PLwC .ffnen$'

        $buildSource = Get-Content -LiteralPath $buildScript -Raw -Encoding UTF8
        foreach ($file in @("getting-started-en.html", "getting-started-de.html", "getting-started.css")) {
            $buildSource | Should Match ([regex]::Escape($file))
        }
        $buildSource | Should Match 'common\\docs'
    }

    It "uses an unmistakable installer revision in the UI and artifact name" {
        $source | Should Match '(?im)^\s*#define\s+InstallerRevision\s+"installer-r22"\s*$'
        $setupSection | Should Match '(?im)^\s*AppVerName=.*\{#InstallerRevision\}\)\s*$'
        $setupSection | Should Match '(?im)^\s*OutputBaseFilename=PLwC-Setup-\{#AppVersion\}-\{#InstallerRevision\}\s*$'
    }

    It "installs one client-independent local configuration UI" {
        foreach ($file in $configurationFiles) {
            (Test-Path -LiteralPath (Join-Path $configurationRoot $file) -PathType Leaf) | Should Be $true
        }
        $iconSection = Get-InnoSection -Source $source -Name "Icons"
        $runSection = Get-InnoSection -Source $source -Name "Run"
        $codeSection = Get-InnoSection -Source $source -Name "Code"
        $iconSection | Should Match '(?im)^Name:.*IconConfig.*Filename:\s*"\{code:GetConfigurationPythonPath\}".*GetConfigurationArguments'
        $iconSection | Should Match '(?im)^Name:\s*"\{userdesktop\}\\\{cm:IconConfig\}";.*GetConfigurationPythonPath.*GetConfigurationArguments'
        $iconSection | Should Match '(?im)^Name:.*IconConfigFolder.*explorer\.exe.*GetConfigPath'
        $runSection | Should Match '(?im)^Filename:\s*"\{code:GetConfigurationPythonPath\}".*RunOpenConfiguration.*unchecked'
        $codeSection | Should Match '(?is)function\s+GetConfigurationArguments.*?--project-root.*?--gateway-root.*?--workspace.*?--profiles.*?--active-profile.*?--memory-threshold.*?--persona-threshold.*?--temperament-threshold.*?--qdrant-enabled.*?--persona-layer-disabled.*?--language'
        $codeSection | Should Match '(?is)function\s+ConfigurationUiExists.*?plwc-config\.js.*?plwc-config\.css'

        $python = Get-Content -LiteralPath (Join-Path $configurationRoot "plwc-config.py") -Raw -Encoding UTF8
        $javascript = Get-Content -LiteralPath (Join-Path $configurationRoot "plwc-config.js") -Raw -Encoding UTF8
        $python | Should Match '\("127\.0\.0\.1",\s*0\)'
        $python | Should Match '_bootstrap_gateway_import_path'
        $python | Should Match 'SameSite=Strict'
        $python | Should Match 'plwc_governor\('
        $python | Should Match 'confirmed=True'
        $javascript | Should Match '/api/settings'
        $javascript | Should Match '/api/profile/plan'
        $javascript | Should Match '/api/profile/apply'

        $buildSource = Get-Content -LiteralPath $buildScript -Raw -Encoding UTF8
        foreach ($file in $configurationFiles) {
            $buildSource | Should Match ([regex]::Escape($file))
        }
        $buildSource | Should Match 'common\\configuration'
    }

    It "pins the accepted 1.0 Chat Bridge identity across Setup and the component manifest" {
        $expectedBuildIdentity = Get-Content -LiteralPath $bridgeBuildIdentityPath -Raw | ConvertFrom-Json
        $componentManifest = Get-Content -LiteralPath $componentsManifestPath -Raw | ConvertFrom-Json
        $componentManifestSource = Get-Content -LiteralPath $componentsManifestPath -Raw

        $expectedBuildIdentity.releaseVersion | Should Be "1.0.0"
        $expectedBuildIdentity.components.nodeBridge | Should Be $expectedBuildIdentity.releaseVersion
        $expectedBuildIdentity.components.browserExtension | Should Be $expectedBuildIdentity.releaseVersion
        $expectedBuildIdentity.components.nativeLauncher | Should Be $expectedBuildIdentity.releaseVersion
        $componentManifest.product.releaseVersion | Should Be $expectedBuildIdentity.releaseVersion
        $source | Should Match '(?im)^\s*#define\s+AppVersion\s+"1\.0\.0"\s*$'
        $source | Should Match '(?im)^\s*#define\s+GatewayVersion\s+"1\.0\.0"\s*$'
        $source | Should Match '(?im)^\s*#define\s+NodeBridgeVersion\s+"1\.0\.0"\s*$'
        $source | Should Match '(?im)^\s*#define\s+BrowserExtensionVersion\s+"1\.0\.0"\s*$'
        $source | Should Match '(?im)^\s*#define\s+NativeLauncherVersion\s+"1\.0\.0"\s*$'
        $source | Should Match '(?im)^\s*#define\s+BridgeDirectoryName\s+"chat-bridge-1\.0\.0"\s*$'
        $source | Should Match '"track": "v1\.0\.0"'
        $componentManifest.product.chatBridgeVersion | Should Be $expectedBuildIdentity.releaseVersion
        (@($componentManifest.components | Where-Object { $_.id -eq "chat_bridge" })[0].version) |
            Should Be $expectedBuildIdentity.releaseVersion
        $componentManifestSource | Should Not Match '0\.2\.0-rc19\.dev\d+'
    }

    It "records one complete runtime build identity in summary diagnostics and selection state" {
        $source | Should Match '(?is)function\s+GetSetupExeSha256.*?GetSHA256OfFile\(ExpandConstant\(''\{srcexe\}''\)\)'
        $source | Should Match '(?is)function\s+GetInstallerBuildId.*?GetSetupExeSha256'
        $source | Should Match '(?is)function\s+GetInstallationMode.*?WizardSetupType\(False\)'
        $source | Should Match '(?is)function\s+GetSelectedComponentIds.*?WizardSelectedComponents\(False\)'
        $codeSection | Should Match '(?is)function\s+BuildIdentitySummary.*?SummaryBuildId.*?SummaryInstallerRevision.*?SummarySetupSha256.*?SummaryGatewayVersion.*?SummaryNodeBridgeVersion.*?SummaryBrowserExtensionVersion.*?SummaryNativeLauncherVersion.*?SummaryInstallationMode.*?SummarySelectedComponentIds'
        $codeSection | Should Match '(?is)function\s+BuildInstallSummary.*?BuildIdentitySummary'

        foreach ($key in @(
            "BuildId",
            "InstallerRevision",
            "SetupExeSha256",
            "GatewayVersion",
            "NodeBridgeVersion",
            "BrowserExtensionVersion",
            "NativeLauncherVersion",
            "InstallationMode",
            "SelectedComponents"
        )) {
            $codeSection | Should Match (
                "(?is)SetIniString\(\s*'BuildIdentity'\s*,\s*'{0}'" -f $key
            )
        }

        foreach ($diagnosticKey in @(
            "build_id",
            "installer_revision",
            "setup_exe_sha256",
            "gateway_version",
            "node_bridge_version",
            "browser_extension_version",
            "native_launcher_version",
            "installation_mode",
            "selected_components"
        )) {
            $codeSection | Should Match (
                "(?is)BuildInstallerDiagnosticRecord.*?'{0}=" -f $diagnosticKey
            )
        }
        $codeSection | Should Match '(?is)procedure\s+CurStepChanged.*?ConfigureChatBridgeWindowsIntegration\s*;.*?AppendInstallerDiagnosticRecord\(\s*''installation_completed'''
    }

    It "derives the installer build record from canonical component identities" {
        $buildSource = Get-Content -LiteralPath $buildScript -Raw
        $buildSource | Should Match '(?is)function\s+Get-InstallerRevision.*?PLwCSetup\.iss'
        $buildSource | Should Match '(?is)function\s+Write-InstallerBuildIdentity.*?Get-FileHash.*?InstallerPath.*?Get-FileHash.*?PayloadManifestPath'
        $buildSource | Should Match 'CHAT-BRIDGE-1\.0'
        $buildSource | Should Match 'docs/evidence/CHAT_BRIDGE_1_0_ACCEPTANCE_EN\.md'
        foreach ($define in @(
            "InstallerRevision",
            "GatewayVersion",
            "NodeBridgeVersion",
            "BrowserExtensionVersion",
            "NativeLauncherVersion"
        )) {
            $buildSource | Should Match ("/D{0}=" -f $define)
        }
        $uiSmokeSource = Get-Content -LiteralPath $installerUiSmokePath -Raw -Encoding UTF8
        $uiSmokeSource | Should Match 'ExpectSetupP003BuildIdentity'
        $uiSmokeSource | Should Match 'SETUP_P0_03_BUILD_IDENTITY_VISIBLE'
    }

    It "keeps signing strong while allowing only an explicit unsigned build" {
        $buildSource = Get-Content -LiteralPath $buildScript -Raw
        $buildSource | Should Match '\[switch\]\s+\$Unsigned'
        $buildSource | Should Match 'function\s+Invoke-AuthenticodeSigning'
        $buildSource | Should Match 'function\s+Assert-AuthenticodeSignature'
        $buildSource | Should Match 'function\s+Assert-UnsignedArtifact'
        $buildSource | Should Match 'mode\s*=\s*"explicit_unsigned"'
        $buildSource | Should Match 'required\s*=\s*\$false'
        $buildSource | Should Match 'PLWC_SIGNING_CERT_THUMBPRINT'
        $buildSource | Should Match 'PLWC_SIGNING_TIMESTAMP_URL'
        $buildSource | Should Match '"/fd",\s*"SHA256"'
        $buildSource | Should Match '"/tr",\s*\$Context\.TimestampUrl'
        $buildSource | Should Match '"/td",\s*"SHA256"'
        $buildSource | Should Match '@\("verify",\s*"/pa",\s*"/all",\s*"/tw"'
        $buildSource | Should Match '(?is)Build-NativeLauncher.*?Invoke-AuthenticodeSigning.*?Write-PayloadManifest'
        $buildSource | Should Match '(?is)Invoke-CheckedCommand\s+-FilePath\s+\$iscc.*?Invoke-AuthenticodeSigning.*?Write-InstallerBuildIdentity'
        $buildSource | Should Match '(?is)\$Unsigned.*?Assert-UnsignedArtifact.*?Write-InstallerBuildIdentity'
    }

    It "keeps Setup per-user and elevates only prerequisite child operations" {
        $setupSection | Should Match '(?im)^\s*PrivilegesRequired\s*=\s*lowest\s*$'
        $setupSection | Should Not Match '(?im)^\s*PrivilegesRequiredOverridesAllowed\s*='
        $codeSection | Should Match '(?is)procedure\s+RunPrerequisiteChecks.*?if\s+IsAdmin\s+then.*?PrereqAdminElevated.*?else.*?PrereqAdminStandard'
        $customMessageSection | Should Match '(?im)^\s*german\.PagePrereqActionSubCaption=.*nur bei Bedarf'
        $customMessageSection | Should Match '(?im)^\s*english\.PagePrereqActionSubCaption=.*only.*when needed'
        $customMessageSection | Should Not Match '(?im)^\s*(?:german|english)\.PagePrereqActionSubCaption=.*(?:Als Administrator ausf.hren|Run as administrator)'
        $codeSection | Should Match '(?is)if\s+Elevated\s+then\s+Result\s*:=\s*ShellExec\(\s*''runas'''
        $nodeFunction = [regex]::Match(
            $codeSection,
            '(?is)function\s+InstallNodePrerequisite.*?(?=function\s+InstallDockerPrerequisite)'
        ).Value
        $nodeFunction | Should Match "MsiexecPath\s*:=\s*ExpandConstant\('\{sys\}\\msiexec\.exe'\)"
        $nodeFunction | Should Not Match '\{sysnative\}\\msiexec\.exe'
        $codeSection | Should Match "(?is)PrerequisiteExitCodeHint.*?ResultCode\s*=\s*3.*?PrereqFailurePath"
    }

    It "uses one stable Chat Bridge identity and executes the installed integration scripts" {
        (Test-Path -LiteralPath $bridgeIdentityPath -PathType Leaf) | Should Be $true
        $identity = Get-Content -LiteralPath $bridgeIdentityPath -Raw | ConvertFrom-Json
        $identity.extensionId | Should Be "nlogfcafjdfdoknpkbehjgihpafpipdb"
        $identity.allowedOrigin | Should Be "chrome-extension://nlogfcafjdfdoknpkbehjgihpafpipdb/"

        $source | Should Match '(?im)^\s*#define\s+StableChatBridgeExtensionId\s+"nlogfcafjdfdoknpkbehjgihpafpipdb"\s*$'
        $codeSection | Should Match "(?im)^\s*ChatBridgeExtensionId\s*=\s*'\{#StableChatBridgeExtensionId\}'\s*;"
        $codeSection | Should Not Match '(?im)^\s*ExtensionPage\s*:'
        $codeSection | Should Not Match '(?i)FieldChromeId|FieldEdgeId|IsValidExtensionId'

        $registration = [regex]::Match(
            $codeSection,
            '(?is)procedure\s+ConfigureChatBridgeWindowsIntegration.*?(?=procedure\s+RemoveChatBridgeWindowsIntegration)'
        ).Value
        $registration | Should Match '(?i)GetNativeInstallScriptPath'
        $registration | Should Match '(?i)-SkipBuild\s+-Browser\s+All'
        $registration | Should Match '(?i)-ExtensionId.*ChatBridgeExtensionId'
        $registration | Should Match '(?i)GetBridgeAutostartScriptPath'
        $registration | Should Match '(?i)-ConfigPath'
        $registration | Should Match '(?i)-StartNow'
        $codeSection | Should Match '(?is)procedure\s+CurStepChanged.*?SaveGeneratedFiles\s*;.*?ConfigureChatBridgeWindowsIntegration\s*;'
        $codeSection | Should Match '(?is)function\s+ExecuteBridgePowerShellScript.*?ExecAsOriginalUser.*?ewWaitUntilTerminated'
        $registration | Should Match '(?is)if\s+not\s+ExecuteBridgePowerShellScript.*?GetBridgeAutostartScriptPath.*?begin.*?GetNativeInstallScriptPath.*?-Uninstall.*?RaiseException'
        $codeSection | Should Match '(?is)procedure\s+RemoveChatBridgeWindowsIntegration.*?-Remove.*?-Uninstall.*?-Browser\s+All'
        $codeSection | Should Match '(?is)procedure\s+RemoveChatBridgeWindowsIntegration.*?False,\s*False'
        $codeSection | Should Match '(?is)BuildInstallSummary.*?SummaryNativeStable.*?ChatBridgeExtensionId'
        $codeSection | Should Match '(?is)BuildInstallSummary.*?SummaryBridgeAutostart'
    }

    It "keeps Native Messaging registration and Bridge autostart scripts idempotent and removable" {
        foreach ($scriptPath in @($nativeInstallScriptPath, $autostartInstallScriptPath, $bridgeStartScriptPath)) {
            (Test-Path -LiteralPath $scriptPath -PathType Leaf) | Should Be $true
            $scriptSource = Get-Content -LiteralPath $scriptPath -Raw -Encoding UTF8
            { [scriptblock]::Create($scriptSource) | Out-Null } | Should Not Throw
        }

        $nativeSource = Get-Content -LiteralPath $nativeInstallScriptPath -Raw -Encoding UTF8
        $nativeSource | Should Match '(?i)\$SkipBuild'
        $nativeSource | Should Match '(?i)--register'
        $nativeSource | Should Match '(?i)--unregister'
        $nativeSource | Should Match '(?i)--status'
        $nativeSource | Should Match '(?i)native-messaging\\plwc\.chat_bridge\.launcher\.json'
        $nativeSource | Should Match '(?i)BraveSoftware\\Brave-Browser\\NativeMessagingHosts'
        $nativeSource | Should Match '(?is)\$Uninstall\s+-and\s+-not.*?\$registryRoots.*?Remove-Item'

        $autostartSource = Get-Content -LiteralPath $autostartInstallScriptPath -Raw -Encoding UTF8
        $autostartSource | Should Match '(?i)New-ScheduledTaskTrigger\s+-AtLogOn'
        $autostartSource | Should Match '(?i)Delay\s*=\s*"PT20S"'
        $autostartSource | Should Match '(?is)New-ScheduledTaskPrincipal.*?-LogonType\s+Interactive.*?-RunLevel\s+Limited'
        $autostartSource | Should Match '(?i)-MultipleInstances\s+IgnoreNew'
        $autostartSource | Should Match '(?i)-RestartCount\s+3'
        $autostartSource | Should Match '(?i)Unregister-ScheduledTask'
        $autostartSource | Should Match '(?i)Stop-OwnedBridgeProcess'
        $autostartSource | Should Match '(?is)function\s+Get-PLwCOwnedBridgeProcesses.*?\$previousBridgeEntry.*?Get-CimInstance\s+Win32_Process'
        $autostartSource | Should Match '(?is)function\s+Stop-OwnedBridgeProcess.*?Get-PLwCOwnedBridgeProcesses.*?Stop-Process'
        $autostartSource | Should Match '(?i)Test-PLwCOwnedScheduledTask'
        $autostartSource | Should Match '(?i)exists but is not owned by PLwC'
        $autostartSource | Should Match '(?i)Export-ScheduledTask'
        $autostartSource | Should Match '(?i)\$previousSettingsBytes'
        $autostartSource | Should Match '(?is)catch\s*\{.*?Register-ScheduledTask.*?-Xml\s+\$previousTaskXml.*?WriteAllBytes'
        $autostartSource | Should Match '(?i)\$StartNow'

        $startSource = Get-Content -LiteralPath $bridgeStartScriptPath -Raw -Encoding UTF8
        $startSource | Should Match '(?i)\$Detached'
        $startSource | Should Match '(?i)launch-bridge\.mjs'
        $startSource | Should Match '(?i)healthcheck\.mjs'
        $startSource | Should Match '(?i)\$healthEndpoint'
        $startSource | Should Match '(?i)build-identity\.json'
        $startSource | Should Match '(?i)--expected-build-id'
        $startSource | Should Match '(?i)Get-CimInstance'
        $startSource | Should Match '(?i)Stop-Process'
        $startSource | Should Match '(?is)Stop-PLwCOwnedBridgeProcess.*?did not reach the 8 of 8 ready state'
        $startSource | Should Not Match '(?im)^\s*exit(?:\s|$)'
        $startSource | Should Match '(?i)8 of 8'
        $startSource | Should Match '(?i)Resolve-PLwCDockerExecutable'
        $startSource | Should Match '(?i)\$env:PLWC_DOCKER_EXE\s*='
        $codeSection | Should Match '(?is)function\s+BuildBridgeConfig.*?"PLWC_DOCKER_EXE"'

        $launchSource = Get-Content -LiteralPath $bridgeLaunchScriptPath -Raw -Encoding UTF8
        $launchSource | Should Match '(?i)acquireLaunchLock'
        $launchSource | Should Match '(?i)launchInProgress'
        $launchSource | Should Match '(?i)verifyBridgeHealth'
        $launchSource | Should Match '(?i)process\.kill\(child\.pid\)'
        $launchSource | Should Not Match '(?i)isProcessRunning'

        $launcherSource = Get-Content -LiteralPath $nativeLauncherSourcePath -Raw -Encoding UTF8
        $launcherSource | Should Match '(?i)ResolveBridgeEndpoint'
        $launcherSource | Should Match '(?i)QuoteArgument\(layout\.Endpoint\)'
        $launcherSource | Should Match '(?i)IsLoopbackPortOpen\(layout\.Port\)'
        $launcherSource | Should Match '(?is)health_timeout.*?StopLaunchedBridge\(launchOutput\)'
    }

    It "documents manual Chrome and Brave extension installation for end users" {
        (Test-Path -LiteralPath $windowsInstallerGuidePath -PathType Leaf) | Should Be $true
        $guide = Get-Content -LiteralPath $windowsInstallerGuidePath -Raw -Encoding UTF8
        foreach ($requiredText in @(
            '%APPDATA%\PLwC\app\chat-bridge-<version>\extension',
            '<selected Chat Bridge directory>\extension',
            'chrome://extensions',
            'brave://extensions',
            'Developer mode',
            'Load unpacked',
            'Reload',
            'plwc.chat_bridge.launcher',
            '%APPDATA%\PLwC\config\native-messaging\plwc.chat_bridge.launcher.json',
            'Reconnect',
            'Tools     8 / 8',
            'wrong extension directory',
            'Bridge is unavailable',
            'Do not run repository scripts manually'
        )) {
            $guide | Should Match ([regex]::Escape($requiredText))
        }
    }

    It "records the serial browser Store track before clean-Windows acceptance" {
        foreach ($path in @($workOrderPath, $windowsInstallerPlanPath)) {
            (Test-Path -LiteralPath $path -PathType Leaf) | Should Be $true
            $document = Get-Content -LiteralPath $path -Raw -Encoding UTF8
            $trackStart = $document.IndexOf(
                "Browser Store Distribution Track",
                [StringComparison]::OrdinalIgnoreCase
            )
            ($trackStart -ge 0) | Should Be $true
            $track = $document.Substring($trackStart)
            $positions = @(
                $track.IndexOf("STORE-G0-01", [StringComparison]::Ordinal),
                $track.IndexOf("BRIDGE-P0-03", [StringComparison]::Ordinal),
                $track.IndexOf("SETUP-P0-05", [StringComparison]::Ordinal),
                $track.IndexOf("STORE-P0-02", [StringComparison]::Ordinal),
                $track.IndexOf("SETUP-P0-04", [StringComparison]::Ordinal)
            )
            ($positions -notcontains -1) | Should Be $true
            (($positions | Sort-Object) -join ",") | Should Be ($positions -join ",")
            $track | Should Match '(?i)H2'
            $track | Should Match '(?i)(?:(?:must\s+)?never|must not)\s+bypass.*browser.*consent'
        }
    }

    It "uses friendly action-required wording and real German umlauts" {
        $sourceBytes = [IO.File]::ReadAllBytes($setupScript)
        $strictUtf8 = New-Object Text.UTF8Encoding -ArgumentList $false, $true
        { $strictUtf8.GetString($sourceBytes) } | Should Not Throw

        $germanText = (@([regex]::Matches($customMessageSection, '(?im)^\s*german\.[A-Za-z0-9_]+\s*=(?<Value>.*)$') |
            ForEach-Object { $_.Groups['Value'].Value }) -join "`n")
        foreach ($codePoint in @(0x00E4, 0x00F6, 0x00FC, 0x00C4, 0x00DF)) {
            $germanText.Contains([string][char]$codePoint) | Should Be $true
        }
        $germanText.Contains([string][char]0x00C3) | Should Be $false
        $germanText | Should Not Match '(?i)\b(fuer|ueber|zurueck|waehlen|ausgewaehlt|geprueft|pruefen|pruefungen|muessen|duerfen|oeffnen|verfuegbar|veraendert|spaeter|standardmaessig|ueberspringen)\b'
        $germanText | Should Not Match '(?i)\bblockiert\b'
        $customMessageSection | Should Match '(?im)^\s*german\.PrereqActionRequired\s*=\[AKTION ERFORDERLICH\]\s*$'
        $customMessageSection | Should Match '(?im)^\s*english\.PrereqActionRequired\s*=\[ACTION REQUIRED\]\s*$'
    }

    It "does not embed German-only page or message-box text in Pascal code" {
        $localizedLookup = '(?i)CustomMessage\s*\(|\{cm:'
        $pageCalls = Get-PascalCalls -Source $codeSection -FunctionPattern 'Create(?:InputDir|InputQuery|InputOption|Custom|OutputMsg)Page'
        $messageCalls = Get-PascalCalls -Source $codeSection -FunctionPattern '(?:MsgBox|SuppressibleMsgBox)'
        ($pageCalls.Count -gt 0) | Should Be $true
        ($messageCalls.Count -gt 0) | Should Be $true
        @($pageCalls | Where-Object { $_.Value -notmatch $localizedLookup }).Count | Should Be 0
        @($messageCalls | Where-Object {
            $_.Value -notmatch $localizedLookup -and
            $_.Value -notmatch '(?i)MsgBox\s*\(\s*ErrorMessage'
        }).Count | Should Be 0
    }

    It "splits directory inputs across pages with at most three inputs each" {
        $dirPageDeclarations = @([regex]::Matches($codeSection, '(?im)^\s*(?<Name>[A-Za-z][A-Za-z0-9_]*)\s*:\s*TInputDirWizardPage\s*;'))
        ($dirPageDeclarations.Count -ge 3) | Should Be $true

        foreach ($declaration in $dirPageDeclarations) {
            $pageName = $declaration.Groups["Name"].Value
            $addCount = [regex]::Matches($codeSection, ("(?im)\b{0}\.Add\s*\(" -f [regex]::Escape($pageName))).Count
            ($addCount -le 3) | Should Be $true
        }
    }

    It "keeps three threshold inputs separate from checkbox options" {
        $queryDeclarations = @([regex]::Matches($codeSection, '(?im)^\s*(?<Name>[A-Za-z][A-Za-z0-9_]*)\s*:\s*TInputQueryWizardPage\s*;'))
        $thresholdPages = @($queryDeclarations | Where-Object {
            $pageName = $_.Groups["Name"].Value
            $adds = @([regex]::Matches($codeSection, ("(?is)\b{0}\.Add\s*\((?<Argument>.*?)\);" -f [regex]::Escape($pageName))))
            (($adds | ForEach-Object { $_.Groups["Argument"].Value }) -join "`n") -match 'FieldMemoryThreshold' -and
            (($adds | ForEach-Object { $_.Groups["Argument"].Value }) -join "`n") -match 'FieldPersonaThreshold' -and
            (($adds | ForEach-Object { $_.Groups["Argument"].Value }) -join "`n") -match 'FieldTemperamentThreshold'
        })
        $thresholdPages.Count | Should Be 1
        $thresholdPageName = $thresholdPages[0].Groups["Name"].Value
        [regex]::Matches($codeSection, ("(?im)\b{0}\.Add\s*\(" -f [regex]::Escape($thresholdPageName))).Count | Should Be 3
        $codeSection | Should Not Match ("(?is)\b{0}\.Add\s*\([^;]*(?:Qdrant|Persona Layer)" -f [regex]::Escape($thresholdPageName))
    }

    It "uses checkbox options for Qdrant and the persona layer" {
        $optionDeclarations = @([regex]::Matches($codeSection, '(?im)^\s*(?<Name>[A-Za-z][A-Za-z0-9_]*)\s*:\s*TInputOptionWizardPage\s*;'))
        ($optionDeclarations.Count -gt 0) | Should Be $true

        $matchingOptionPages = @()
        foreach ($declaration in $optionDeclarations) {
            $pageName = $declaration.Groups["Name"].Value
            $pageAdds = @([regex]::Matches($codeSection, ("(?is)\b{0}\.Add\s*\((?<Argument>.*?)\);" -f [regex]::Escape($pageName))))
            $arguments = $pageAdds | ForEach-Object { $_.Groups["Argument"].Value }
            if (($arguments -join "`n") -match '(?i)Qdrant' -and ($arguments -join "`n") -match '(?i)Persona') {
                $matchingOptionPages += $pageName
            }
        }
        $matchingOptionPages.Count | Should Be 1
        $optionPageName = $matchingOptionPages[0]
        $codeSection | Should Match ("(?is)\b{0}\s*:=\s*CreateInputOptionPage\s*\(.*?,\s*False\s*,\s*False\s*\);" -f [regex]::Escape($optionPageName))
        $codeSection | Should Match ("(?im)\b{0}\.Values\s*\[\s*0\s*\]" -f [regex]::Escape($optionPageName))
        $codeSection | Should Match ("(?im)\b{0}\.Values\s*\[\s*1\s*\]" -f [regex]::Escape($optionPageName))
    }
}

Describe "PLwC Windows payload build gate" {
    $testBuildMutex = [Threading.Mutex]::new($false, "Local\PLwC-Windows-Installer-Build")
    $testBuildMutexAcquired = $false
    try {
        try {
            $testBuildMutexAcquired = $testBuildMutex.WaitOne([TimeSpan]::FromMinutes(10))
        }
        catch [Threading.AbandonedMutexException] {
            $testBuildMutexAcquired = $true
        }
        if (-not $testBuildMutexAcquired) {
            throw "Timed out waiting for the PLwC installer build mutex."
        }

        $buildParameters = @{
            ValidateOnly = $true
            GeneratedOutputRoot = $testGeneratedOutputRoot
        }
        $existingBridgeBuild = Join-Path $repoRoot "integrations\plwc-chat-bridge\bridge\dist\src\index.js"
        $existingExtensionBuild = Join-Path $repoRoot "integrations\plwc-chat-bridge\extension\dist\manifest.json"
        if ((Test-Path -LiteralPath $existingBridgeBuild -PathType Leaf) -and
            (Test-Path -LiteralPath $existingExtensionBuild -PathType Leaf)) {
            $buildParameters.SkipNodeBuild = $true
        }
        try {
            $output = @(& $buildScript @buildParameters *>&1)
            $buildExitCode = 0
        }
        catch {
            $output = @($_)
            $buildExitCode = 1
        }

    It "completes ValidateOnly without ISCC" {
        if ($buildExitCode -ne 0) {
            Write-Host ($output -join [Environment]::NewLine)
        }
        $buildExitCode | Should Be 0
        ($output -join "`n") | Should Match 'ISCC was not invoked'
    }

    It "stages real Gateway and Chat Bridge runtime artifacts" {
        (Test-Path -LiteralPath (Join-Path $stageRoot "gateway\server.py") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "gateway\src\plwc_gateway\mcp\server.py") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\bridge\dist\src\index.js") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\extension\manifest.json") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\native\bin\plwc-chat-bridge-launcher.exe") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\scripts\install-native-launcher-windows.ps1") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\scripts\install-autostart-windows.ps1") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\scripts\start-windows.ps1") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\bridge\scripts\healthcheck.mjs") -PathType Leaf) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $stageRoot "chat-bridge\bridge\scripts\launch-bridge.mjs") -PathType Leaf) | Should Be $true
        $stagedIdentity = Get-Content -LiteralPath (Join-Path $stageRoot "chat-bridge\native\extension-identity.json") -Raw | ConvertFrom-Json
        $stagedIdentity.extensionId | Should Be "nlogfcafjdfdoknpkbehjgihpafpipdb"
        $expectedBuildIdentity = Get-Content -LiteralPath $bridgeBuildIdentityPath -Raw | ConvertFrom-Json
        $stagedBuildIdentity = Get-Content -LiteralPath (Join-Path $stageRoot "chat-bridge\build-identity.json") -Raw | ConvertFrom-Json
        $launcherBuildIdentity = (& (Join-Path $stageRoot "chat-bridge\native\bin\plwc-chat-bridge-launcher.exe") --build-identity) | ConvertFrom-Json
        $stagedBuildIdentity.buildId | Should Be $expectedBuildIdentity.buildId
        $launcherBuildIdentity.buildId | Should Be $expectedBuildIdentity.buildId
        $launcherBuildIdentity.components.nodeBridge | Should Be $expectedBuildIdentity.components.nodeBridge
        $launcherBuildIdentity.components.browserExtension | Should Be $expectedBuildIdentity.components.browserExtension
        $launcherBuildIdentity.components.nativeLauncher | Should Be $expectedBuildIdentity.components.nativeLauncher
    }

    It "stages the localized Getting Started pages as hashed common payload" {
        $manifest = Get-Content -LiteralPath (Join-Path $stageRoot "payload-manifest.json") -Raw | ConvertFrom-Json
        foreach ($file in @("getting-started-en.html", "getting-started-de.html", "getting-started.css")) {
            $stagedPath = Join-Path $stageRoot ("common\docs\{0}" -f $file)
            (Test-Path -LiteralPath $stagedPath -PathType Leaf) | Should Be $true
            $manifestEntry = @($manifest.files | Where-Object { $_.path -eq ("common/docs/{0}" -f $file) })
            $manifestEntry.Count | Should Be 1
            (Get-FileHash -LiteralPath $stagedPath -Algorithm SHA256).Hash.ToLowerInvariant() |
                Should Be ([string] $manifestEntry[0].sha256)
        }
    }

    It "stages the local configuration UI as hashed common payload" {
        $manifest = Get-Content -LiteralPath (Join-Path $stageRoot "payload-manifest.json") -Raw | ConvertFrom-Json
        foreach ($file in $configurationFiles) {
            $stagedPath = Join-Path $stageRoot ("common\configuration\{0}" -f $file)
            (Test-Path -LiteralPath $stagedPath -PathType Leaf) | Should Be $true
            $manifestEntry = @($manifest.files | Where-Object { $_.path -eq ("common/configuration/{0}" -f $file) })
            $manifestEntry.Count | Should Be 1
            (Get-FileHash -LiteralPath $stagedPath -Algorithm SHA256).Hash.ToLowerInvariant() |
                Should Be ([string] $manifestEntry[0].sha256)
        }
    }

    It "records the complete component contract" {
        $manifest = Get-Content -LiteralPath (Join-Path $stageRoot "payload-manifest.json") -Raw | ConvertFrom-Json
        $componentIds = @($manifest.components | ForEach-Object { $_.id })
        foreach ($componentId in @("gateway", "claude-mcpb", "stdio-codex", "stdio-odysseus", "chat-bridge")) {
            ($componentIds -contains $componentId) | Should Be $true
        }
        (@($manifest.components | Where-Object { $_.id -eq "gateway" })[0].required) | Should Be $true
        (@($manifest.components | Where-Object { $_.id -ne "gateway" -and $_.required }).Count) | Should Be 0
        $expectedBuildIdentity = Get-Content -LiteralPath $bridgeBuildIdentityPath -Raw | ConvertFrom-Json
        $chatBridge = @($manifest.components | Where-Object { $_.id -eq "chat-bridge" })[0]
        $chatBridge.version | Should Be $expectedBuildIdentity.releaseVersion
        $chatBridge.buildId | Should Be $expectedBuildIdentity.buildId
        $chatBridge.identityPath | Should Be "chat-bridge/build-identity.json"
        $chatBridge.components.nodeBridge | Should Be $expectedBuildIdentity.components.nodeBridge
        $chatBridge.components.browserExtension | Should Be $expectedBuildIdentity.components.browserExtension
        $chatBridge.components.nativeLauncher | Should Be $expectedBuildIdentity.components.nativeLauncher
    }

    It "binds staged payload metadata to the installer revision and component versions" {
        $manifest = Get-Content -LiteralPath (Join-Path $stageRoot "payload-manifest.json") -Raw | ConvertFrom-Json
        $expectedBuildIdentity = Get-Content -LiteralPath $bridgeBuildIdentityPath -Raw | ConvertFrom-Json
        $manifest.installer.revision | Should Be "installer-r22"
        $manifest.installer.artifactName | Should Be (
            "PLwC-Setup-{0}-installer-r22.exe" -f $manifest.version
        )
        $manifest.installer.buildIdentityArtifact | Should Be (
            "PLwC-{0}-installer-r22-build-identity.json" -f $manifest.version
        )
        $manifest.installer.evidencePackage | Should Be "CHAT-BRIDGE-1.0"
        $manifest.installer.evidencePath | Should Be "docs/evidence/CHAT_BRIDGE_1_0_ACCEPTANCE_EN.md"
        $componentManifest = Get-Content -LiteralPath $componentsManifestPath -Raw | ConvertFrom-Json
        $manifest.version | Should Be $componentManifest.product.releaseVersion
        $manifest.installer.components.gateway | Should Be $componentManifest.product.gatewayVersion
        $manifest.installer.components.nodeBridge | Should Be $expectedBuildIdentity.components.nodeBridge
        $manifest.installer.components.browserExtension | Should Be $expectedBuildIdentity.components.browserExtension
        $manifest.installer.components.nativeLauncher | Should Be $expectedBuildIdentity.components.nativeLauncher
    }

    It "binds the browser bridge to fixed loopback and eight public tools" {
        $config = Get-Content -LiteralPath (Join-Path $stageRoot "chat-bridge\config\plwc.example.json") -Raw | ConvertFrom-Json
        $config.bridge.host | Should Be "127.0.0.1"
        $config.tools.publicFacadeOnly | Should Be $true
        $config.tools.expectedPublicToolCount | Should Be 8
        $config.gateway.args.Count | Should Be 1
        $config.gateway.args[0] | Should Be '${configDir}/../../gateway/server.py'
        $config.gateway.cwd | Should Be '${configDir}/../../gateway'
    }

    It "stages the optional MCPB where the Inno Claude component consumes it" {
        $manifest = Get-Content -LiteralPath (Join-Path $stageRoot "payload-manifest.json") -Raw | ConvertFrom-Json
        $claudeComponent = @($manifest.components | Where-Object { $_.id -eq "claude-mcpb" })[0]
        $mcpbFiles = @(Get-ChildItem -LiteralPath (Join-Path $stageRoot "claude") -Filter *.mcpb -File -ErrorAction SilentlyContinue)
        if ($claudeComponent.available) {
            $mcpbFiles.Count | Should Be 1
        }
        else {
            $mcpbFiles.Count | Should Be 0
        }
        (Test-Path -LiteralPath (Join-Path $stageRoot "mcpb")) | Should Be $false
    }

    It "discovers the per-user Inno Setup compiler location" {
        $source = Get-Content -LiteralPath $buildScript -Raw
        $source | Should Match 'LOCALAPPDATA'
        $source | Should Match 'Programs\\Inno Setup 6\\ISCC\.exe'
    }

    It "stages the native identity context required by the extension build" {
        $source = Get-Content -LiteralPath $buildScript -Raw
        foreach ($relativePath in @(
            "native\extension-identity.json",
            "native\manifest\plwc.chat_bridge.launcher.json",
            "native\launcher-host\Plwc.ChatBridge.NativeLauncher.cs"
        )) {
            $source | Should Match (
                '(?i)nodeBuildWorkRoot\s+"{0}"' -f
                    [regex]::Escape($relativePath)
            )
        }
        $copyIndex = $source.IndexOf(
            'nodeBuildWorkRoot "native\extension-identity.json"',
            [StringComparison]::OrdinalIgnoreCase
        )
        $extensionBuildIndex = $source.IndexOf(
            'Invoke-CheckedCommand -FilePath $npm.Source -ArgumentList @("run", "build")',
            [StringComparison]::OrdinalIgnoreCase
        )
        ($copyIndex -ge 0 -and $copyIndex -lt $extensionBuildIndex) |
            Should Be $true
    }

    It "contains no private roots, credentials, reparse points or unsafe legacy payloads" {
        $forbidden = @(
            Get-ChildItem -LiteralPath $stageRoot -Recurse -File -Force | Where-Object {
                $relative = $_.FullName.Substring($stageRoot.Length).TrimStart('\', '/').Replace('\', '/')
                $relative -match '(^|/)(private_evidence|logs?|workspace|\.git|\.env)(/|$)' -or
                $relative -match '(?i)(install_pba2|setup-claude-server|track-installation|desktop-commander)' -or
                $_.Extension -match '(?i)^\.(pem|key|pfx|p12)$'
            }
        )
        $forbidden.Count | Should Be 0

        $reparsePoints = @(Get-ChildItem -LiteralPath $stageRoot -Recurse -Force | Where-Object {
            ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
        })
        $reparsePoints.Count | Should Be 0
    }

    It "publishes a sorted and complete SHA256 payload manifest" {
        $manifestPath = Join-Path $stageRoot "payload-manifest.json"
        $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        $manifest.hashAlgorithm | Should Be "SHA256"

        $recordedPaths = @($manifest.files | ForEach-Object { [string] $_.path })
        $sortedPaths = @($recordedPaths)
        [Array]::Sort($sortedPaths, [StringComparer]::Ordinal)
        ($recordedPaths -join "`n") | Should Be ($sortedPaths -join "`n")

        $actualFiles = @(
            Get-ChildItem -LiteralPath $stageRoot -Recurse -File -Force |
                Where-Object { $_.FullName -ne $manifestPath }
        )
        $manifest.files.Count | Should Be $actualFiles.Count
        $actualPayloadBytes = [long] (($actualFiles | Measure-Object -Property Length -Sum).Sum)
        $manifest.payloadSizeBytes | Should Be $actualPayloadBytes
        $manifest.payloadSizeMiB | Should Be ([int] [Math]::Ceiling($actualPayloadBytes / 1MB))
        ([int] $manifest.payloadSizeMiB -gt 0) | Should Be $true
        foreach ($entry in $manifest.files) {
            $path = Join-Path $stageRoot ([string] $entry.path)
            (Test-Path -LiteralPath $path -PathType Leaf) | Should Be $true
            (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() | Should Be ([string] $entry.sha256)
            (Get-Item -LiteralPath $path).Length | Should Be ([long] $entry.size)
        }
    }

    It "keeps all generated output below installer/windows" {
        ([IO.Path]::GetFullPath($stageRoot).StartsWith($installerRoot, [StringComparison]::OrdinalIgnoreCase)) | Should Be $true
        ([IO.Path]::GetFullPath($distRoot).StartsWith($installerRoot, [StringComparison]::OrdinalIgnoreCase)) | Should Be $true
        (Test-Path -LiteralPath (Join-Path $distRoot "SHA256SUMS.txt") -PathType Leaf) | Should Be $true
    }
    }
    finally {
        if ($testBuildMutexAcquired) {
            $testBuildMutex.ReleaseMutex()
        }
        $testBuildMutex.Dispose()
    }
}
