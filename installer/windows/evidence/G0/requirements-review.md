# G0 requirements review – Windows Installer r27

Stand: 2026-09-05

Entscheidung: **PASS / GO zu G1**

Baseline-Commit vor der r27-Dokumentation:
`a4c4457ddc56013dac475931a683bbdd027df8bd`

Installerkandidat: **nicht vorhanden / nicht anwendbar in G0**

## Anlass

Der unveröffentlichte r26-Kandidat
`d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
stellte auf einem realen Windows-11-System das erforderliche
Document-Worker-Image nicht bereit. Ein separater erneuter Lauf endete im
Preflight mit Exitcode 1, ohne den in der UI genannten Bericht in den
Diagnoseexport aufzunehmen. Beide Befunde sind als
`WIN11-R26-IMAGE-001` und `WIN11-R26-PREFLIGHT-001` in der normativen Baseline
erfasst.

## Reviewumfang

- UR-001 bis UR-016 wurden auf Eindeutigkeit, Testbarkeit und
  Widerspruchsfreiheit geprüft.
- SR-001 bis SR-011 wurden gegen Installations-, Security-, Privacy-,
  Container-Supply-Chain- und Freigabegrenzen geprüft.
- Jede neue r27-Anforderung besitzt Designobjekte, Verifikationsmethoden,
  spätere Gates und benannte Evidenz.

## Festgelegte r27-Entscheidungen

1. Korrekturen verwenden ausschließlich die neue Revision `installer-r27`;
   r26 bleibt unveränderliche historische Evidenz.
2. PLwC kontrolliert drei Runtime-Images: Document Worker, Node Runner und
   Python Runner für `linux/amd64`.
3. Kanonische Distribution ist `ghcr.io/mhoedt-ai`; Endnutzer-Pulls müssen
   nach öffentlicher Freigabe anonym funktionieren.
4. Installer und Runtime vertrauen ausschließlich auf vollständige
   `@sha256:`-Referenzen. Tags sind nicht vertrauensbegründend.
5. Image-Akquisition ist im interaktiven Installer ausdrücklich und
   standardmäßig ausgeschaltet. Silent-Modi erteilen keine Zustimmung.
6. Ablehnung, Offlinezustand oder Pullfehler lassen die PLwC-Kerninstallation
   im sichtbar dokumentierten Safe Mode zu.
7. Zustimmung verpflichtet zu Digestprüfung und echtem netzwerklosem Probe je
   Laufzeit; ein erfolgreicher Download allein genügt nicht.
8. Diagnoseberichte sind atomar zu schreiben und vollständig zu exportieren,
   auch bei unerwarteten Python-/Child-Prozessfehlern.
9. GHCR-Push, öffentliche Paketsichtbarkeit, endgültiger Produktionsbuild und
   Veröffentlichungen bleiben getrennte Product-Owner-Freigaben.

## Konfliktauflösung

SR-008 verbietet implizite Image-Pulls. UR-015 verletzt diese Grenze nicht,
weil der neue Pfad eine sichtbare, standardmäßig ausgeschaltete Zustimmung
verlangt. Die bisherige Safe-Mode-Fähigkeit bleibt erhalten; sie darf nur nicht
mehr als vollständige Document-/Sandbox-Bereitschaft bezeichnet werden.

Das bestehende direkte `python:3.12-slim` wird nicht still über GHCR gespiegelt.
Stattdessen erhält PLwC einen eigenen, nachvollziehbar aus einer
digest-gepinnten offiziellen Basis gebauten Python Runner.

## G0-Exitprüfung

- Anforderungen und Defaults reviewed: PASS
- Nicht-Ziele und Freigabegrenzen reviewed: PASS
- grundlegende offene Architekturentscheidung: keine
- jede neue UR/SR tracebar: PASS
- Security-/Privacy-Widerspruch: keiner
- Veröffentlichung oder Build ausgelöst: nein

G0 ist damit fachlich geschlossen. Die konkreten Digests, Größen und
Buildartefakte sind bestimmungsgemäß Ergebnisse von G1 bis G3 und keine offene
G0-Entscheidung.

