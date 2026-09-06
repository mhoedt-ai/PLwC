# PLwC Chat Bridge 1.0 / Windows Installer r25 Evidence

Date: 2026-09-01

Status: build and contract gates passed; clean-Windows acceptance pending.
This record does not supersede the historical r24 acceptance record and does
not yet authorize publication of r25.

## Candidate identity

- Artifact: `PLwC-Setup-1.0.0-installer-r25.exe`
- Size: `5,221,208` bytes
- SHA-256: `e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c`
- Build ID: `plwc-windows-setup@1.0.0/installer-r25#sha256:e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c`
- Signing mode: `explicit_unsigned`
- Setup Authenticode status: `NotSigned`
- Native Launcher Authenticode status: `NotSigned`
- Payload manifest SHA-256: `46ebcf9266e24cd8e6f1bac227588c7e832cd330e8929b09f5e52aaf8c567e8d`

The candidate is isolated below `installer/windows/.unsigned-build-r25/`. It
does not overwrite the historical r24 artifact or evidence.

## r25 change boundary

- Replaces the PLwC scheduled-task sign-in path with a per-user Startup-folder
  shortcut targeting `plwc-chat-bridge-launcher.exe` directly.
- Adds native `--start` and `--delay-seconds` modes. Success requires the exact
  build identity and exactly eight public tools.
- Registers, verifies and unregisters Native Messaging through the launcher
  directly. The normal setup path no longer invokes PowerShell or
  `ExecutionPolicy Bypass`.
- Removes a legacy scheduled task only when its action identifies the prior
  PLwC PowerShell start script. A foreign same-name task is preserved.
- Makes Chat Bridge setup fail closed: `installation_completed/status=success`
  is recorded only after launcher, Startup shortcut, build identity and eight
  tools pass postflight.

Gateway, Node Bridge, browser extension and Native Launcher product identities
remain `1.0.0`. The Chrome and Edge Store packages are outside this installer
change and were not modified or resubmitted.

## Automated evidence

- Pester installer contract suite: `70 passed, 0 failed`.
- Isolated `build.ps1 -ValidateOnly`: passed; canonical r24 evidence paths were
  not used as generated output.
- Native C# launcher compilation and embedded `--build-identity`: passed.
- Inno Setup compiler against the verified r25 stage: exit code `0`.
- Explicit unsigned production build: passed, including unsigned assertions,
  payload manifest and external build identity.
- Fail-closed negative case: the real staged launcher was copied into an
  intentionally incomplete layout and invoked with `--start`. It returned a
  non-zero exit code with `ok=false`, `state=failed`,
  `code=bridge_files_missing` and `toolCount=0`. The installer contract also
  proves that the successful completion record occurs only after the postflight
  call and that a failed postflight raises an installer error.

## Remaining acceptance gate

Install this exact byte-identical EXE on a clean Windows 11 system with Chat
Bridge selected. Acceptance requires:

1. no Trend Micro/Apex One behavior block;
2. no PLwC scheduled task and no PowerShell/`ExecutionPolicy Bypass` sign-in
   action;
3. one current-user Startup shortcut targeting the native launcher with a
   20-second delay;
4. Native Messaging registered for Chrome, Edge and Brave approved origins;
5. exact installed build identity and `Tools 8 / 8`;
6. reboot/sign-in recovery followed by browser Reconnect;
7. a deliberately broken postflight attempt must not show successful Setup
   completion and must record `chat_bridge_postflight/status=failure`.

Only after those checks pass may this record be amended to clean-Windows
accepted and r25 considered as a replacement candidate for r24.
