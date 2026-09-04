# PLwC 1.0 / Windows Installer r26 – Kandidatenabnahme

Stand: 2026-09-04

Status: **FINALER R26-RELEASEKANDIDAT PASS / PHASE 8 PASS / NICHT VERÖFFENTLICHT**

## Freigegebener r26-Releasekandidat

`PLwC-Setup-1.0.0-installer-r26.exe`

- Bytes: `5.494.996`
- SHA-256: `d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
- Authenticode: `NotSigned`
- Buildmodus: `explicit_unsigned`
- Build-ID:
  `plwc-windows-setup@1.0.0/installer-r26#sha256:d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`

Begleitartefakte:

| Datei | SHA-256 |
| --- | --- |
| Buildidentität | `5747fdb7733b8c25ef87b0c13bedf83a09bd8524241b50ef2c94ff60b7afd3cd` |
| Payload-Manifest | `571319b097172418cad69b89b30debd83ad70975c5095d89bef7fdd789bba76b` |
| `SHA256SUMS.txt` | `7ff4a0458775381878bf9e5fb5155f10fba3c2c494079a78ea3ad6101a5cf145` |

Der Product Owner gab diesen endgültigen r26-Build am 2026-09-04 ausdrücklich
frei. Mangels Authenticode-Zertifikat erfolgte der Build bewusst mit
`-Unsigned`; Windows darf deshalb `Unbekannter Herausgeber` anzeigen. Die vier
Artefakte liegen unveränderlich unter
`private_evidence/r26-final-candidate/sha256-d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65/`.

## Verwerfungen vor diesem Kandidaten

| Setup-SHA-256 | Ergebnis und Reaktion |
| --- | --- |
| `11dcf0eea098bf57880f46593d03082bfa41f8a6d5a2c8e78663ba7844be949d` | Postflight behandelte eine nativ erzeugte Manifestkonfiguration fälschlich als geschützte Mutation; Rollback traf zusätzlich auf einen Bridge-Lock. System aus Backup vollständig wiederhergestellt; Kandidat verworfen. |
| `999eeb5e60fc3f82cd4461f6a1750bb037ec4f7ac516340e86d081882a21a758` | Shortcut-Probe kombinierte Windows-Pfade durch PowerShell-Kommapräzedenz. Automatischer atomarer Rollback erfolgreich; zusätzlich falscher Setup-Erfolgscode entdeckt. Probe, Reportpersistenz und Custom-Exitcode korrigiert; Kandidat verworfen. |
| `33f7fef0b55a83823439b167d885179f44fd7ae94982ddc54ac13ca7ad6748da` | Reale Dirty-/r25-Migration und 12/12 Postflight bestanden, aber der installierte Doctor prüfte den falschen Bridge-Einstiegspfad. Pfad und Regressionstests korrigiert; Kandidat verworfen. |
| `55e10b6193ddf0bb88efc2e02e5ad5d587f3c54b48b48b2f58795e4a6b6feab6` | Sauberer VM-Lauf installierte Python, Module, Node, Docker, Gateway und Bridge. Ein kalter Python-Import überschritt die 30-Sekunden-Grenze; anschließend verlor der gemeinsame 8-Sekunden-Windows-Probe die Detailfelder gültiger Verknüpfungen. Postflight meldete korrekt keinen Erfolg und der Rollback war vollständig. Timeout und unabhängige Windows-Probes korrigiert; Kandidat verworfen. |

Alle vier Bytefolgen bleiben nur als private, schreibgeschützte Fehler- und
Regressionsevidenz erhalten. Keine davon ist der auszuliefernde Kandidat.

## Testnachweise des aktuellen Quellstands

- Python: `112 passed, 6 skipped` in 44,28 s;
- Extension: `190/190 passed`, Typecheck und Build PASS;
- Store-Paket-Reproduzierbarkeit, Inventar, Identität und Secret-Scan: PASS;
- Installer-Pester: `72 passed, 0 failed, 0 skipped` in 620,12 s;
- Pester-NUnit SHA-256:
  `22bc69dc445050eb627e34915b30f57365fde363f84044d33f323fbef35d8068`.

## Isolierter VM-Vorlauf

Vor der endgültigen Buildfreigabe wurde derselbe Implementierungsstand als
ausdrücklich unsignierter, isolierter VM-Testbuild erzeugt. Seine saubere
Windows-11-Installation und der anschließende vollständige Chrome-Neustart
bestanden. Dieses Artefakt bleibt Testevidenz und ist nicht der
Releasekandidat.

| Datei | Bytes | SHA-256 |
| --- | ---: | --- |
| `PLwC-Setup-1.0.0-installer-r26-VMTEST-f30a2795.exe` | 5.495.024 | `f30a2795e6144882e824bb8ca69ebf5466e831d9415cc9ae597d58250519dfa8` |
| Buildidentität | 1.329 | `6e6fb369556ab7de0a36409579d0acc3db50c36ab4c6e22c44f033bcc76d5b78` |
| Payload-Manifest | 718.106 | `8d6346a11d9efcaf593d817e7fb0fb736fd47fdc9ff5ee2ce8e182181e1748ac` |
| `SHA256SUMS.txt` | 311 | `1edb171f1403ec488e645e342adfea49ecdf39df6167778d8e2822c7b23f61bd` |

Quell- und Stagingversion der korrigierten Windows-Diagnosemodule sind
bytegleich. Der lokale Windows-Probe lieferte für Verknüpfungen, Prozesse,
Port 3007 und geplante Aufgaben jeweils einen erfolgreichen Einzelstatus und
vollständige Shortcut-Ziele und -Argumente.

