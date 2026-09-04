# PLwC 1.0 / Installer r26 – Phase 4 CLU-basierter PLwC-Doktor

Stand: 3. September 2026

## Eine sichtbare Diagnoseoberfläche

Die lokale Konfigurationsseite enthält genau einen Bereich `PLwC-Doktor` mit
den Aktionen Diagnose, Reparaturplan, bestätigte Reparatur und JSON-Export. Der
öffentliche MCP-Vertrag wurde nicht erweitert: `plwc_profile(operation="doctor")`
bleibt der CLU-Doctor-Zugang innerhalb der unveränderten Fassade aus exakt acht
Werkzeugen; ein separates öffentliches `plwc_doctor` existiert nicht.

## Read-only-Diagnose

Für die lokale Oberfläche gibt es einen internen CLU- und Runtime-Snapshotpfad,
der weder das öffentliche Auditverhalten verändert noch beim Laden fehlende
Verzeichnisse anlegt. Die Diagnose liest Komponenten-/Kompatibilitätsstatus,
Runtime- und Legacy-Pfade, erwartete Dateien und Hashes, Profile, Workspace,
Launcher-/Extension-Zustand sowie – auf Windows begrenzt und read-only –
Native-Messaging-Registrierungen, relevante Prozesse, Port 3007, geplante
PLwC-Aufgaben und Autostartlinks.

Jeder Check enthält Status, Beleg, Risiko, Empfehlung und gegebenenfalls eine
erlaubte Reparaturaktion. Unvollständige Profile bleiben ausdrücklich außerhalb
automatischer Reparatur; der Doctor erfindet oder überschreibt keine Profil-,
Persona-, Memory- oder Governance-Inhalte. Unbekannte oder fremde Prozesse und
Portinhaber werden nur inventarisiert.

Der Diagnose-Snapshot erhält eine SHA-256-basierte `snapshot_id`. Tests vergleichen
den vollständigen Datei- und Verzeichnisbaum vor und nach Diagnose bytegenau und
belegen keine Mutation. Der öffentliche CLU-Doctor wurde zusätzlich mit einem
reinen In-Memory-Metadatenaudit geprüft; auch dort blieb der Systembaum
unverändert.

## Deterministische Reparaturtransaktion

Die aktuelle Engine akzeptiert ausschließlich die Allowlist-Aktionen
`ensure_directory` und `restore_file_from_payload`. Die zweite Aktion verlangt
eine Quelle innerhalb eines festgelegten Payloadroots, einen exakten SHA-256-Wert
und ein Ziel innerhalb des PLwC-Approots. Weitere Installer-/Migrationsaktionen
werden in Phase 5 auf derselben Transaktionsgrenze ergänzt.

Ein Plan bindet:

- die unveränderliche Diagnose-`snapshot_id`,
- jede Aktion samt Erklärung, Risiko und Vorbedingung,
- eine kanonisch berechnete `plan_id`,
- die Pflicht zur Bestätigung genau dieser Plan-ID.

Vor Apply wird der Istzustand erneut diagnostiziert. Ein geänderter Snapshot,
eine manipulierte Planaktion, eine andere Plan-ID oder eine nicht allowlistete
Aktion wird abgelehnt. Beim Apply werden ersetzte Dateien vorab gesichert, jeder
Schritt als JSONL auditiert und ein vollständiger Postflight ausgeführt. Bei
Fehlern werden bereits ausgeführte reversible Schritte in umgekehrter Reihenfolge
zurückgerollt. Ein erfolgreicher zweiter Lauf erzeugt einen leeren Plan und
schreibt oder ändert nichts.

## Prüfnachweise

- Doctor-Transaktions- und Konfigurationsintegration: `22 passed`
- gezielte Phase-0-bis-4-Pythonregression: `39 passed`
- vollständige Python-Suite: `84 passed, 6 skipped`
- Extension-Typecheck: `PASS`
- vollständige Extension-Suite: `177 passed`
- Python- und JavaScript-Syntax: `PASS`
- Rollbacktest: erste reversible Aktion ausgeführt, Folgeaktion wegen fehlendem
  verifiziertem Payload abgelehnt, erster Schritt vollständig zurückgerollt
- Read-only-Test: Datei- und Verzeichnisbaum vor/nach Diagnose identisch
- Idempotenztest: zweiter Plan `no_changes=true`, zweites Apply
  `result=no_changes`, Baum unverändert

Die sechs übersprungenen Python-Tests sind vorhandene umgebungsabhängige
Docker-/Windows-Integrationen und keine Phase-4-Fehler. Reale Windows-11-
Installations- und Reparaturfälle bleiben Teil der verbindlichen Phase-8-Matrix.

## Phase-4-Gate

**PASS.** Diagnose verändert nichts; jede planbare Änderung wird erklärt und an
Snapshot plus Plan-ID gebunden; Apply akzeptiert nur denselben bestätigten Plan
und bekannte Aktionen; Backup, Audit, Rollback und Postflight sind getestet;
der zweite Lauf ist änderungsfrei. Die öffentliche CLU-Diagnose bleibt read-only
und die Acht-Werkzeug-Fassade unverändert.
