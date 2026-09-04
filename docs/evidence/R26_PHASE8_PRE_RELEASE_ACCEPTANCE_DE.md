# PLwC 1.0 / Windows Installer r26 – Phase 8 Zwischenabnahme

Stand: 2026-09-04

Status: **HOLD – vorhandener Kandidat durch nachträgliche Quellfixes überholt;
saubere Windows-Systemmatrix noch unvollständig**

## Freigabegrenzen

Der Benutzer hat mit `los` den endgültigen r26-Build freigegeben. Diese
Freigabe umfasste keine Browser-Store-Einreichung oder -Veröffentlichung. Der
Build wurde mangels Authenticode-Zertifikat ausschließlich über den
ausdrücklichen Schalter `-Unsigned` erzeugt. Windows darf deshalb
`Unbekannter Herausgeber` anzeigen.

Keine Store-Datei wurde hochgeladen, kein Entwurf verändert, keine Prüfung
ausgelöst und keine Veröffentlichung vorgenommen.

## Repository- und Releaseidentität

| Feld | Wert |
| --- | --- |
| Branch | `codex/plwc-chat-bridge-rc19` |
| Ausgangs-HEAD | `3f02b54e648486ce3a5a4c071080ae10440f1716` |
| Produkt / Revision | `1.0.0` / `installer-r26` |
| Gateway / Node Bridge / Launcher | `1.0.0` / `1.0.0` / `1.0.0` |
| Extension-Quellpaket | `1.0.1` |
| Abnahmehost | Windows 11 Pro 64 Bit, Build 22631 |

Der Arbeitsbaum enthält die zusammengehörigen, noch nicht als Releaseabschluss
committeten r26-Änderungen sowie das vom Benutzer bereitgestellte Briefing.
Historische Dateien und fremde Änderungen wurden nicht entfernt.

## Aktueller Kandidat

| Artefakt | Bytes | SHA-256 |
| --- | ---: | --- |
| `PLwC-Setup-1.0.0-installer-r26.exe` | 5.493.306 | `55e10b6193ddf0bb88efc2e02e5ad5d587f3c54b48b48b2f58795e4a6b6feab6` |
| `PLwC-1.0.0-installer-r26-build-identity.json` | 1.329 | `b6f7f3f37e7605ce254b208792c4d23cba57ca0bdaf87232d0a518ed6738adf5` |
| `PLwC-1.0.0-payload-manifest.json` | 718.106 | `e2fbb20578422b989607f8bbe7a8ac5aaee8ba0e5e15f6d40e79dd6870cd0827` |
| `SHA256SUMS.txt` | 311 | `b0e51d0ead7aafaf3251ada4d9a88d14f6bc524cd4136c12f0c659eabcc74cd4` |

Authenticode-Status von Setup und nativem Launcher: `NotSigned`. Die externe
Buildidentität bindet Dateiname, Setup-Hash, Payload-Hash, Revision,
Komponentenversionen und diesen Abnahmenachweis.

Die vier Dateien liegen zusätzlich schreibgeschützt unter
`private_evidence/r26-final-candidate/sha256-55e10b6193ddf0bb88efc2e02e5ad5d587f3c54b48b48b2f58795e4a6b6feab6/`.

## Vertrauenskette

Der öffentliche RSA-4096-Verifikationsschlüssel ist in
`config/release-trust.json` gepinnt:

- Key-ID: `plwc-release-r1-6bc3b440c598c407`
- Public-Key-Fingerprint:
  `6bc3b440c598c407f1b685b136ad89cccb344f25c6b02d5d10fe72c3bfa8dcda`

Der private PKCS#8-Schlüssel liegt nicht im Repository und ist für den aktuellen
Windows-Benutzer per DPAPI geschützt. Paarung, Fingerprint und Manifestprüfung
bestanden.

## Automatisierte Gates

