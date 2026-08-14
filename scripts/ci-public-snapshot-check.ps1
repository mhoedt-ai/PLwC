[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$trackedFiles = @(& git ls-files)
if ($LASTEXITCODE -ne 0 -or $trackedFiles.Count -eq 0) {
    throw "Unable to enumerate the tracked public repository snapshot."
}

$forbiddenPathPatterns = @(
    '(^|/)(logs?|private_evidence|tmp|workspace)(/|$)',
    '^docs/(ARBEITSAUFTRAG_|briefings/|evidence/screenshots/)',
    '^installer/windows/(\.compile-check[^/]*|\.test-build|\.unsigned-build|dist|evidence|output|stage)(/|$)',
    '^installer/windows\.zip$',
    '^integrations/plwc-chat-bridge/(SESSION_NOTES_|bridge/[^/]*\.log$|extension/store/out/|native/bin/)',
    '(?i)\.(env|exe|key|mcpb|p12|pem|pfx|zip)$'
)

$forbiddenPaths = @(
    foreach ($path in $trackedFiles) {
        $normalized = $path.Replace('\', '/')
        if ($forbiddenPathPatterns | Where-Object { $normalized -match $_ }) {
            $normalized
        }
    }
)
if ($forbiddenPaths.Count -ne 0) {
    throw "The public snapshot contains forbidden local or release artifacts:`n$($forbiddenPaths -join [Environment]::NewLine)"
}

$maximumPublicFileBytes = 1MB
$oversizedFiles = @(
    foreach ($path in $trackedFiles) {
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
            throw "Tracked path is missing from the checkout: $path"
        }
        $file = Get-Item -LiteralPath $path -Force
        if ($file.Length -gt $maximumPublicFileBytes) {
            "{0} bytes  {1}" -f $file.Length, $path
        }
    }
)
if ($oversizedFiles.Count -ne 0) {
    throw "The public snapshot contains files larger than 1 MiB:`n$($oversizedFiles -join [Environment]::NewLine)"
}

$contentChecks = @(
    [PSCustomObject]@{ Label = "local repository path"; Fixed = $true; Pattern = ('T:' + '\CODEX_PROJEKTE') },
    [PSCustomObject]@{ Label = "local test-user path"; Fixed = $true; Pattern = ('C:\Users\' + 'UserTest') },
    [PSCustomObject]@{ Label = "GitHub token"; Fixed = $false; Pattern = 'gh[pousr]_[A-Za-z0-9]{20,}' },
    [PSCustomObject]@{ Label = "OpenAI-style token"; Fixed = $false; Pattern = 'sk-(proj-)?[A-Za-z0-9_-]{20,}' },
    [PSCustomObject]@{ Label = "AWS access key"; Fixed = $false; Pattern = 'AKIA[0-9A-Z]{16}' },
    [PSCustomObject]@{ Label = "private key"; Fixed = $false; Pattern = '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----' }
)

$contentFindings = @()
foreach ($check in $contentChecks) {
    $arguments = @("grep", "-n", "-I")
    if ($check.Fixed) {
        $arguments += "-F"
    }
    else {
        $arguments += "-E"
    }
    $arguments += @("--", $check.Pattern)
    $matches = @(& git @arguments)
    $grepExitCode = $LASTEXITCODE
    if ($grepExitCode -eq 0) {
        $contentFindings += "[$($check.Label)]"
        $contentFindings += $matches
    }
    elseif ($grepExitCode -ne 1) {
        throw "git grep failed while checking $($check.Label)."
    }
}
if ($contentFindings.Count -ne 0) {
    throw "The public snapshot content scan failed:`n$($contentFindings -join [Environment]::NewLine)"
}

Write-Output ("Public snapshot check passed for {0} tracked files." -f $trackedFiles.Count)
