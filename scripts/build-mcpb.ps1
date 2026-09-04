[CmdletBinding()]
param()

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$repoRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$outputRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot "build\mcpb"))
$fixedTimestamp = [DateTimeOffset]::new(2000, 1, 1, 0, 0, 0, [TimeSpan]::Zero)

function Copy-PackageFile {
    param(
        [Parameter(Mandatory = $true)][string] $RelativePath,
        [Parameter(Mandatory = $true)][string] $StageRoot
    )

    $source = [IO.Path]::GetFullPath((Join-Path $repoRoot $RelativePath))
    if (-not $source.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Required MCPB input is missing or unsafe: $RelativePath"
    }
    $destination = Join-Path $StageRoot $RelativePath
    [IO.Directory]::CreateDirectory((Split-Path -Parent $destination)) | Out-Null
    [IO.File]::Copy($source, $destination, $true)
}

function Copy-PackageTree {
    param(
        [Parameter(Mandatory = $true)][string] $RelativeRoot,
        [Parameter(Mandatory = $true)][string] $StageRoot
    )

    $sourceRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot $RelativeRoot))
    if (-not $sourceRoot.StartsWith($repoRoot, [StringComparison]::OrdinalIgnoreCase) -or
        -not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
        throw "Required MCPB input tree is missing or unsafe: $RelativeRoot"
    }
    $reparsePoints = @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -Force | Where-Object {
        ($_.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
    })
    if ($reparsePoints.Count -gt 0) {
        throw "MCPB input contains a reparse point: $($reparsePoints[0].FullName)"
    }
    foreach ($file in Get-ChildItem -LiteralPath $sourceRoot -Recurse -File -Force) {
        if ($file.Name -match '\.pyc$' -or $file.FullName -match '\\__pycache__\\') {
            continue
        }
        $relative = $file.FullName.Substring($repoRoot.Length).TrimStart('\', '/')
        Copy-PackageFile -RelativePath $relative -StageRoot $StageRoot
    }
}

$manifest = Get-Content -LiteralPath (Join-Path $repoRoot "manifest.json") -Raw | ConvertFrom-Json
$projectText = Get-Content -LiteralPath (Join-Path $repoRoot "pyproject.toml") -Raw
$projectMatch = [regex]::Match($projectText, '(?m)^version\s*=\s*"([^"]+)"\s*$')
$packageVersion = [string] $manifest.version
if (-not $projectMatch.Success -or
    ($projectMatch.Groups[1].Value -replace '-', '') -ne ($packageVersion -replace '-', '')) {
    throw "MCPB manifest and Python package versions are inconsistent."
}
if ($packageVersion -notmatch '^\d+\.\d+\.\d+$') {
    throw "Final MCPB version must be stable semantic versioning: $packageVersion"
}

$stageRoot = [IO.Path]::GetFullPath((Join-Path $outputRoot "plwc-gateway-$packageVersion"))
$archivePath = [IO.Path]::GetFullPath((Join-Path $outputRoot "plwc-gateway-$packageVersion.mcpb"))
$expectedStageRoot = Join-Path $outputRoot "plwc-gateway-$packageVersion"
$expectedArchivePath = Join-Path $outputRoot "plwc-gateway-$packageVersion.mcpb"
if (-not $stageRoot.Equals($expectedStageRoot, [StringComparison]::OrdinalIgnoreCase) -or
    -not $archivePath.Equals($expectedArchivePath, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing unsafe MCPB output paths."
}
if (Test-Path -LiteralPath $stageRoot) {
    [IO.Directory]::Delete($stageRoot, $true)
}
if (Test-Path -LiteralPath $archivePath) {
    [IO.File]::Delete($archivePath)
}
[IO.Directory]::CreateDirectory($stageRoot) | Out-Null

foreach ($file in @(
    "LICENSE",
    "manifest.json",
    "plwc-icon-512.png",
    "pyproject.toml",
    "README.md",
    "requirements.txt",
    "server.py",
    "config\security.yaml.example",
    "docker\document-worker\Dockerfile",
    "docker\document-worker\README.md",
    "docker\document-worker\requirements-doc-worker.lock",
    "docker\document-worker\requirements-doc-worker.txt",
    "docker\document-worker\wheelhouse-manifest.csv",
    "docker\document-worker\wheelhouse-manifest.json",
    "docker\document-worker\wheelhouse\.gitkeep",
    "docker\node-runner\Dockerfile",
    "docker\node-runner\README.md"
)) {
    Copy-PackageFile -RelativePath $file -StageRoot $stageRoot
}
foreach ($tree in @(
    "docker\document-worker\worker",
    "profiles\template",
    "src\plwc_gateway"
)) {
    Copy-PackageTree -RelativeRoot $tree -StageRoot $stageRoot
}
foreach ($doc in @(
    "AUDIT_LOG.md",
    "CONFIGURATION.md",
    "FIRST_RUN.md",
    "INSTALLATION.md",
    "ONBOARDING.md",
    "PROJECT_SCOPE.md",
    "QUICKSTART_CLAUDE_DESKTOP.md",
    "SAFE_MODE.md",
    "SECURITY_MODEL.md",
    "TOOLS.md",
    "TROUBLESHOOTING.md"
)) {
    Copy-PackageFile -RelativePath ("docs\$doc") -StageRoot $stageRoot
}

$forbiddenPathPattern = '(?i)(?:^|/)(?:\.env(?:\.|$)|workspace|logs?|tests?|__pycache__|profile_backups?|\.git)(?:/|$)|(?<!\.example)security\.ya?ml$|\.mcpb$'
$files = @(Get-ChildItem -LiteralPath $stageRoot -Recurse -File -Force | Sort-Object FullName)
foreach ($file in $files) {
    $relative = $file.FullName.Substring($stageRoot.Length).TrimStart('\', '/').Replace('\', '/')
    if ($relative -match $forbiddenPathPattern) {
        throw "Privacy filter rejected MCPB path: $relative"
    }
    if ($file.Extension -in @(".json", ".md", ".py", ".toml", ".txt", ".yaml", ".yml", ".csv", ".example")) {
        $content = Get-Content -LiteralPath $file.FullName -Raw
        if ($content -match '\bAKIA[0-9A-Z]{16}\b' -or
            $content -match '\bgh[pousr]_[A-Za-z0-9]{36,}\b' -or
            $content -match '\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b' -or
            $content -match '-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----') {
            throw "Secret scan rejected MCPB file: $relative"
        }
    }
    $file.LastWriteTimeUtc = $fixedTimestamp.UtcDateTime
}

Add-Type -AssemblyName System.IO.Compression
$archiveStream = [IO.File]::Open($archivePath, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
try {
    $archive = [IO.Compression.ZipArchive]::new($archiveStream, [IO.Compression.ZipArchiveMode]::Create, $true)
    try {
        foreach ($file in $files) {
            $relative = $file.FullName.Substring($stageRoot.Length).TrimStart('\', '/').Replace('\', '/')
            $entry = $archive.CreateEntry($relative, [IO.Compression.CompressionLevel]::Optimal)
            $entry.LastWriteTime = $fixedTimestamp
            $input = [IO.File]::OpenRead($file.FullName)
            $output = $entry.Open()
            try {
                $input.CopyTo($output)
            }
            finally {
                $output.Dispose()
                $input.Dispose()
            }
        }
    }
    finally {
        $archive.Dispose()
    }
}
finally {
    $archiveStream.Dispose()
}

$hash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Host "MCPB build complete: $archivePath"
Write-Host "Files: $($files.Count)"
Write-Host "SHA256: $hash"
