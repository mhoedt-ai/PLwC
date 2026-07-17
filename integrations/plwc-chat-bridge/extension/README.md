# Extension Source Boundary

This directory will hold the PLwC Chat Bridge browser extension source after
the upstream-derived prototype is reduced or imported as a reviewable patch
series.

## Required UI Surface

- Header name: `PLwC Chat Bridge`.
- Icon: derived from `../../../plwc-icon-512.png`.
- Tabs: `PLwC Tools`, `Primer`, `Policy`, `Status`, `Settings`.
- Theme: black/green terminal style with monospace text.
- Host layout: right dock or movable panel that never blocks the host chat menu.
- Prompt flow: versioned PLwC Bridge Primer, not generic prompt injection.

## Required Isolation

Injected CSS must be shadow-DOM isolated or strongly namespaced. Host
navigation, chat list and composer styles must remain untouched.