| Prüfung | Ergebnis |
| --- | --- |
| Vollständige Python-Suite | **112 passed, 6 skipped** in 64,77 s |
| Extension `npm run check` | **190/190 passed**, TypeScript PASS, Build PASS |
| Installer-Pester | **72/72 passed**, 0 failed, 0 skipped |
| Pester-NUnit SHA-256 | `22bc69dc445050eb627e34915b30f57365fde363f84044d33f323fbef35d8068` |
| `git diff --check` | vor Dokumentationsabschluss PASS; nur CRLF-Hinweise |

Die sechs Python-Skips sind optionale Docker-/Symlink-Capability-Gates.

## Realer Lauf des exakten Kandidaten

Der Kandidat wurde als r26→r26-Aktualisierung mit den Komponenten Gateway und
Chat Bridge auf dem Abnahmehost ausgeführt. Ergebnis:

- Installertransaktion: `postflight_succeeded`;
- sechs installerverwaltete Konfigurationsdateien vor Austausch gesichert;
- alle 12 harten Postflight-Checks bestanden;
- Postflight-Report-ID:
  `9701e7e16db0b6c5b5e2b619b57f06d35344526e512c5f638424417ded88205c`;
- Setup-Log regulär geschlossen;
- `selection.ini` bindet Revision und Setup-SHA des aktuellen Kandidaten;
- genau ein Port-3007-Besitzer unter dem versionlosen Pfad
  `%APPDATA%\PLwC\app\bridge\bridge\dist\src\index.js`;
- Live-Health für Development-, Chrome- und Edge-Store-Origin jeweils PASS,
  Build `plwc-chat-bridge@1.0.0`, exakt 8 Werkzeuge.

Der äußere PowerShell-Testwrapper wurde nach dem regulären Setup-Ende beendet,
weil `Start-Process -Wait` auch auf den absichtlich weiterlaufenden
Bridge-Kindprozess wartete. Setup, Postflight und Bridge wurden dabei nicht
abgebrochen; der Listener blieb anschließend aktiv.

## Schutz der Benutzerdaten

Der vollständige Vorher/Nachher-Hashvergleich ergab:

- Profile: 83 Dateien / 22 Verzeichnisse, keine Abweichung;
- Arbeitsbereich: 953 Dateien / 196 Verzeichnisse, keine Abweichung;
- aktive Profildatei unverändert, SHA-256
  `24ee97780a92a4e67eefa9bd2982e89dc3b832c9f79d8998d39df61b036c39ec`;
- fachliche Einstellungen erhalten: `Sororitas`, Arbeitsbereich auf F:,
  Schwellen 2/3/2, Qdrant an, Persona-Layer an.

## Installierter Doctor

Die erste Diagnose des zuvor gebauten Kandidaten `33f7…` deckte einen falschen
Inventurpfad auf: geprüft wurde `bridge\dist\index.js`, gebaut wird verbindlich
`bridge\dist\src\index.js`. Dieser Kandidat wurde verworfen. Nach Korrektur,
Regressionstest, Vollgates, Neubau und Aktualisierung meldet der installierte
Doctor:

- `installation.runtime_files`: PASS, `missing=none`;
- harter Postflight: PASS;
- Zusammenfassung: 6 PASS, 2 Hinweise, 0 Fehler;
- Reparaturplan: 0 Änderungen, `no_changes=true`;
- Windows-Snapshot: ein Port-3007-Besitzer, keine Probe-Fehler.

Der damals installierte Doctor meldete `browser_extension` und
`document_worker` als nicht erkannt. Für den Browser war das vor dem ersten
Handshake zulässig; für den lokal vorhandenen Document Worker war es ein
übersehener Implementierungs- und Abnahmefehler. Das zugehörige Phase-2-Gate
wurde wieder geöffnet. Der korrigierte Quellstand erkennt auf demselben Host
Docker `29.3.1`, Qdrant-Client `1.18.0` und Document Worker `0.1.0` mit lokaler
Image-ID; neue Regressionen und die wiederholten Python-/Installer-Gates sind
grün. Der installierte alte Kandidat enthält diese Korrektur noch nicht.

## Chrome- und Edge-Storestatus

Der Chrome-Entwurf wurde in diesem Arbeitsablauf tatsächlich gelesen:

- ID `feceodobnhefdbfgmbinkndhogpfkicb`, Version `1.0.0`;
- akzeptiert und `Bereit zur Veröffentlichung`;
- angezeigter spätester Termin 2026-10-01;
- aktive Sichtbarkeit **Privat**;
- keine Trusted-Tester-Gruppe ausgewählt.

Der Entwurf ist deshalb keine nutzbare Linkveröffentlichung. Das vorgesehene
Modell ist **Nicht gelistet / Unlisted**. Ein erneuter Leseversuch am 2026-09-04
endete zunächst an Googles Passwort-Reauth. Nach der später erfolgreichen
Anmeldung wurde derselbe Zustand live bestätigt. Der Paketbereich sperrt einen
neuen Upload, solange der akzeptierte Entwurf auf die Veröffentlichung wartet;
das Menü bietet nur den Abbruch dieser Veröffentlichung. Dieser potenziell
review-verwerfende Schritt wurde anschließend durch den Product Owner
ausgeführt; `1.0.0` wurde dabei nicht veröffentlicht. Das reproduzierbar
geprüfte Paket `PLwC-Chat-Bridge-1.0.1-chrome-brave-store.zip` wurde danach in
dieselbe Artikel-ID geladen und gespeichert. Chrome zeigt Version `1.0.1`,
Status **Entwurf**, weiterhin **Privat**, keine Trusted-Tester-Gruppe und keine
veröffentlichte Version. `Prüfen lassen` wurde nicht betätigt.

Edge wurde am 2026-09-04 ebenfalls live verifiziert: Version `1.0.0` war
**Live**, Sichtbarkeit **Hidden**, CRX-ID
`nncomjknhhlgcmkmlaljhkiojcnpmflb`, und der offizielle Direktlink war
vorhanden. Anschließend wurde das reproduzierbar geprüfte Paket
`PLwC-Chat-Bridge-1.0.1-edge-store.zip` in dieselbe Identität geladen. Partner
Center verifizierte Version `1.0.1`; sie steht nun **In draft** und weiterhin
**Hidden**, während `1.0.0` live bleibt. `Publish` wurde nicht verwendet.

## Phasenergebnis und offene Bedingungen

Phasen 0 bis 7: **PASS**. Phase 8 bleibt **HOLD**. Die zuletzt installierte EXE
hat den vorhandenen Hostlauf technisch bestanden, ist aber durch danach
implementierte Browser-Lifecycle- und Komponenten-Inventar-Fixes nicht mehr der
freigabefähige Quellstand.
Der isolierte Unsigned-VM-Testkandidat `f30a2795…9dfa8` hat inzwischen die
saubere Windows-11-Installation sowie den vollständigen Chrome-Neustart mit
Extension `1.0.1`, passender Buildidentität und 8/8 bestanden. Noch offen sind:

1. abschließende Hash-Bindung der bereits funktional bestandenen direkten
   r25→r26-/Dirty-Migration an den später freigegebenen Produktionskandidaten;
2. die übrigen isolierten Negativ- und Browser-Lifecycle-Fälle; der zuvor
   offene vollständige Brave-Neustart ist nach dem Wechsel der entpackten
   Erweiterung vom Repository-Netzpfad auf
   `%APPDATA%\PLwC\app\bridge\extension` bestanden (`1.0.1`, passender Build,
   `8/8`, erfolgreicher `plwc_status`);
3. Aktualisierung dieses Nachweises auf vollständiges PASS;
4. ausdrückliche Entscheidung über Chrome-Sichtbarkeit und die getrennte
   Einreichung des gespeicherten `1.0.1`-Entwurfs zur Prüfung;
5. ausdrückliche Freigabe eines endgültigen Produktionsbuilds.

Auf dem Abnahmehost sind Windows Sandbox, VirtualBox, VMware und QEMU nicht
verfügbar; Docker läuft im Linux-Modus. Das Aktivieren einer Windows-Funktion
mit möglichem Neustart wurde nicht ohne ausdrückliche Zustimmung vorgenommen.

**Kein Store-Gate ist freigegeben.**
