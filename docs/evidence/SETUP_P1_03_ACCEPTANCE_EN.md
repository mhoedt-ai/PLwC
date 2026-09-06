# SETUP-P1-03 Acceptance Record

## Scope

SETUP-P1-03 adds a client-independent local PLwC configuration page to the
Windows package. It is available to Gateway-only, Claude Desktop MCPB, Codex
STDIO, Odysseus STDIO, and Chat Bridge installations through one Start menu
entry.

Gateway remains `0.2.0-rc18.dev10` and Chat Bridge remains
`0.2.0-rc19.dev20`. The Windows package advances to `installer-r17`.

## Accepted behavior

- The page displays the effective active profile, profile status, source, and
  Gateway version.
- The page lists existing profiles and changes the active profile only through
  a `plwc_governor` profile-activation Plan and confirmed Apply.
- The confirmation is bound to the stable, security-relevant plan fields by a
  SHA-256 digest. A changed plan must be reviewed again.
- Memory, Persona, and Temperament thresholds accept effective integer values
  from 1 through 1,000,000.
- Persona Layer and Qdrant are controlled by native binary switches.
- These five values are written atomically to the canonical shared file
  `%APPDATA%\PLwC\config\gateway-settings.json`. Existing supported path and
  bootstrap values are preserved.
- Persona Layer changes affect future compiled context and do not rewrite
  `PERSONA.md`.
- Enabling Qdrant permits use of a configured index and does not silently
  create or rebuild one.
- Saved shared values are available to every PLwC client on its next Gateway
  call. A client restart is needed only for a host that retains stale state.
- English and German pages are installed with no external scripts, styles,
  images, fonts, telemetry, or network dependencies.
- The localized Getting Started guide explains the shared configuration path
  and its effect for every supported client type.

## Local security boundary

- The service binds to an ephemeral port on `127.0.0.1` only.
- A random bootstrap token is exchanged for an HttpOnly, SameSite=Strict
  session cookie and removed from the address bar by redirect.
- API requests require the exact loopback Host, local Origin, session cookie,
  JSON content type, and a PLwC-specific request header.
- Responses deny framing, sniffing, referrer leakage, caching, and all content
  sources except the local page's own CSS, JavaScript, and API connection.
- The service has a bounded request size and exits after inactivity.
- Shared settings are written through a same-directory temporary file,
  `fsync`, and atomic replacement. The target is constrained to the PLwC
  configuration root.

## Setup integration

- Setup stages the five configuration assets under `common/configuration` and
  hashes them in the payload manifest.
- The Start menu entry resolves the selected Python runtime and passes the
  exact project, Gateway, workspace, profile, and security paths selected in
  Setup.
- The configuration script bootstraps `plwc_gateway` from the selected custom
  Gateway source tree, including non-default runtime locations.
- The former configuration-folder shortcut remains available as a separate
  advanced entry.
- The Finish page offers the configuration page as an optional unchecked
  action.

## Verification

Automated verification completed on 2026-08-08:

- `python -m pytest tests/integration/test_plwc_configuration_ui.py -q`
  returned `8 passed`.
- `python -m py_compile installer/windows/assets/configuration/plwc-config.py`
  passed.
- `node --check installer/windows/assets/configuration/plwc-config.js` passed.
- The installer source-contract phase passed, including the new local
  configuration contracts.
- The complete installer contract and payload gate returned
  `66 passed, 0 failed`.
- Browser verification loaded the live German page from its authenticated
  loopback service against an existing PLwC runtime.
- Desktop layout, a 390 x 844 responsive viewport, runtime values, switches,
  profile selection, and the Governor plan dialog were inspected. The narrow
  layout had no horizontal overflow.
- No Governor Apply or shared-settings write was performed during visual
  verification.

## Build artifacts

- Installer:
  `installer/windows/dist/PLwC-Setup-0.2.0-rc18.dev10-installer-r17.exe`
- Installer size: `5,205,258` bytes
- Installer SHA-256:
  `7bd13462ca5151b20e14b32f11cbbda6a8811615804d467a36164031e170025e`
- Build identity:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-installer-r17-build-identity.json`
- Build identity SHA-256:
  `1cf3886ccde45b2d184d8be4083bc123f003ac64cbb94b2ec69fca2e918cd42f`
- Payload manifest:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-payload-manifest.json`
- Payload manifest SHA-256:
  `e4095e38ed2be275bf33b7b6285c7d78f9955eafe13ddb3fc32a4069fdc56940`
- Build ID:
  `plwc-windows-setup@0.2.0-rc18.dev10/installer-r17#sha256:7bd13462ca5151b20e14b32f11cbbda6a8811615804d467a36164031e170025e`

The build identity binds the installer to evidence package `SETUP-P1-03`,
Gateway `0.2.0-rc18.dev10`, and Node Bridge, browser extension, and native
launcher `0.2.0-rc19.dev20`.
