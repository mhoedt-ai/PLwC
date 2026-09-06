# PLwC 1.0 / Installer r26 – Phase 5 Installer-Migration und harter Postflight

Stand: 3. September 2026

## Preflight und Updateerkennung

Der r26-Installer erfasst vor der ersten Payloadänderung einen read-only
Preflight-Snapshot. Er enthält die gespeicherten und tatsächlich vorhandenen
App-, Gateway-, Bridge- und Datenpfade, Buildidentitäten, Profile und
Konfigurationshashes sowie Windows-Fakten zu Prozessen, Port 3007,
Native Messaging, Autostartlinks und geplanten Aufgaben. Prozessbelege werden
ausdrücklich als `proven`, `suspected` oder `unknown` klassifiziert.

Ein vollständiger vorhandener Zustand verwendet weiterhin den Update-Seitensprung
ohne erneute Abfrage der Datenverzeichnisse. Der aktive Bridgepfad ist in r26
jedoch immer der versionslose Pfad `app\bridge`; ein gespeicherter
`app\chat-bridge`- oder Versionspfad wird nur als Legacyquelle inventarisiert und
nicht still als neues Ziel übernommen. Unsichere überlappende Runtime- oder
Datenpfade werden abgelehnt.

## Migrations- und Rollbacktransaktion

Der Preflight erzeugt eine kanonisch gehashte Snapshot-ID und daraus einen
maschinenlesbaren Plan mit Plan-ID. Ausgeführt wird ausschließlich genau der vom
laufenden Windows-Setup bestätigte Plan. Vor Überschreiben wird der vollständige
vorhandene Appbaum unter `profile_backups\installer-r26\<snapshot>` gesichert.
Bekannte PLwC-Shortcuts und eindeutig benannte alte PLwC-Aufgaben werden für ein
mögliches Rollback ebenfalls gesichert.

Ein Prozess wird nur beendet, wenn Pfad oder Bridge-Kommandozeile ihn einem
inventarisierten PLwC-Runtimepfad eindeutig zuordnet. Ein fremder oder unbekannter
Inhaber von Port 3007 blockiert Setup mit Diagnose; er wird nicht beendet. Der
alte `app\chat-bridge`-Pfad bleibt bis zum erfolgreichen Postflight unverändert.
Erst danach wird er als Recoverybestand verschoben. Bei Fehler, Abbruch oder
fehlendem Erfolgssignal stellt Setup soweit möglich Appbaum, Native-Messaging-
Registrierung, bekannte Links und gesicherte Legacy-Aufgaben wieder her.

Die Installer-Hilfslogik verwendet dieselbe
`plwc_gateway.installation.installer_state`-Engine wie der lokale PLwC-Doktor.
Der native Launcher liest benutzerdefinierte Config-, State- und Logpfade aus dem
gespeicherten Installerzustand und fällt nur bei nicht verfügbarem Zustand auf
die stabilen `%APPDATA%\PLwC`-Pfade zurück.

## Verbindlicher gemeinsamer Postflight

Vor `installation_completed/status=success` müssen alle Checks desselben
Installer-/Doktor-Reports bestehen:

- SHA-256 jedes ausgewählten unveränderlichen Payloadelements,
- Installerrevision `installer-r26` und gemeinsame Bridge-Buildidentität,
- installierte Gateway-, Bridge-, Launcher-, Konfigurations- und Icondateien,
- erfolgreicher Launcherzustand mit antwortendem Gateway und exakt 8/8
  kanonischen Werkzeugen,
- korrekte Native-Messaging-Manifeste für Chrome, Edge und Brave mit dem
  aktuellen Launcherziel und erlaubter Extension-Origin,
- genau ein korrekter Benutzer-Autostartlink,
- eine funktional adressierte PLwC-Konfigurationsverknüpfung,
- keine alte PLwC-Aufgabe und kein eindeutig alter PLwC-Prozess,
- unveränderte vorhandene Profil- und geschützte Konfigurationsinhalte,
- atomar geschriebener Diagnosebericht und r26-Installationsidentität.

