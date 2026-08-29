# Troubleshooting

## Docker Missing

PLwC runs in Safe Mode.

Sandboxed code execution is disabled until Docker is installed and running.

## Claude Shows Multiple MCP Servers

This is a configuration error.

Only `plwc-gateway` should be active.

## Windows Shows Unknown Publisher

The current r24 Setup candidate is explicitly unsigned. Verify that the file is
named `PLwC-Setup-1.0.0-installer-r24.exe` and that its SHA-256 is exactly:

```text
b00c5298bf6faa76c5910ecbb36497a8aa4764a8a3720f73a450851a3fc3e4d0
```

Stop if the hash differs. Do not substitute an older installer with a similar
name. The public reviewer artifact and status are recorded in
[`evidence/CHAT_BRIDGE_1_0_INSTALLER_R24_ACCEPTANCE_EN.md`](evidence/CHAT_BRIDGE_1_0_INSTALLER_R24_ACCEPTANCE_EN.md).

## Setup Asks For Every Directory During An Update

A complete installation should be detected before the directory and runtime
pages. If Setup asks again, inspect the installation summary and
`selection.ini` under `%APPDATA%\PLwC\config\installer` (or the selected
configuration root). The prior installation may be incomplete or its persisted
state may be missing.

Do not create new version-suffixed Gateway or Bridge directories as a repair.
New installs use `app\gateway` and `app\bridge`; valid older paths are preserved
automatically.

## Workspace Change Is Not Visible

Open **PLwC Configuration**, enter an absolute path under the workspace-change
control and select **Save settings**. PLwC creates missing `Tagebuch`, `Temp`
and `Trashcan` directories but does not move existing files. Restart only the
client that still shows the old value.

The shared value is stored in `gateway-settings.json` and mirrored into the
installer selection state so later updates continue to use it.

## Duplicate PLwC Configuration Shortcuts

r24 owns one canonical desktop shortcut named `PLwC-Konfiguration`. Run r24 in
update or repair mode to remove the owned legacy name variants and recreate the
shortcut with the PLwC icon. A manually created shortcut is outside this cleanup
contract.

## Chat Bridge Does Not Reach 8 / 8 Tools

1. Open the PLwC panel and select **Status**.
2. Select **Reconnect** once.
3. Confirm that the endpoint is `ws://127.0.0.1:3007/message`.
4. If the Launcher is missing, run Windows Setup r24 in repair mode.
5. If the Launcher is available but the Bridge remains offline, inspect the
   setup summary and Bridge logs referenced by the installed diagnostics.

Setup registers `plwc.chat_bridge.launcher` per user for Chrome, Edge and
Brave. Do not run maintainer scripts from a repository as an end-user repair.

## Browser Store Page Is Unavailable

The Chrome and Edge 1.0 items were submitted for review on 2026-08-30. Chrome
remains private with automatic publication disabled; Edge remains hidden and
link-only. Neither Store-signed package is installable until its review or
certification gate provides the configured test channel. An unavailable public
listing is therefore expected before that gate.

Loading the installed extension folder in Developer mode uses the separate
development identity. It can test local behavior, but it cannot prove Chrome or
Edge Store-ID acceptance.
