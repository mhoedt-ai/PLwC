# G0 open decisions – Windows Installer r27

Stand: 2026-09-05

Status: **PASS – keine G0-blockierende Entscheidung offen**

## Fest entschieden

- Revision `installer-r27` statt Änderung oder Ersetzung des r26-Artefakts.
- Drei PLwC-eigene Runtime-Images für Document Worker, Node Runner und Python
  Runner.
- GHCR-Namespace `ghcr.io/mhoedt-ai`.
- Zielplattform für r27: `linux/amd64` unter Docker Desktop/WSL2 auf Windows 11.
- Digest-only-Vertrauen, explizites Opt-in, anonymer Endnutzer-Pull und
  ehrlicher Safe Mode.
- Keine eingebetteten Registry-Zugangsdaten.
- Vollständige Fehlerbericht- und Diagnoseexportpflicht.
- Gesonderte Freigaben vor Upload, öffentlicher Sichtbarkeit, Produktionsbuild
  und Veröffentlichung.

## Nachgelagerte, nicht G0-blockierende Bestimmungen

Diese Werte werden aus reproduzierbaren Builds oder Messungen abgeleitet und
sind keine offenen Produktentscheidungen:

- endgültige drei Image-Digests;
- komprimierte Transfer- und lokale Speichergrößen;
- konkrete gepinnte Basis-Digests und Debian-Snapshotstände;
- konkrete SBOM-, Provenienz- und Schwachstellenbericht-Hashes;
- exakter r27-EXE-Hash und Signaturstatus.

Wenn eine dieser Bestimmungen eine Änderung der G0-Grenzen erfordert, wird G0
gemäß globaler Stop-/Go-Regel erneut geöffnet.