Der reale VM-Nachtest schloss Setup ohne Postflight-Fehler ab. Danach waren
Gateway `1.0.0`, der vollständige Arbeitsbereich und 8/8 öffentliche Tools
verfügbar. Nach vollständigem Chrome-Neustart blieb PLwC installiert; das Panel
meldete Extension `1.0.1`, die stabile Entwicklungs-ID
`nlogfcafjdfdoknpkbehjgihpafpipdb`, passenden Build und erneut 8/8.

## Direkte r25→r26-Abnahme auf Windows 11

Auf Windows 11 Pro 64 Bit, Build 22631, wurde zuerst der unveränderte
r25-Kandidat `e0fdcc54…1fa7c` mit Gateway, Codex und Chat Bridge installiert.
Die danach gesicherte Auswahl bindet `installer-r25`, den vollständigen
r25-Setuphash und Browser-Extension `1.0.0`. Unmittelbar anschließend bestand
der exakte r26-Kandidat `d604e771…97dc65` die direkte Aktualisierung:

- beide Setups Exitcode 0 und regulär geschlossene Inno-Logs;
- Transaktion und gemeinsamer Postflight: PASS, 12/12 Checks;
- Gateway und Bridge unter versionlosen Pfaden aktiv;
- Native Messaging für Chrome, Edge und Brave registriert;
- drei fest erlaubte Origins, kein Wildcard-Origin;
- Live-Health für Development-, Chrome- und Edge-Origin: 8/8;
- installierter Doctor: 7 PASS, 1 Hinweis, 0 Fehler, Runtime-Dateien
  vollständig, Kompatibilität `blocking=none`/`unknown=none`, leerer Plan;
- Docker `29.3.1`, Qdrant `1.18.0`, Document Worker `0.1.0` und Extension
  `1.0.1` tatsächlich erkannt;
- Profile, aktives Profil und Arbeitsbereich bytegleich erhalten; in
  `gateway-settings.json` änderte sich ausschließlich `updated_at`.

Referenzhashes der lokalen Systemnachweise:

| Nachweis | SHA-256 |
| --- | --- |
| r25-Setup-Log | `7d3f56afbb1af228dafd3590fc0f05dcf12069c91f42486630334660ad088cd9` |
| gesicherte r25-`selection.ini` | `9919ad4897468f3bf5be22236199aa04017882b0fbc7d6f488dd8d7875906934` |
| r26-Setup-Log | `a89a6eb053740c6b7f74e5527bec11d474d4c0c8287d14d6a873545ad16686fc` |
| r26-Transaktion | `97a5ce5bced6d84be67f7719d719df90e206ebdbe210f956c199bbd6529878bf` |
| Postflight-Report | `56569ea9f524d6f83c34fc8701c6c7c459aa9cac50aa3211f5a35c1eda77cd5e` |
| finale `selection.ini` | `37bf330dd37b4440827ee231ff14873db0a052fca725dd9b4dbd5034ebd69788` |
| Profilbaum vor/nachher | `8d57e1f4af69e8d2cdd21314786279ae7d9b7f75ebd5c564c339d5c6f7cd7544` |
| Workspacebaum vor/nachher | `b4280ed5437576620030525714a0a8ec89905615059adb7da01e64e235ef2736` |

## Gate-Entscheidung

Der endgültige r26-Kandidat bindet den korrigierten Quellstand, bestand die
vollständigen automatisierten Gates und die direkte r25→r26-Aktualisierung.
Die zuvor offenen Browser-Lifecycle- und Komponenten-Inventarpunkte sind im
installierten Ergebnis geschlossen. Der Product Owner hat den ausdrücklich
unsignierten Build freigegeben. **Phase 8 ist PASS.**

Diese Freigabe veröffentlicht nichts. Insbesondere wurden weder ein
GitHub-Release noch eine Store-Veröffentlichung ausgeführt. Solche Schritte
bleiben eigenständige, ausdrücklich zu bestätigende Gates.

Der aktuelle Store-Zustand wurde live gelesen. Chrome `1.0.0` war akzeptiert,
aber privat ohne Trusted-Tester-Gruppe und keine Linkveröffentlichung.
Der Product Owner brach die wartende Veröffentlichung ab; `1.0.0` wurde nicht
veröffentlicht. Das geprüfte Chrome-Paket `1.0.1` wurde in derselben ID
gespeichert und am 2026-09-04 zunächst privat zur Prüfung eingereicht. Diese
Prüfung wurde danach kontrolliert abgebrochen, die Sichtbarkeit auf **Nicht
gelistet** geändert und gespeichert und Version `1.0.1` erneut zur Prüfung
eingereicht. Die automatische Veröffentlichung nach bestandener Prüfung blieb
deaktiviert. Der abschließend live gelesene Status ist **Überprüfung
ausstehend**, Sichtbarkeit **Nicht gelistet** und keine veröffentlichte Version.
Edge `1.0.0` ist bereits live und hidden. Das
geprüfte `1.0.1`-Paket wurde dort in derselben CRX-Identität als
Hidden-Aktualisierung gespeichert und steht **In draft**; die bestehende
`1.0.0` bleibt live. Edge `1.0.1` wurde nicht zur Prüfung eingereicht. Keine
neue Veröffentlichung und kein Sichtbarkeitswechsel wurden ausgeführt.