Die vom Installer erwartungsgemäß erzeugte Bridge-Konfiguration sowie
installerverwaltete Auswahl-/Clientdateien werden getrennt von geschützten
Benutzerdaten behandelt. Ein fehlerhafter Hash, eine Profiländerung, ein falsches
Shortcutziel oder eine falsche Registrierung führt zu `ok=false`; Legacybestände
dürfen dann nicht archiviert und ein Installationserfolg nicht geschrieben
werden.

## Automatisierte Abnahme

- Clean-Install, r25-Update und Dirty-Migration durchlaufen in den
  Dateisystemfixtures dieselbe Postflight-Funktion: `PASS`.
- Fremder Port-3007-Inhaber: blockiert, kein Stop-Aufruf: `PASS`.
- Eindeutig belegter Legacy-Prozess: nur dieser PID wird in der Testtransaktion
  gestoppt: `PASS`.
- Manipulierter Gatewayhash plus veränderte Profildatei: Postflight scheitert,
  keine Legacyarchivierung: `PASS`.
- Fehlgeschlagenes Update: vollständiger alter Appbaum wiederhergestellt:
  `PASS`.
- Manipulierter Plan, geänderter Snapshot und überlappende Datenpfade: abgelehnt:
  `PASS`.
- Vollständige Python-Suite: `93 passed, 6 skipped`.
- Browser-Extension Typecheck, Tests und Build: `PASS`, `177 passed`.
- Native Launcher: mit .NET-C#-Compiler gebaut; Build-ID
  `plwc-chat-bridge@1.0.0`: `PASS`.
- Windows-/Pester-Verträge einschließlich isoliertem Payloadbuild: `72/72 PASS`.
- `ValidateOnly`: erfolgreich; ISCC nicht aufgerufen; kanonische `stage`-/`dist`-
  Bäume laut Byte-Snapshot unverändert.

Die sechs übersprungenen Python-Tests sind vorhandene umgebungsabhängige
Docker-/Windows-Integrationen. Reale Windows-11-Clean-, Update- und Dirty-
Installationen bleiben Bestandteil der Phase-8-Systemtestmatrix; dafür wurde in
Phase 5 bewusst noch kein r26-Setup-EXE erzeugt.

## Isolierte Artefaktnachweise

- isoliertes Payloadmanifest SHA-256:
  `8a47e9372e7edaf6d6877209c14220a0f9ddfe27b4aeea3eee5f663d2263c034`
- Manifestrevision: `installer-r26`
- Browser-Extension-Komponente: `1.0.1`
- Payloaddateien: `3521`
- Payloadgröße: `18023621` Byte
- isolierter nativer Launcher SHA-256:
  `5326221eef86bc5c36a059cf1e7d8331086ec66c6bdf967025a09aed929e4251`
- in `.validate-build` erzeugte Setup-EXE-Dateien: `0`
- gesicherter r25-Kandidat weiterhin vorhanden und bytegleich, SHA-256:
  `e0fdcc548769588ccf23bd7de9e05ce32b3f220be047c63b0ebc46ff5071fa7c`

Diese Hashes bezeichnen nur den isolierten Validierungsstand, keinen freigegebenen
oder veröffentlichungsfähigen Produktionskandidaten.

## Chrome-Web-Store-Grenze

Der im neuen Chat tatsächlich geprüfte Chrome-Artikel
`feceodobnhefdbfgmbinkndhogpfkicb` blieb Version `1.0.0`,
`Bereit zur Veröffentlichung`, Frist vor dem 1. Oktober 2026, aber mit aktiver
Sichtbarkeit `Privat` und ohne Trusted-Tester-Gruppe. Er ist daher keine nutzbare
Linkveröffentlichung. Das Zielmodell `Nicht gelistet` wurde nicht gespeichert
oder veröffentlicht; es erfolgte keine Store-Aktion.

## Phase-5-Gate

**PASS.** Clean-, r25-Update- und Dirty-Fixtures bestehen denselben harten
Postflight. Fremde Portinhaber bleiben unangetastet, Legacy wird erst nach Erfolg
archiviert, Fehler und Abbrüche erzeugen kein falsches Erfolgssignal und lösen
Rollback aus. Weder ein Store-Upload noch ein endgültiger r26-Produktionsbuild
wurde ausgeführt.
