[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$builder = Join-Path $scriptRoot "build-store-packages.ps1"
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("plwc-store-package-test-" + [Guid]::NewGuid().ToString("N"))
$firstOutput = Join-Path $temporaryRoot "first"
$secondOutput = Join-Path $temporaryRoot "second"

try {
    & $builder -OutputDirectory $firstOutput | Out-Null
    & $builder -OutputDirectory $secondOutput -SkipBuild | Out-Null

    $firstFiles = @(Get-ChildItem -LiteralPath $firstOutput -File | Sort-Object Name)
    $secondFiles = @(Get-ChildItem -LiteralPath $secondOutput -File | Sort-Object Name)
    if ($firstFiles.Count -ne 4 -or $secondFiles.Count -ne 4) {
        throw "Store package test expected two ZIPs and two build-identity sidecars per build."
    }
    if ((ConvertTo-Json -Compress @($firstFiles.Name)) -ne (ConvertTo-Json -Compress @($secondFiles.Name))) {
        throw "Store package test builds produced different file inventories."
    }

    foreach ($firstFile in $firstFiles) {
        $secondFile = Join-Path $secondOutput $firstFile.Name
        $firstHash = (Get-FileHash -LiteralPath $firstFile.FullName -Algorithm SHA256).Hash
        $secondHash = (Get-FileHash -LiteralPath $secondFile -Algorithm SHA256).Hash
        if ($firstHash -ne $secondHash) {
            throw "Store package output is not reproducible: $($firstFile.Name)"
        }
    }

    $sidecars = @($firstFiles | Where-Object { $_.Name -like '*-build-identity.json' })
    $expectedTargets = @("chrome-brave", "edge")
    foreach ($sidecarFile in $sidecars) {
        $sidecar = Get-Content -LiteralPath $sidecarFile.FullName -Raw | ConvertFrom-Json
        if (
            $sidecar.target -notin $expectedTargets -or
            $sidecar.expectedExtensionId -notmatch '^[a-p]{32}$' -or
            $sidecar.expectedNativeMessagingOrigin -ne "chrome-extension://$($sidecar.expectedExtensionId)/" -or
            $sidecar.entries.Count -ne 4 -or
            $sidecar.entries -notcontains "manifest.json"
        ) {
            throw "Store package build-identity sidecar is invalid: $($sidecarFile.Name)"
        }
        $archivePath = Join-Path $firstOutput $sidecar.archive.fileName
        if (
            -not (Test-Path -LiteralPath $archivePath -PathType Leaf) -or
            (Get-Item -LiteralPath $archivePath).Length -ne $sidecar.archive.bytes -or
            (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $sidecar.archive.sha256
        ) {
            throw "Store package sidecar does not bind its archive: $($sidecarFile.Name)"
        }
    }

    Write-Output "Store package reproducibility, inventory, identity, and secret-scan tests passed."
}
finally {
    if (Test-Path -LiteralPath $temporaryRoot) {
        Remove-Item -LiteralPath $temporaryRoot -Recurse -Force
    }
}
