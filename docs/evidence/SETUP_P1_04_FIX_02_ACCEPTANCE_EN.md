# SETUP-P1-04-FIX-02 Acceptance Record

## Scope

SETUP-P1-04-FIX-02 aligns the localized Getting Started header with the PLwC
Configuration header. Gateway remains `0.2.0-rc18.dev10`, Chat Bridge remains
`0.2.0-rc19.dev20`, and Windows Setup advances to `installer-r20`.

## Accepted behavior

- `Open configuration` is removed from the horizontally scrolling guide
  section navigation.
- The link is placed at the upper right of the dark guide header, mirroring
  the `Getting Started` link on the configuration page.
- The guide header uses the same maximum width, title scale, spacing, dark
  background, green border, link treatment, status indicator, and responsive
  collapse as the configuration page.
- A local-documentation status appears beside the navigation link.
- The section navigation now begins with `Installation paths` or
  `Installationswege` and contains section links only.
- English and German pages retain a direct bidirectional link.

## Verification

- `python -m pytest tests/integration/test_plwc_configuration_ui.py -q`
  returned `10 passed`.
- The complete Windows installer Pester contract suite returned `66 passed,
  0 failed`.
- The live installed German guide was inspected at the normal browser width.
- The header link, local-documentation state, and section-navigation order
  were confirmed through the accessibility tree.
- A `390 x 844` view had no horizontal page overflow; the section navigation
  remains intentionally horizontally scrollable within its own band.
- Installed guide files matched the corrected source files byte-for-byte.

## Build artifacts

- Installer:
  `installer/windows/dist/PLwC-Setup-0.2.0-rc18.dev10-installer-r20.exe`
- Size: `5,209,699` bytes
- Installer SHA-256:
  `ff3fdb880519e1a5a6c6e3b79129ff818d4cd14ced3a72ed8c76af63a613e804`
- Build identity:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-installer-r20-build-identity.json`
- Build ID:
  `plwc-windows-setup@0.2.0-rc18.dev10/installer-r20#sha256:ff3fdb880519e1a5a6c6e3b79129ff818d4cd14ced3a72ed8c76af63a613e804`
- Payload manifest SHA-256:
  `9cdb011dd7b787c19c5e44a8bf077d9aa78035d7af3a3b058c887f868f065e6a`
- The copy in the user's Downloads directory matched the release artifact
  byte-for-byte by SHA-256.
