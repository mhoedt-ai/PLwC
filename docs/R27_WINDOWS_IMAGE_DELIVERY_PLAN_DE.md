# PLwC 1.0 / Windows Installer r27 – GHCR-Imagebereitstellung und Gates

Stand: 2026-09-10

Status: **PLAN / G0–G2 PASS / G3–G5 STOP / G6 NO-GO**

Dieser Plan korrigiert den auf einem realen Windows-11-System beobachteten
r26-Vertriebsfehler: Docker Desktop war vorhanden, das für
`plwc_document_operation` erforderliche Image jedoch nicht. Der Installer r26
prüft lokale Images nur mit `docker image inspect`; er lädt oder importiert sie
nicht. Der unveränderliche r26-Kandidat mit SHA-256
`d604e7714ab4838337ac036a91335292c7315fd9b0be7d16c54c08b39797dc65`
wird nicht überschrieben. Jede Korrektur trägt die Revision `installer-r27`.

Es wird durch diesen Plan weder ein Container-Image hochgeladen noch ein
Installer gebaut oder veröffentlicht. Externe Uploads, öffentliche
Paket-Sichtbarkeit, ein endgültiger Produktionsbuild und jede Veröffentlichung
bleiben eigene Freigabepunkte des Product Owners.

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
- Workflowrechte minimal auf `contents: read`, `packages: write` und die
  tatsächlich verwendeten Attestierungsrechte begrenzen;
- zuerst nur nach ausdrücklicher Freigabe in einen nicht öffentlichen
  Stagingzustand pushen;
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
| G3 – Code Complete/reproduzierbarer Kandidat | drei Images zweimal reproduzierbar gebaut; identische Digests; SBOM/Lizenzen/Provenienz; GHCR-Stagingdigest; r27-Code und Artefaktmanifest vollständig | Die technische Critical-Bereinigung liegt lokal vor: Python-Basen und Document-Worker-Pakete sind auf den gepinnten Trixie-Stand angehoben, das nicht benötigte Perl ist aus allen drei Images entfernt, und der nur `tools/tiffcrop.c` betreffende TIFF-Fund besitzt eine eng festgelegte OpenVEX-Bewertung. Roher SARIF und VEX werden getrennt gehasht. Ein lokaler Doppelbuild aller drei Images einschließlich gehärteter Realprobes ist reproduzierbar; er ist wegen uncommitted Quellen und lokal nicht authentifiziertem Scout ausdrücklich nur Entwicklungsevidenz. Ein sauberer, authentifizierter GitHub-Lauf und der GHCR-Stagingdigest fehlen noch. | **FAIL / STOP** |
| G4 – Komponentenverifikation | alle automatisierten Image-, Installer-, Security-, Diagnose- und Regressionsprüfungen PASS | Aktueller lokaler Zwischenstand nach der Critical-Bereinigung: Python `161 PASS / 12 umgebungsbedingt SKIP`, Bridge `26/26`, Extension `190/190`; der frühere Installer-Pester-Stand ist `73/73`, muss für den neuen Commit aber in GitHub CI erneut bestätigt werden, weil Pester 3.4.0 lokal nicht installiert ist. Der Gate-Status bleibt gesperrt, bis G3 geschlossen ist und ein vollständiger Image-Security-/Realprobe-Lauf unter der freigegebenen Critical-only-Regel bestanden wurde. | **STOP – G3 VORGESCHALTET** |
| G5 – Systemvalidierung | Clean-Windows- und Upgrade-Matrix einschließlich echter Dokument-/Sandboxoperation, anonymer GHCR-Pull, Offline/Proxy/Abbruch/Neustart und Datenerhalt PASS | Realer Nutzerbefund zeigt `worker_missing`. Der r26→r27-Pfad existiert noch nicht. Der separate Preflight-Exitcode 1 ist nicht vollständig diagnostiziert, weil der referenzierte JSON-Bericht im Export fehlt. | **FAIL / STOP** |
| G6 – Release Acceptance | G0–G5 PASS; exakte Image- und EXE-Digests, Signaturstatus, Claims, Known Limitations und Product-Owner-GO vollständig | Kein r27-Artefakt; r26 durch neuen Feldbefund zurückgezogen; keine Veröffentlichungsfreigabe. | **BLOCKED / NO-GO** |

## 5. Heutige technische Baseline

- Branch: `codex/plwc-chat-bridge-rc19`; letzter eingecheckter Stand vor der
  Critical-Bereinigung: `87e278e778dbb9536bc4902f6c316d5bf6585bfc`.
- GitHub-Repository: `mhoedt-ai/PLwC`, öffentlich; Standardbranch `main`.
- Der manuelle Workflow baut und prüft alle Images vor einem möglichen privaten
  Staging-Push; ohne Environment-Freigabe findet kein Upload statt.
- Der lokale Entwicklungs-Doppelbuild nach der Critical-Bereinigung ergab
  reproduzierbar `sha256:01c4e259…` (Document Worker), `sha256:22ce0357…`
  (Node Runner) und `sha256:a218bd0d…` (Python Runner). Alle netzwerklosen,
  nicht privilegierten Realprobes bestanden. Diese Digests enthalten noch die
  Identität des vorherigen Commits und sind deshalb keine Freigabedigests.
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

## 6. Nächster zulässiger Schritt

G0 bis G2 sind geschlossen. Nächster zulässiger Schritt ist das Einchecken der
Critical-Bereinigung, die normale CI-Verifikation und anschließend ein neuer
vollständiger, authentifizierter Image-Lauf aus exakt diesem sauberen Commit.
Der private GHCR-Staging-Push und damit das Schließen von G3 benötigen erneut
die ausdrückliche Product-Owner-Freigabe. Bis dahin werden weder Stagingimages
hochgeladen noch Freigabedigests in den Installer übernommen.

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
