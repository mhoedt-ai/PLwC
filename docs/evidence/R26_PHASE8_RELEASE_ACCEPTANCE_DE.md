# PLwC 1.0 / Windows Installer r26 – Kandidatenabnahme

Stand: 2026-09-04

Status: **VORGÄNGERKANDIDAT VERWORFEN / VM-TESTKANDIDAT SYSTEM PASS / PHASE 8 HOLD**

## Nicht mehr freigabefähiger Vorgängerkandidat

`PLwC-Setup-1.0.0-installer-r26.exe`

- Bytes: `5.493.306`
- SHA-256: `55e10b6193ddf0bb88efc2e02e5ad5d587f3c54b48b48b2f58795e4a6b6feab6`
- Authenticode: `NotSigned`
- Buildmodus: `explicit_unsigned`
- Build-ID:
  `plwc-windows-setup@1.0.0/installer-r26#sha256:55e10b6193ddf0bb88efc2e02e5ad5d587f3c54b48b48b2f58795e4a6b6feab6`

Begleitartefakte:

| Datei | SHA-256 |
| --- | --- |
| Buildidentität | `b6f7f3f37e7605ce254b208792c4d23cba57ca0bdaf87232d0a518ed6738adf5` |
| Payload-Manifest | `e2fbb20578422b989607f8bbe7a8ac5aaee8ba0e5e15f6d40e79dd6870cd0827` |
| `SHA256SUMS.txt` | `b0e51d0ead7aafaf3251ada4d9a88d14f6bc524cd4136c12f0c659eabcc74cd4` |

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

- Python: `112 passed, 6 skipped`;
- Extension: `190/190 passed`, Typecheck und Build PASS;
- Installer-Pester: `72 passed, 0 failed, 0 skipped`;
- Pester-NUnit SHA-256:
  `22bc69dc445050eb627e34915b30f57365fde363f84044d33f323fbef35d8068`.

## Isolierter VM-Testkandidat

Der aktuelle Quellstand wurde ausschließlich als ausdrücklich unsignierter,
isolierter VM-Testbuild erzeugt. Er ist kein endgültiger Produktionsbuild und
noch nicht als Releasekandidat gebunden. Seine saubere Windows-11-Installation
und der anschließende vollständige Chrome-Neustart sind inzwischen bestanden.

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

## Reale Windows-11-Abnahme

Auf Windows 11 Pro 64 Bit, Build 22631, bestand der exakte Kandidat eine
r26→r26-Aktualisierung:

- Transaktion und gemeinsamer Postflight: PASS, 12/12 Checks;
- Gateway und Bridge unter versionlosen Pfaden aktiv;
- Native Messaging für Chrome, Edge und Brave registriert;
- drei fest erlaubte Origins, kein Wildcard-Origin;
- Live-Health für Development-, Chrome- und Edge-Origin: 8/8;
- installierter Doctor: 0 Fehler, Runtime-Dateien vollständig, leerer Plan;
- Profile, aktives Profil und Arbeitsbereich bytegleich erhalten.

Referenzhashes der lokalen Systemnachweise:

| Nachweis | SHA-256 |
| --- | --- |
| Setup-Log | `a505f9a9ab27edd4959e8bac4ef15f3bc50523e0a10253131a0a943feb14c3b7` |
| r26-Transaktion | `f82ff1d6c6361ccc6895fa00f463699afa42fe69bc0dd688e47b8d536c8afa50` |
| Postflight-Report | `974175dde40c37399eaea7b16e40e33b3eb72109e06de224d5ff2da67a3d8c18` |
| `selection.ini` | `34ceb4f6a7262947f03966f679fbc71f1c59f14bd282af6de7337bf9b8df7898` |
| Vorher-Benutzerdatensnapshot | `0f1baa35bcf09b244b63ba169de0c38f043dfd4fe9e317740d103f31268115d7` |

## Gate-Entscheidung

Der Kandidat hat den vorhandenen Windows-Hostlauf bestanden. Nach diesem Lauf
wurden jedoch ein reales Brave-Neustartproblem mit `Bereit 8/8` bei gleichzeitig
verriegeltem Toolvertrag sowie eine fest eingetragene `unknown`-Beobachtung für
den lokal vorhandenen Document Worker nachgewiesen und im Quellstand korrigiert.
Damit ist die hier gebundene EXE nicht mehr der freigabefähige Quellstand. Der
vollständige Brave-Neustart bestand nach dem einmaligen Wechsel der entpackten
Entwicklungsinstanz vom Repository-Netzpfad auf
`%APPDATA%\PLwC\app\bridge\extension`. Die direkte r25→r26-/Dirty-Migration ist
funktional bereits einschließlich 12/12 Postflight bestanden. Zum
Releaseabschluss fehlen nur ihre einmalige Hash-Bindung an den späteren
Produktionskandidaten und die ausdrückliche Freigabe für diesen endgültigen
Build. Die Einzelheiten stehen in
`docs/R26_WINDOWS_TEST_MATRIX.md`.

Der aktuelle Store-Zustand wurde live gelesen. Chrome `1.0.0` war akzeptiert,
aber privat ohne Trusted-Tester-Gruppe und keine Linkveröffentlichung.
Der Product Owner brach die wartende Veröffentlichung ab; `1.0.0` wurde nicht
veröffentlicht. Das geprüfte Chrome-Paket `1.0.1` ist nun in derselben ID
gespeichert und steht **Entwurf**, weiterhin **Privat**, ohne Testergruppe und
ohne veröffentlichte Version. Edge `1.0.0` ist bereits live und hidden. Das
geprüfte `1.0.1`-Paket wurde dort in derselben CRX-Identität als
Hidden-Aktualisierung gespeichert und steht **In draft**; die bestehende
`1.0.0` bleibt live. Keine neue Veröffentlichung, kein Sichtbarkeitswechsel und
keine Review-Einreichung wurden ausgeführt.
