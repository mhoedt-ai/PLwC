# Chat Bridge P1-03 Acceptance Evidence

Date: 2026-07-30

Scope: BRIDGE-P1-03 only. The 1.0.0 version alignment, Setup G4/G5 acceptance,
and final release test remain outside this acceptance pass.

## Outcome

BRIDGE-P1-03 passes.

`integrations/plwc-chat-bridge/build-identity.json` is the canonical identity
source for the complete Chat Bridge payload. It defines the common build ID
`plwc-chat-bridge@0.2.0-rc19.dev18`, the Installer component and directory
identity, and the following independently visible component versions:

| Component | Internal version |
| --- | --- |
| Node Bridge | `0.2.0-rc19.dev12` |
| Browser extension | `0.2.0-rc19.dev18` |
| Native launcher | `0.2.0-rc19.dev18` |

The Node Bridge returns the identity through `build/identity`. Its health check
verifies that identity before accepting the exact eight-tool contract.

The extension embeds the same document at build time, verifies every field
after connecting, and keeps tool execution locked when the identity is invalid
or mismatched. Its Primer and Status tab expose the common build ID and all
three component versions.

The native launcher embeds the same JSON document as a compiled resource. It
rejects an extension request for another build, verifies the Bridge build and
component versions through the health check, includes the identity in native
messaging responses, and prints it through `--build-identity`.

PLwC Windows Setup stages the canonical document, compiles the launcher from
that exact input, uses the shared release version for the installation
directory, and records the common build ID plus all component versions in the
SHA-256 payload manifest.

## Acceptance Matrix

| Requirement | Status | Evidence |
| --- | --- | --- |
| Node Bridge provides a common build identity | PASS | `build/identity` returns the canonical identity. Bridge health rejects another `buildId` before checking tools. |
| Browser extension provides the same identity | PASS | Build scripts inject the canonical JSON into production, test, and browser-fixture bundles. Runtime validation compares every identity field. |
| Native launcher provides the same identity | PASS | The JSON is embedded as `Plwc.ChatBridge.BuildIdentity.json`; `--build-identity` returns the complete parsed document. |
| Identity is attributable to the Installer | PASS | The identity names Installer component `chat-bridge` and directory `chat-bridge-0.2.0-rc19.dev18`. The payload manifest references `chat-bridge/build-identity.json` and repeats the common `buildId`. |
| Different internal versions remain visible | PASS | The canonical document, Installer payload manifest, Primer, Status tab, Bridge RPC, health output, and launcher output retain all three component versions. |
| Mismatches fail closed | PASS | Bridge health rejects another build. The extension reports mismatched fields and locks execution. The native launcher validates both its requested build and all Bridge component versions. |
| Source versions cannot silently drift | PASS | Extension and Installer builds compare the canonical release, Node Bridge, extension package, and extension manifest versions before producing artifacts. |

## Verification Commands

Executed in
`<REPOSITORY_ROOT>\integrations\plwc-chat-bridge`:

```powershell
npm run check:windows
```

Result: production Bridge and extension builds passed, all 23 Node Bridge tests
passed, all 123 extension tests passed, and the native launcher compiled with
the embedded canonical identity.

Executed from the repository root:

```powershell
python -m pytest tests/integration/test_chat_bridge_contract.py -q
```

Result: all 7 cross-component contract tests passed.

Executed in `<REPOSITORY_ROOT>\installer\windows`:

```powershell
.\build.ps1 -ValidateOnly
Invoke-Pester -Script .\tests\installer-contract.Tests.ps1 -PassThru
```

Result: the full payload was rebuilt and staged without invoking ISCC. The
staged launcher identity matched the staged canonical JSON. All 49 Installer
source and payload contract tests passed.

The staged payload manifest contains:

```json
{
  "id": "chat-bridge",
  "version": "0.2.0-rc19.dev18",
  "buildId": "plwc-chat-bridge@0.2.0-rc19.dev18",
  "identityPath": "chat-bridge/build-identity.json",
  "components": {
    "nodeBridge": "0.2.0-rc19.dev12",
    "browserExtension": "0.2.0-rc19.dev18",
    "nativeLauncher": "0.2.0-rc19.dev18"
  }
}
```

`git diff --check` passed with line-ending conversion warnings only.

## Browser Smoke

The local browser fixture was rebuilt and served over loopback HTTP. The Status
tab was inspected at the default desktop viewport and at an explicit
800 by 900 viewport.

The common build ID and all component versions remained readable. Long values
wrapped inside the status grid without overlap. Below the responsive breakpoint
the panel started collapsed, remained user-openable, and the expanded Status
view stayed internally scrollable. The temporary viewport override, browser tab,
HTTP server, and browser session were cleaned up after verification.

## Implementation Boundary

- `build-identity.json` is the canonical shared source.
- `bridge/src/build-identity.ts`, `bridge/src/server.ts`, and
  `bridge/src/healthcheck.ts` own Node runtime loading and verification.
- `extension/src/shared/build-identity.ts` owns the extension parser and
  full-field comparison.
- `extension/src/background/index.ts` and `native-launcher.ts` enforce the
  runtime lock.
- `native/launcher-host/Plwc.ChatBridge.NativeLauncher.cs` owns embedded native
  identity reporting and Bridge verification.
- `installer/windows/build.ps1` owns payload attribution and staged
  cross-component validation.

## Non-P1-03 Items

- No version was changed to 1.0.0.
- No release Installer executable was produced; the Installer run used
  `-ValidateOnly`.
- No clean-machine or upgrade VM acceptance was claimed.
