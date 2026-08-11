# SETUP-P1-04-FIX-01 Acceptance Record

## Scope

SETUP-P1-04-FIX-01 corrects cancellation in the guided profile-creation
dialog introduced by SETUP-P1-04. Gateway remains `0.2.0-rc18.dev10`, Chat
Bridge remains `0.2.0-rc19.dev20`, and Windows Setup advances to
`installer-r19`.

## Defect and correction

The profile form uses required onboarding fields. Its dialog close and Cancel
buttons were ordinary submit buttons, so browser constraint validation blocked
them while required fields were empty.

All dialog close and Cancel submit controls now use the native
`formnovalidate` contract. Required-field validation remains active for
`Review creation plan`, while Cancel and the close button can always dismiss
the dialog without changing PLwC state.

## Required environment

Profile creation requires:

- the installed PLwC Gateway and its Python 3.11+ runtime dependencies;
- read and write access for the current user to the configured PLwC profiles,
  config, and workspace directories;
- a browser that permits the authenticated `127.0.0.1` loopback session; and
- a complete Gateway payload containing the public Governor and profile
  onboarding contracts.

Docker Desktop, a running Docker daemon, Qdrant, Node.js, and Chat Bridge are
not required for profile creation itself. Node.js and Chat Bridge are required
only when ChatGPT in the browser is the chosen client route. Docker and Qdrant
remain optional capabilities.

## Verification

- `python -m pytest tests/integration/test_plwc_configuration_ui.py -q`
  returned `10 passed`.
- Python and JavaScript syntax checks passed.
- Live browser verification opened an empty German profile form and confirmed
  that both `Abbrechen` and `Schließen` dismissed it without validation.
- The locally installed configuration pages were updated and matched the
  corrected source files byte-for-byte.
- The complete installer source, payload, integration, and build-identity gate
  returned `66 passed, 0 failed`.
- The production installer-r19 build completed successfully.

## Build artifacts

- Installer:
  `installer/windows/dist/PLwC-Setup-0.2.0-rc18.dev10-installer-r19.exe`
- Installer size: `5,209,707` bytes
- Installer SHA-256:
  `1ad16ccaf8c249678a0fdfeab17eb31af105eeda41a90dbac71d0427cb35f4a4`
- Build identity:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-installer-r19-build-identity.json`
- Build identity SHA-256:
  `637dd04160216769ed853ba9f5100d0b12e85bd891136f813f07500f424a0f3d`
- Payload manifest:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-payload-manifest.json`
- Payload manifest SHA-256:
  `874cfa8c8bc409e4b3e21abb318fd5c91837c71f0c844807d04f7fcc9a53894d`
- Build ID:
  `plwc-windows-setup@0.2.0-rc18.dev10/installer-r19#sha256:1ad16ccaf8c249678a0fdfeab17eb31af105eeda41a90dbac71d0427cb35f4a4`

The build identity binds installer-r19 to evidence package
`SETUP-P1-04-FIX-01`, Gateway `0.2.0-rc18.dev10`, and Node Bridge, browser
extension, and native launcher `0.2.0-rc19.dev20`.
