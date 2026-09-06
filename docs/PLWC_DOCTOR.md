# PLwC Doctor

PLwC exposes exactly one visible Doctor in the local **PLwC Configuration**
page. CLU supplies the read-only diagnosis; deterministic installer-owned code
plans and applies only allowlisted repairs.

## Diagnosis

Diagnosis is guaranteed not to change installation, profile, workspace,
configuration, task, shortcut, process, or registry state. It records a stable
snapshot ID and checks, where available:

- product, Gateway, Bridge, Native Launcher, extension, and configuration UI
  identities and compatibility;
- the exact eight-tool Gateway postflight;
- versionless active Gateway and Bridge paths;
- Native Messaging manifests and permitted origins;
- Bridge autostart shortcut and owned legacy tasks;
- port 3007 ownership without stopping any process;
- configuration shortcut and icon;
- shared configuration, active profile, every profile directory, and workspace;
- last launcher/extension evidence and trusted update state.

The public MCP Doctor access remains the read-only `operation=doctor` mode of
`plwc_profile`; it is not a second repair program.

## Repair plan

A plan is bound to the exact diagnosis snapshot and has an immutable plan ID.
It lists every intended write. Unknown actions, changed plan content, a stale
snapshot, or a missing explicit confirmation fail closed.

Allowlisted repairs can recreate known PLwC shortcuts/manifests, remove proven
obsolete PLwC-owned tasks, restore approved path references, and perform the
same hard installation postflight used by r26 Setup. They cannot invent profile
content, delete workspace data, terminate an unproven process, change profile
substance, or install an update.

## Apply, audit, and rollback

Before an apply, PLwC verifies that the current snapshot still matches the
reviewed plan. Replaced files are backed up, each action and outcome is audited,
and the complete postflight runs afterward. A failure rolls back completed
steps where supported and reports the backup/audit location. A second run after
a successful repair must contain no changes.

Profile creation and profile activation are governed profile flows, not Doctor
repairs. They always require their own confirmation and are never covered by a
standing write approval.
