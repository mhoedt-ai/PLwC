# PLwC 1.0 / Windows Installer r27 – GHCR-Imagebereitstellung und Gates

Stand: 2026-09-12

Status: **G0–G4 PASS / G5 TEILWEISE PASS, SYSTEMMATRIX OFFEN / G6 NO-GO**

Dieser Plan korrigiert den auf einem realen Windows-11-System beobachteten
r26-Vertriebsfehler: Docker Desktop war vorhanden, das für
`plwc_document_operation` erforderliche Image jedoch nicht. Der Installer r26
prüft lokale Images nur mit `docker image inspect`; er lädt oder importiert sie
nicht. Der unveränderliche r26-Kandidat mit SHA-256
`d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
wird nicht überschrieben. Jede Korrektur trägt die Revision `installer-r27`.

Dieser Plan erteilt für sich allein keine externe Freigabe. Die private
Stagingbereitstellung und am 11. September 2026 genau die drei öffentlichen
r27-Runtime-Images wurden jeweils erst nach eigener Product-Owner-Freigabe
ausgeführt. Ein endgültiger Produktionsbuild sowie GitHub- und
Store-Veröffentlichungen bleiben davon getrennte, weiterhin gesperrte
Freigabepunkte.

## 1. Zielzustand

Der interaktive r27-Installer bietet nach einer erfolgreichen Docker-Prüfung
eine ausdrückliche, verständliche Zustimmung zum Herunterladen der für PLwC
benötigten Container-Images an. Nach Zustimmung gilt die Installation nur dann
als vollständig Docker-bereit, wenn alle festgelegten Digests lokal vorhanden
sind und echte, netzwerklose Probeläufe bestanden wurden. Ohne Zustimmung oder
bei einem Fehler bleibt die Kerninstallation möglich, wird aber sichtbar und
persistiert als Safe Mode ausgewiesen.

Die kanonische Quelle für PLwC-eigene Images ist die GitHub Container Registry
`ghcr.io`. Öffentliche Images müssen ohne GitHub-Anmeldung abrufbar sein. Tags
dienen nur der Anzeige; Installer und Runtime vertrauen ausschließlich auf
vollständige `@sha256:`-Referenzen.

Vorgesehenes Imageinventar für Windows/WSL2 `linux/amd64`:

| Logische Komponente | Vorgesehene Referenz | Zweck |
| --- | --- | --- |
| Document Worker | `ghcr.io/mhoedt-ai/plwc-document-worker:0.1.0` plus Digest | Dokument-, PDF-, ZIP-, Bild- und Office-Operationen |
| Node Runner | `ghcr.io/mhoedt-ai/plwc-node-runner:0.1.0` plus Digest | Node-Sandbox |
| Python Runner | `ghcr.io/mhoedt-ai/plwc-python-runner:0.1.0` plus Digest | Python-Sandbox; ersetzt die direkte mutable Runtime-Abhängigkeit von `python:3.12-slim` |

Die genauen Digests dürfen erst aus reproduzierbaren r27-Builds übernommen
werden. Die heute lokal vorhandenen Image-IDs sind Testevidenz, aber keine
Freigabedigests.

## 2. Unverrückbare Sicherheits- und UX-Grenzen

1. Kein Download und kein `docker pull` ohne eine sichtbare ausdrückliche
   Auswahl des Benutzers; Silent-Modi erteilen keine Zustimmung.
2. Kein `latest`, kein Tag-only-Pull und keine dynamische, vom Modell gelieferte
   Imageauswahl.
3. Keine GitHub-Zugangsdaten im Installer. Der öffentliche Endnutzerpfad muss
   anonym funktionieren.
4. Pro Image werden Registry, Repository, Plattform, Version und Digest in
   einem buildgenerierten Manifest festgelegt.
5. Der Installer zeigt Downloadgröße, zusätzlichen Speicherbedarf, Quelle,
   Zweck, Fortschritt, Abbruch, Timeout und Wiederholung in Deutsch und Englisch.
6. Ein bestehendes falsches oder veraltetes Tag wird nicht still als passend
   akzeptiert. Entscheidend ist der erwartete Digest.
7. Nach dem Pull folgen `docker image inspect` und ein realer, netzwerkloser
   Probelauf. Ein erfolgreicher Pull allein ist kein PASS.
8. Fehler führen zu einem ehrlichen Safe Mode oder zu einem geschlossenen
   Abbruch der ausdrücklich gewählten Imageinstallation; niemals zu einem
   falschen „vollständig bereit“.
9. Der r26-Preflight-Fehlerpfad wird mit korrigiert: stdout/stderr, Exceptiontyp
   und Reportpfad müssen auch bei unerwarteten Python-Ausnahmen erhalten bleiben.
10. Profile, Workspace und Benutzerdaten werden durch Pull, Probe, Abbruch,
    Wiederholung, Upgrade und Deinstallation nicht verändert.
11. Der vollständige Schwachstellenbericht bleibt verpflichtende Evidenz. Nach
    ausdrücklicher Product-Owner-Entscheidung vom 10. September 2026 blockieren
    ausschließlich `CRITICAL` beziehungsweise CVSS-Werte ab 9,0 das r27-Gate.
    `HIGH`, `MEDIUM`, `LOW` und `UNSPECIFIED` werden bewusst akzeptiert, aber
    weder aus dem SARIF-Bericht entfernt noch als behoben dargestellt.
12. Eine Critical-Ausnahme ist nur als gehashte OpenVEX-Evidenz zulässig. Der
    Verifier akzeptiert ausschließlich die im Code festgelegte Kombination aus
    Image, CVE, Paket, Paketversion, Begründung und bestandenem Realprobe-Vertrag.
    Der unveränderte rohe SARIF-Bericht bleibt daneben erhalten; eine generische
    Allowlist oder das Entfernen eines Fundes aus der Evidenz ist verboten.

## 3. Phasenfolge

### Phase 0 – Befund sichern und r26 einfrieren

- r26-Feldbefund redigiert dokumentieren;
- r26-Hash und bisherige Evidenz unverändert erhalten;
- r26 als nicht veröffentlichungsfähig markieren;
- fehlenden Worker und den separaten Preflight-Exitcode 1 nicht vermischen.

### Phase 1 – Anforderungen und Architektur

- Imageinventar, GHCR-Namen, Plattform und Versionsregeln festlegen;
- neue explizite Image-Opt-in-Anforderung in V-Modell und Traceability aufnehmen;
- Image-Manifest-Schema und Zustände `present`, `download_required`,
  `pulling`, `verified`, `probe_passed`, `safe_mode` und `failed` festlegen;
- Verhalten bei bereits vorhandenem richtigen/falschen Digest spezifizieren;
- Safe-Mode-, Proxy-, Offline-, Abbruch- und Wiederholungsfluss entwerfen.

### Phase 2 – Reproduzierbare Image-Buildkette

- alle `FROM`-Referenzen durch Digests fixieren;
- Debian-Paketquellen und Pakete reproduzierbar fixieren;
- fehlendes Wheelhouse-Erzeugungs-/Prüfskript wiederherstellen;
- Document Worker, Node Runner und Python Runner aus sauberem Checkout bauen;
- OCI-Labels, SBOM, Lizenzinventar, Schwachstellenscan und Provenienz erzeugen;
- zwei unabhängige Builds je Image vergleichen.

### Phase 3 – GHCR-Staging

- separaten, manuell startbaren und SHA-gepinnten GitHub-Actions-Workflow
  erstellen;
- Workflow-`GITHUB_TOKEN` auf `contents: read` begrenzen; Registryzugriffe
  ausschließlich über den separaten Environment-PAT ausführen;
- private Stagingpakete unter getrennten Namen mit einem Environment-PAT
  anlegen; der PAT braucht ausschließlich `read:packages` und
  `write:packages`;
- jedes noch nicht vorhandene Stagingpaket zuerst mit einem nicht zum
  öffentlichen Quellrepository verknüpften `scratch`-Bootstrap erzeugen und
  seine Sichtbarkeit als `private` verifizieren, bevor ein Runtime-Image
  gepusht wird;
- zuerst nur nach ausdrücklicher Freigabe in einen nicht öffentlichen
  Stagingzustand pushen;
- die bereits zweimal geprüften Images nach dem Security-Gate mit einem dritten
  deterministischen BuildKit-Registryexport pushen und dessen Manifest- sowie
  Konfigurationsdigest exakt gegen den Doppelbuild prüfen; ein
  Docker-Daemon-Reexport über `docker push` ist dafür nicht zulässig;
- Digests aus GHCR zurücklesen und mit Buildmanifest, SBOM und Provenienz
  verbinden;
- öffentliche, anonyme Pullbarkeit erst nach gesonderter Freigabe prüfen.

### Phase 4 – Installer r27

- Revision und Buildidentität auf `installer-r27` erhöhen;
- eigene Image-Akquisitionsseite beziehungsweise eindeutige Opt-in-Auswahl
  ergänzen;
- ausschließlich digest-fixierte Pulls ausführen und jedes Ergebnis erneut
  inspizieren;
- Docker-Neuinstallation/Erststart, laufenden Daemon und verzögerten WSL2-Start
  kontrolliert behandeln;
- echte Document-/Node-/Python-Probes integrieren;
- einzelne Imagezustände statt eines einzigen kombinierten Booleans speichern;
- Diagnoseexport um Preflight-/Transaktions-/Image-Akquisitionsberichte und
  Prozessausgaben erweitern;
- Safe Mode und Nachinstallation über die Konfigurationsoberfläche eindeutig
  anbieten.

### Phase 5 – Automatisierte Verifikation

- statische Verträge für Opt-in, Digestpflicht, verbotene Tag-only-Pulls,
  Silent-Modus und Sprachvollständigkeit;
- Fake-Docker-Matrix für CLI fehlt, Daemon fehlt, einzelne Images fehlen,
  richtiger/falscher Digest, Pullfehler, Timeout, Abbruch und Wiederholung;
- Clean-Checkout-Imagebuild und Zwei-Build-Vergleich;
- SBOM-, Lizenz-, Secret-, Provenienz- und Schwachstellen-Gates;
- Installer-Auswahlmatrix sowie Preflight-, Postflight- und Rollbacktests;
- echte lokale Worker-/Sandbox-Probes mit `--pull never` und ohne Netzwerk.

### Phase 6 – Windows-Systemabnahme

- sauberes Windows 11 ohne PLwC-Images, Docker bereits betriebsbereit;
- sauberes Windows 11 mit durch Setup installiertem Docker und erforderlichem
  Docker-Erststart;
- direkter r26→r27-Upgradefall mit laufender Bridge, fehlendem Worker-Image und
  unveränderten Profil-/Workspace-Daten;
- r25→r27-Migration;
- Offline-, DNS-/Proxy-, Abbruch-, Neustart-, Wiederholungs- und
  Rollbackvarianten;
- echter `plwc_document_operation`-Aufruf sowie Python- und Node-Sandboxlauf;
- Browser-Neustart und 8/8-Bridge-Smoke als Regressionsnachweis.

### Phase 7 – Releaseentscheidung

- exakten GHCR-Digestbestand einfrieren;
- exakten r27-Kandidaten bauen, hashen und vollständig gegen G0–G6 prüfen;
- bekannte Einschränkungen und Signaturstatus dokumentieren;
- separate Product-Owner-Freigaben für öffentliche GHCR-Sichtbarkeit,
  endgültigen Produktionsbuild und GitHub-/Store-Veröffentlichungen einholen.

## 4. Stop/Go-Gates und Baseline vom 2026-09-05

Die Gates entsprechen den bestehenden G0–G6 des Windows-V-Modells. Ein Gate
ist nur PASS, wenn alle Musskriterien belegt sind; Teilerfolge öffnen das
nächste Gate nicht.

| Gate | r27-Musskriterien | Heute beobachtet | Status |
| --- | --- | --- | --- |
| G0 – Anforderungsbaseline | r26-Befund, neues Image-Opt-in, exaktes Inventar, GHCR-/Sichtbarkeitsregeln, Freigabepunkte und Traceability reviewed | UR-015, UR-016 und SR-011 sind in V-Modell und vollständiger G0-Traceability ergänzt; Konflikt zu SR-008 ist durch standardmäßig ausgeschaltetes ausdrückliches Opt-in aufgelöst; keine blockierende Entscheidung offen. | **PASS / GO zu G1** |
| G1 – Architektur und Security | Digest-only, drei kontrollierte Runtime-Images, reproduzierbare Basen/Pakete, Manifest, anonymer öffentlicher Pull, Diagnose-, Safe-Mode- und Rollbackdesign reviewed | Die fünf G1-Reviews legen Single-Source-Manifest, drei feste GHCR-Repositories, reproduzierbare Buildgrenzen, standardmäßig ausgeschaltetes Opt-in, gehärtete Realprobes, Safe Mode, Besitzgrenzen, Threat Controls und vollständige Diagnose-/Exportverträge ohne offene Security- oder UX-Entscheidung fest. | **PASS / GO zu G2** |
| G2 – Implementierungs-/Testfreigabe | vollständiges Design, Tests für alle Erfolgs-/Fehlerpfade, saubere Testdaten und Freigabe zur Implementierung | 27/27 Anforderungen sind automatisierten und systemischen Tests zugeordnet; 16/16 Komponentenauswahlen, 30 Image-Akquisitionsfälle, 24 Diagnose-Faults, neun disposable Windows-Umgebungen sowie das vollständige Deutsch-/Englisch- und Redaktionsdesign sind festgelegt. Die beiden fehlenden README-Dateien sind explizite, nicht verzichtbare G3-Implementierungsobjekte. | **PASS / GO zu G3-Implementierung** |
| G3 – Code Complete/reproduzierbarer Kandidat | drei Images zweimal reproduzierbar gebaut; identische Digests; SBOM/Lizenzen/Provenienz; GHCR-Stagingdigest; r27-Code und Artefaktmanifest vollständig | Der Compilerfix-Freeze `1d8eaa4f82c2aec2fbe7212d446c7ebb05fa9fe8` bestand im privaten Staginglauf `34636663782` Doppelbuild, Realprobes, Critical-Gate, direkten BuildKit-Push, Sichtbarkeitsprüfung, exakte Digestbindung und Evidenzupload vollständig. Das resultierende `runtime-images.json` ist zugleich der unveränderte Lock des real kompilierten unsigned Systemtestkandidaten. | **PASS / GO zu G4** |
| G4 – Komponentenverifikation | alle automatisierten Image-, Installer-, Security-, Diagnose- und Regressionsprüfungen PASS | Für `1d8eaa4` bestanden lokal Python `211 PASS / 12 umgebungsbedingt SKIP`, Windows-Installer-Verträge `73/73`, der betroffene Clean-Machine-/Security-Block `51/51`, Node-Bridge `26/26`, Browser-Extension `190/190`, Public-Snapshot für 386 Dateien und ein vollständiger unsigned ISCC-Build. GitHub-CI-Lauf `34636660800` bestand alle sechs Jobs; privates Staging `34636663782` war ebenfalls vollständig grün. | **PASS / GO zu G5** |
| G5 – Systemvalidierung | Clean-Windows- und Upgrade-Matrix einschließlich echter Dokument-/Sandboxoperation, anonymer GHCR-Pull, Offline/Proxy/Abbruch/Neustart und Datenerhalt PASS | Der unsigned Kandidat aus `1d8eaa4` kompiliert und trägt exakt den geprüften Image-Lock. Nach gesonderter Product-Owner-Freigabe wurden die drei unveränderten Stagingmanifeste in Lauf `34638887032` in die Releasepakete kopiert und anschließend sichtbar auf `public` gesetzt. Lauf `34640119110` lud alle drei Images mit leerer Docker-Konfiguration wirklich per `docker pull` und bewies danach Manifestdigest, lokalen Config-Digest und RepoDigest. Die disposable Windows-Systemmatrix und die dortigen realen Installations-/Upgrade-/Fehlerpfade stehen noch aus. | **ANONYMER GHCR-PULL PASS / SYSTEMMATRIX OFFEN / STOP** |
| G6 – Release Acceptance | G0–G5 PASS; exakte Image- und EXE-Digests, Signaturstatus, Claims, Known Limitations und Product-Owner-GO vollständig | Öffentliche r27-Images sind digestgebunden verfügbar; ein unsigned Systemtestkandidat existiert. G5 ist nicht geschlossen, der Kandidat ist nicht signiert und weder endgültiger Produktionsbuild noch GitHub-/Store-Veröffentlichung sind freigegeben. | **BLOCKED / NO-GO** |

## 5. Heutige technische Baseline

- Branch: `codex/plwc-chat-bridge-rc19`; geprüfter G4-Freeze vor dem lokalen
  Phase-6-Compilerfix: `30d87d6`.
- GitHub-Repository: `mhoedt-ai/PLwC`, öffentlich; Standardbranch `main`.
- Der manuelle Workflow baut und prüft alle Images vor einem möglichen privaten
  Staging-Push; ohne Environment-Freigabe findet kein Upload statt. Ein eigener
  `GHCR_STAGING_PAT` verhindert, dass der Repository-`GITHUB_TOKEN` neue
  Stagingpakete automatisch an das öffentliche Repository bindet. Getrennte
  Paketnamen und ein quellrepositoryfreier Bootstrap erzwingen die private
  Ausgangssichtbarkeit vor dem ersten Runtime-Push.
- Lauf `34501880750` hat für `490246c0c0d09163fc6cc902edcaf0fd5e84d159`
  den direkten deterministischen Registryexport, private Sichtbarkeit,
  identische Registry-/Builddigests und den vollständigen Critical-Gate
  bewiesen. Das unveränderliche Actions-Artefakt bindet Buildbericht,
  Stagingbericht, SBOM, Lizenzen, Vulnerability-SARIF, OpenVEX und Provenienz.
- Die dabei geprüften Manifestdigests waren `sha256:e0004550…` (Document
  Worker), `sha256:5292a8a3…` (Node Runner) und `sha256:779a944b…` (Python
  Runner). Sie bleiben gültige Evidenz für genau diesen Commit, sind nach den
  anschließenden r27-Codeänderungen aber keine Freigabedigests des aktuellen
  Stands.
- `7e9b300` prüft den erforderlichen Docker-Speicher vor dem ersten Pull.
  `4c0bb78` ergänzt die separate Nachinstallation über die lokale
  Konfigurationsoberfläche mit installiertem hashgeprüftem Lock/Manager,
  neuem Plan je Versuch, eigener Bestätigung, Serialisierung und vollständiger
  Diagnosevalidierung. Der nachfolgende G4-Freeze ergänzt vollständige
  Wartungsumschläge mit Build-/Planbindung und Fallback, prüft nur vorhandene
  valide Berichtspfade, schließt aktive fehlende oder traversierende
  Diagnoseverweise und startet Docker mit einer Umgebungs-Allowlist sowie
  isoliertem anonymem `DOCKER_CONFIG`. Lokal bestanden danach Python `211`
  Tests bei `12` umgebungsbedingten Skips, Pester `73/73`, Bridge `26/26` und
  Extension `190/190`.
- OpenSSL wird in den Python-basierten Images aus dem gepinnten Trixie-Stand
  bereitgestellt. Perl ist in allen drei Laufzeitimages entfernt und die Probes
  prüfen zusätzlich, dass `/usr/bin/perl` nicht existiert und `perl` nicht
  auflösbar ist.
- `libtiff6` bleibt eine erforderliche Document-Worker-Laufzeitbibliothek. Das
  vom Scanner gemeldete CVE betrifft ausschließlich das nicht installierte
  Werkzeug `tiffcrop`; dessen Abwesenheit ist Teil des Realprobes und die
  Einzelbewertung liegt als OpenVEX-Dokument vor.
- Der finale r26-Kandidat ist nur 5.494.996 Bytes groß und enthält kein
  importierbares Docker-Imagearchiv.

### 5.1 Verifizierte private Staging-Evidenz

GitHub-Actions-Lauf `34501880750` (`PLwC r27 runtime image staging`) lief für
Commit `490246c0c0d09163fc6cc902edcaf0fd5e84d159` vollständig erfolgreich.
Der Job verifizierte vor und nach dem direkten Registryexport alle drei
Paket-Sichtbarkeiten als `private`.

| Image | Registry-Manifestdigest | Registry-Konfigurationsdigest |
| --- | --- | --- |
| Document Worker | `sha256:e00045503ac38d81685db5385a2d27e1fdc604497ebb283d67e7740b230b1620` | `sha256:d1dfd2c263c127f0151553a6482f8ecdb531ef9d974ecd9bc507f6cdf1bdc9e1` |
| Node Runner | `sha256:5292a8a3bcffb0ffe739f3cb35c7bdeb15635c57189bb07767312d058d833389` | `sha256:797715e51e30006a5a40895ae292022a9accf8d9c8ff228ef4ef1c67274eb225` |
| Python Runner | `sha256:779a944b334f4ee677ae0b716b24d298651f2f8cd25ef82fd97434b49ae31653` | `sha256:3905cf7fa18838c829b0b3a5a4d6a3aa53dc6ddd80bb61500091967e5a9defd1` |

Das unveränderliche Actions-Artefakt heißt
`plwc-r27-runtime-images-490246c0c0d09163fc6cc902edcaf0fd5e84d159`.
Nach erneutem Herunterladen wurden folgende SHA-256-Werte beobachtet:

- `image-build-report.json`:
  `6D7B8D9CAEA1AA926DE8C35372FD1F2A24FF7BFFA1462076AB9E96CEA42361F2`
- `staging-push-report.json`:
  `47674FCBE31A7B256DF8F121EF0B87431332155463AF72A7C370C5BE222DAECD`
- `runtime-images.json`:
  `D75B056832E7972491446B4460EE471A6D4ABA65CCEC4D6609E0F88A0DD343AD`

Diese Werte beweisen den privaten Stagingmechanismus für den genannten Commit.
Sie werden wegen der späteren r27-Codeänderungen nicht in einen aktuellen
Installer übernommen. Öffentliche Paketnamen, anonyme Pullbarkeit und ein
Produktionsartefakt sind damit ausdrücklich nicht freigegeben.

### 5.2 Exakte G4-Evidenz und erster Phase-6-Compilerkandidat

GitHub-CI-Lauf `34611339394` und privater Staginglauf `34611364486` liefen für
Commit `30d87d6b4b7765b7b6343cb9aae5ba071f3f2298` vollständig erfolgreich. Das
Actions-Artefakt
`plwc-r27-runtime-images-30d87d6b4b7765b7b6343cb9aae5ba071f3f2298`
trägt den GitHub-Artefaktdigest
`sha256:1575a9bde31a3b80380491432a7ee0199610afbafaf77ed875fe90e13cacb04c`.
Nach erneutem Herunterladen wurden folgende SHA-256-Werte geprüft:

- `image-build-report.json`:
  `B4D15497A303E545483616A4D375325B5462A4A2A0E820926609747A7D5C2052`
- `staging-push-report.json`:
  `BA672CFBE260167DB258AD29BDC9C1E84778CC19D69744DB253FD0282189A895`
- `runtime-images.json`:
  `B90ED55A217EBB81E4284E334C29570BE698CF1C3C4C37F4929180289BD92B9E`

| Image | Registry-Manifestdigest | Registry-Konfigurationsdigest |
| --- | --- | --- |
| Document Worker | `sha256:dd75468976bf19de9c96107a83441b33dbdd2b58783f250eaf6978e869a118e4` | `sha256:4e890bb0df44dc2e33888eb96810356d0ad1f3afa2af2820b97d87f552bdb39c` |
| Node Runner | `sha256:8339a35b93e7cb30a2b876384858d1533edea1f8bdf26d073bc054c7de44d84a` | `sha256:905694974c75c513c6e86c06e40767663735e02eaa10baf590deaf8cca4360bf` |
| Python Runner | `sha256:0886a33e7d9c4e9e789fbb2354c36162ea9b7bc6643a4492907b2f57cda58b20` | `sha256:3e4ba66b7606ba0de9be73e9739366d43107dd531e3d18733385016620d14a99` |

Der erste vollständig kompilierte Phase-6-Kandidat wurde ausschließlich als
lokaler unsigned Testbuild erzeugt. Seine EXE hatte 5.516.102 Bytes und den
SHA-256-Wert
`AA6CBDB55700C7EA7812EEFB78E90265E4902390FEA95440A9939B1D9F38995B`;
Authenticode meldete erwartungsgemäß `NotSigned`. Der eingebettete Image-Lock
war bytegleich mit `runtime-images.json` aus Lauf `34611364486`. Dieser Hash
ist keine Releaseidentität: Der Kandidat entstand aus dem noch nicht
eingecheckten Compilerfix und dient nur als Nachweis, dass der reale
unsigned-Buildpfad kompiliert.

### 5.3 Compilerfix-Freeze und öffentliche GHCR-Verifikation

Der exakte r27-Image- und Installerquellstand ist
`1d8eaa4f82c2aec2fbe7212d446c7ebb05fa9fe8`. GitHub-CI-Lauf
`34636660800` und privater Staginglauf `34636663782` liefen für diesen Commit
vollständig erfolgreich. Das Staging-Artefakt
`plwc-r27-runtime-images-1d8eaa4f82c2aec2fbe7212d446c7ebb05fa9fe8`
trägt den GitHub-Artefaktdigest
`sha256:7a54757f4d4727ec3cfd908da43904a51c9179e418c6a6f371f3324f51ab9e31`.
Nach erneutem Herunterladen wurden folgende SHA-256-Werte geprüft:

- `image-build-report.json`:
  `7805F841B42C28D764BAD3B7D699EE29B16C2FE81FA1114321242403D36D276A`
- `staging-push-report.json`:
  `38A9DB9E845605901AD713A51FC76287322D271C503DED8AAA26D26562F65CAF`
- `runtime-images.json`:
  `9EEE34D0E30530AD7CB1CA38D75E5ABE33ED0B1991FDFE55E47C641C2583C18F`

Nach ausdrücklicher Product-Owner-Freigabe vom 11. September 2026 kopierte
Lauf `34638887032` ausschließlich die drei geprüften Manifeste per
`imagetools create --prefer-index=false` in zunächst private Releasepakete.
Er änderte weder Imageinhalt noch Digest. Erst nach erfolgreicher privater
Verifikation wurden genau diese drei Pakete in der GitHub-Oberfläche dauerhaft
öffentlich geschaltet. Lauf `34639151326` bestätigte zunächst mit leerer
Docker-Konfiguration den anonymen Manifestzugriff. Der anschließend verstärkte
Lauf `34640119110` führte für alle drei Referenzen einen echten `docker pull`
ohne Zugangsdaten aus und verglich danach zusätzlich die lokale Image-ID sowie
den RepoDigest. Damit ist nicht nur der Manifestabruf, sondern der vollständige
anonyme Pull belegt:

| Öffentliche Referenz | Manifestdigest | Konfigurationsdigest |
| --- | --- | --- |
| `ghcr.io/mhoedt-ai/plwc-document-worker:0.1.0` | `sha256:9f06960d30bc91701161d5490c24611f4e630ee8d0ab57eef04c6f7862df93e1` | `sha256:af6757f5fb28204b7f61b7076cad00fbe4e0a71e11276db5067419083718a6df` |
| `ghcr.io/mhoedt-ai/plwc-node-runner:0.1.0` | `sha256:fccb8cc036d24c764504749d802674e6e6f3c9c72726334b73aa674830e7b6f2` | `sha256:9a8a4a3c78c9f8896b0370e033b56b742b1227e03e7d711630399164e399ee7d` |
| `ghcr.io/mhoedt-ai/plwc-python-runner:0.1.0` | `sha256:83d7d224abbd287fab225a8d81c29b98795440af75edad3a70bf5f4b0c6278bc` | `sha256:95fdfdbd4a5f1f67d3a485a773e5e7a4e9b73295f78fad70a5407f8519dd5917` |

Die unveränderlichen Promotion-/Verifikationsartefakte und ihre nach dem
Download geprüften Dateihashes sind:

- `plwc-r27-private-promotion-2d850c27b6e7cf8c2717b9fc39560904ca7b9351`,
  GitHub-Artefaktdigest
  `sha256:402325275d9ea770dc2d287bf4ce83c99bbcf1dd822826e2b7b25bb0b55edf5a`,
  Bericht-SHA-256
  `9CA4A5C894EB6E6AE23901F3C3289F24181B4FE9A215A92B2AA79DB16C073F22`;
- `plwc-r27-public-verification-2d850c27b6e7cf8c2717b9fc39560904ca7b9351`,
  GitHub-Artefaktdigest
  `sha256:e210da1a83e89de47f906c5d8177f04a3b899344de752420fb3e5909f6006669`,
  Bericht-SHA-256
  `6E4653D630A8CA7ACED9414CD84D293DDE649F82953E4760AC09329709691417`
  (anonymer Manifestabruf);
- `plwc-r27-public-verification-e54a2019d898cfefaf23bb9eed4e275938e4ff24`,
  GitHub-Artefaktdigest
  `sha256:f2ee0fd7dd85dc590ac9862b25f17830635d8fb5d9f551e30c00f23e5ffb7dbf`,
  Bericht-SHA-256
  `6E4653D630A8CA7ACED9414CD84D293DDE649F82953E4760AC09329709691417`
  (vollständiger anonymer Pull plus lokaler Identitätsabgleich).

Der reale unsigned Systemtestkandidat aus diesem Freeze heißt
`PLwC-Setup-1.0.0-installer-r27-TEST-UNSIGNED-1d8eaa4.exe`, ist 5.516.329
Bytes groß und hat SHA-256
`1E69FB1BC3B05DAD18E0C93194187FEFA4709172FA3DD86893193177E1A55272`.
Er ist ausdrücklich kein Produktionsartefakt. Dieser Kandidat wurde am
12. September 2026 nach einem Systemtestbefund zurückgezogen: Beim Prüfen der
lokalen Docker-Images wechselte die Fortschrittsanzeige wiederholt zurück zur
Image-Auswahlseite und startete die Inventur erneut.

### 5.4 G5-Regressionsbefund: wiederholte Imageinventur

Die Ursache lag in `CurPageChanged`: `InventoryRuntimeImages` setzte zwar
`RuntimeImagesInventoryAttempted`, der Seiteneinstieg wertete diese Sperre aber
nicht aus. Das Ein- und Ausblenden der untergeordneten Fortschrittsseite löst
erneut `CurPageChanged` aus. Dadurch konnte dieselbe Inventur während oder
unmittelbar nach dem ersten Lauf erneut beginnen; sichtbar waren Flackern und
ein Zurückspringen zur laufenden Fortschrittsseite.

Der korrigierte Ablauf startet die Inventur nur, wenn weder eine
Runtime-Image-Operation aktiv ist noch bereits eine Inventur versucht wurde.
Ein statischer Regressionstest erzwingt beide Sperren vor dem einzigen
Seiteneinstiegsaufruf. Der isolierte Payload-Check sowie die vollständige,
CI-identische Installer-Suite mit Pester 3.4.0 bestanden danach mit **73/73**.
Der Ersatz-Testkandidat und sein SHA-256 werden erst nach einem neuen unsigned
Build eingetragen. G5 bleibt bis zum erneuten Windows-Systemtest offen.

Ein zusätzlicher privater Kontrolllauf `34677907208` für Commit `480a394` war
vollständig erfolgreich und erzeugte das unveränderliche Artefakt
`plwc-r27-runtime-images-480a394afa045f2fadafc7dccd1b9b0f46e72b8a`
mit GitHub-Artefaktdigest
`sha256:4a155233ac6f258f3faf4f3ae41504bf2cf8d53cf4d60f54b8c5ba7251c152e4`.
Sein Manifest-SHA-256 ist
`C87510E437B902EBD1FB00A1F859212E368EF2167DC8F0F89B5E457D24CCF4BF`.
Die darin enthaltenen Image-Digests unterscheiden sich allein schon durch das
commitabhängige OCI-Revisionslabel vom öffentlichen Freeze. Sie bleiben privat
und werden nicht in die öffentlichen Pakete übernommen.

Der Installer-Build darf deshalb den bereits genehmigten öffentlichen
Image-Freeze weiterverwenden, aber nicht pauschal ein Manifest eines fremden
Commits akzeptieren. Vor der Manifestprüfung weist er mit Git nach, dass der
Manifest-Commit ein Vorfahr von `HEAD` ist und dass `docker/`, `security/vex/`,
Image-Build-, Wheelhouse- und Verifikationsskripte sowie Runtime-Manager und
Manifest-Schema gegenüber diesem Commit selbst im aktuellen Arbeitsbaum
unverändert sind. Erst nach diesem Nachweis wird die vorhandene vollständige
Evidenz mit `--allow-foreign-commit` geprüft. Jede Änderung an einem dieser
Imageeingänge stoppt den Build geschlossen und verlangt neue Imageevidenz und
eine neue Freigabe. Damit erfordert ein reiner Installer-UI-Fix keine
inhaltlich unnötige Neuveröffentlichung der drei Container-Images.

## 6. Nächster zulässiger Schritt

G0 bis G4 sind geschlossen. Die öffentliche GHCR-Sichtbarkeit und der anonyme,
digestgebundene Endnutzerzugriff sind als Teil von G5 belegt. Der bisherige
unsigned Testkandidat ist wegen der wiederholten Imageinventur zurückgezogen.
Der nächste zulässige Schritt ist ein neuer, eindeutig benannter unsigned
Ersatz-Testkandidat aus dem korrigierten Quellstand. Erst danach wird die
Phase-6-Systemmatrix fortgesetzt: zuerst Clean Windows 11 mit bereits
betriebsbereitem Docker, danach Docker-Erststart sowie Upgrade-, Offline-/Proxy-,
Abbruch-, Neustart-, Wiederholungs- und Rollbackvarianten. Dabei sind echte
Dokument-, Python- und Node-Aufrufe, Profil-/Workspace-Datenerhalt,
Browser-Neustart und 8/8-Bridge nachzuweisen. Ein endgültiger Produktionsbuild
und jede GitHub-/Store-Veröffentlichung bleiben gesperrte Freigabepunkte.

## 7. Separat aufgenommener Bridge-Befund

Am 6. September 2026 wurde während der r27-Arbeit ein neuer, noch nicht
untersuchter Laufzeitbefund gemeldet: Während ChatGPT einen JSON-Toolaufruf
sichtbar in den Chat schreibt, verschwindet anschließend der betreffende
Chat-Inhalt, nur die Benutzereingabe bleibt sichtbar und die Ausführung steht.

Dieser Befund wird in diesem Arbeitsschritt weder der Imagebereitstellung noch
dem Installer zugerechnet. Es erfolgt hier ausdrücklich keine Ursachenanalyse
und keine Bridge-Änderung. Vor einer PLwC-Gesamtfreigabe muss er separat
reproduziert, eingegrenzt und gegen die bestehenden Bridge-Regressionstests
bewertet werden.

Zusätzliche Beobachtung des Nutzers: Das Verhalten tritt offenbar insbesondere
auf, wenn eine Kette von Aufgaben unterbrochen oder abgebrochen wurde. Auch
diese Korrelation ist noch nicht verifiziert und wird nicht als festgestellte
Ursache behandelt.
