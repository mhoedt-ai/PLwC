# SETUP-P1-04 Acceptance Record

## Scope

SETUP-P1-04 extends the client-independent local PLwC configuration page with
governed profile creation and connects it to the localized Getting Started
guide. The Windows installer also places a direct PLwC Configuration shortcut
on the current user's desktop.

Gateway remains `0.2.0-rc18.dev10` and Chat Bridge remains
`0.2.0-rc19.dev20`. The Windows package advances to `installer-r18`.

## Accepted behavior

- The configuration page provides a bilingual, guided `New profile` workflow.
- The form covers identity, role, form of address, collaboration style,
  strictness, language, memory scope, confirmation boundaries, project
  context, and optional special instructions.
- Persona-specific answers are required only while the shared Persona Layer is
  enabled.
- Reviewing the form calls the public `plwc_governor` profile-creation Plan and
  does not create a directory or write a protected file.
- The review step displays validation, target directory, activation intent,
  missing answers, and all protected files that would be created.
- Apply requires an explicit confirmation and a SHA-256 digest bound to the
  normalized onboarding answers and stable security-relevant plan fields.
- Changed answers or a changed plan invalidate the confirmation and require a
  new review.
- A successful Apply creates the complete governed profile and activates it
  through PLwC state; the configuration page never creates profile files
  directly.
- Desktop and narrow browser layouts remain usable without horizontal
  overflow.

## Guide and desktop integration

- The configuration page links to `Getting Started`.
- The Getting Started guide links back to the configuration page and explains
  governed profile creation in plain language.
- Both pages are served by the same authenticated loopback session. The guide
  no longer depends on a browser opening an installed HTML file directly.
- The Start menu retains entries for both pages.
- Setup creates a direct `PLwC Configuration` shortcut on the current user's
  desktop and removes it through the normal uninstall record.
- The Finish page opens Getting Started through the local configuration
  launcher by default and keeps direct configuration launch as an optional
  action.

## Local security boundary

- The service binds only to an ephemeral `127.0.0.1` port.
- A random one-time URL token is exchanged for an HttpOnly, SameSite=Strict
  cookie before either page is served.
- Configuration writes retain exact Host, Origin, cookie, JSON content type,
  request-header, size, path-containment, and atomic-write checks.
- Getting Started remains local, has no remote assets or telemetry, and is
  covered by the same content security and anti-framing headers.

## Verification

Automated and browser verification completed on 2026-08-09:

- `python -m pytest tests/integration/test_plwc_configuration_ui.py -q`
  returned `10 passed`.
- `python -m py_compile installer/windows/assets/configuration/plwc-config.py`
  passed.
- `node --check installer/windows/assets/configuration/plwc-config.js` passed.
- Live browser verification exercised the German profile form and Governor
  plan against an existing PLwC runtime without applying it.
- Desktop and `390 x 844` views were inspected; the narrow view had no
  horizontal overflow.
- The preview Plan listed all seven target files and proposed activation.
- The preview profile directory did not exist after the browser test.
- Live installed-page verification followed Configuration to Getting Started
  and back to Configuration inside one authenticated loopback session.
- The complete installer source, payload, integration, and build-identity gate
  returned `66 passed, 0 failed`.
- The production build completed successfully and bound all component versions
  and this evidence package into the r18 build identity.

## Build artifacts

- Installer:
  `installer/windows/dist/PLwC-Setup-0.2.0-rc18.dev10-installer-r18.exe`
- Installer size: `5,209,999` bytes
- Installer SHA-256:
  `9827aea489de510b9de242dcc4be5143d439e04b2c4c3493dafe5c2818a26c52`
- Build identity:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-installer-r18-build-identity.json`
- Build identity SHA-256:
  `d8e5bdada916b20d4f650984377fe10c430bbfd016f897b7259dda62e467e2cb`
- Payload manifest:
  `installer/windows/dist/PLwC-0.2.0-rc18.dev10-payload-manifest.json`
- Payload manifest SHA-256:
  `31d190259bf6a06073bef37ef5dc8254d1f1d5f998372573203181ef79a9514b`
- Build ID:
  `plwc-windows-setup@0.2.0-rc18.dev10/installer-r18#sha256:9827aea489de510b9de242dcc4be5143d439e04b2c4c3493dafe5c2818a26c52`

The build identity binds the installer to evidence package `SETUP-P1-04`,
Gateway `0.2.0-rc18.dev10`, and Node Bridge, browser extension, and native
launcher `0.2.0-rc19.dev20`.
