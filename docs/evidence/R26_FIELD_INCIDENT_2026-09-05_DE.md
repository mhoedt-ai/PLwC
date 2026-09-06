# PLwC 1.0 / Installer r26 – redigierter Feldbefund vom 2026-09-05

Status: **BESTÄTIGTER RELEASEBLOCKER / R26 NO-GO**

## Betroffener Kandidat

- Datei: `PLwC-Setup-1.0.0-installer-r26.exe`
- SHA-256:
  `d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
- Build-ID:
  `plwc-windows-setup@1.0.0/installer-r26#sha256:d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
- Installationsmodus: `custom`
- ausgewählte Komponenten: Gateway, Claude, Chat Bridge

## Beobachtung A – Document Worker nicht nutzbar

Der vorhandene PLwC-Gateway- und Bridge-Pfad arbeitete; der Launcher meldete
wiederholt 8/8 Tools. Ein realer Aufruf von `plwc_document_operation` endete
jedoch mit:

```text
result_status=failure
error_category=UNAVAILABLE
error_detail_category=worker_missing
```

Der Installer enthält keine Image-Akquisition. Seine Docker-Prüfung fordert
lokal `python:3.12-slim`, `plwc-node-runner:0.1.0` und
`plwc-document-worker:0.1.0`, führt aber nur `docker image inspect` aus. Der
Document Worker war deshalb auf diesem System nicht vorhanden.

## Beobachtung B – separater Preflight-Abbruch

Ein erneuter Lauf desselben r26-Kandidaten brach während
„Vorhandene PLwC-Laufzeit wird gesichert und der Migrationsplan geprüft“ ab.
Die redigierte Diagnose enthält:

```text
event=installer_preflight
status=failure
exit_code=1
report=%APPDATA%\PLwC\logs\setup\r26-installer-preflight.json
```

Der genannte JSON-Bericht ist im bereitgestellten Diagnoseexport nicht
enthalten. Der genaue Python-Exceptiontext ist deshalb mit den vorhandenen
Belegen nicht rekonstruierbar. Exitcode 1 entspricht weder dem vorgesehenen
Portblocker-Code 20 noch dem behandelten Maintenance-Fehlercode 40. Damit ist
zusätzlich ein nicht vollständig erfasster Ausnahme-/Diagnosepfad belegt.

Die beiden Beobachtungen werden nicht kausal gleichgesetzt: Das fehlende
Worker-Image erklärt `worker_missing`, aber nicht ohne weitere Evidenz den
separaten Preflight-Exitcode 1.

## Auswirkung auf die bisherige r26-Abnahme

Der frühere positive Systemnachweis für Docker/Document Worker wurde auf einem
Abnahmehost mit bereits vorhandenem lokalem Image erbracht. Die saubere VM
belegte Gateway, Bridge, Extension und 8/8 Toolregistrierung, aber keinen echten
Document-Worker-Aufruf nach einer Installation ohne vorinstallierte
PLwC-Images. Der daraus abgeleitete Gesamtclaim war daher zu weit.

r26 bleibt unverändert als historische Evidenz erhalten, ist aber kein
auszuliefernder Kandidat mehr. Die Korrektur erhält die neue Revision r27.

