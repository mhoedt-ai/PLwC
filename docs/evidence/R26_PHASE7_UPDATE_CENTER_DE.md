# r26 Phase 7 – Updatezentrale

Stand: 2026-09-03

## Ergebnis

Phase 7 ist **PASS**. Die gemeinsame Updatelogik liegt im Gateway-/Installer-
Bereich und ist nicht von der Browser-Bridge abhängig. Es wurde weder ein
r26-Setup erzeugt noch ein Store- oder Releaseartefakt veröffentlicht.

## Sicherheitsarchitektur

- `src/plwc_gateway/installation/update_center.py` prüft ein begrenztes
  UTF-8-JSON-Manifest mit kanonischer Darstellung und
  `rsa-sha256-pkcs1v15`-Signatur gegen einen expliziten Truststore.
- Das Manifest enthält Schemaversion, Produktversion, Installerrevision,
  Komponentenversionen und Kompatibilitätsbereiche, Veröffentlichungszeit,
  empfohlenes/Pflichtupdate, zweisprachige Hinweise sowie URL, Größe, SHA-256
  und Buildidentität jedes Artefakts.
- Nur HTTPS-URLs ohne eingebettete Zugangsdaten werden akzeptiert. JSON-
  Duplikatschlüssel, unbekannte Signaturschlüssel, unsichere Dateinamen und
  auseinanderlaufende Artefakt-/Buildidentitätshashes werden abgelehnt.
- Nur das letzte **signaturverifizierte** Manifest wird atomar gecacht. Offline-
  und Ablehnungszustände behalten Zeitpunkt und Hinweis auf das letzte gültige
  Ergebnis, ersetzen dieses aber nicht.
- Automatische Prüfungen sind auf sechs Stunden begrenzt; eine manuelle Prüfung
  ist jederzeit möglich. Es werden keine Profil- oder Workspaceinhalte
  übertragen und keine Telemetriedaten gesendet.
- Downloadplan, Download und Installerstart sind getrennt. Download und Start
  benötigen jeweils eine eigene ausdrückliche Bestätigung. Vor dem Start werden
  Dateigröße, SHA-256 und die durch denselben Hash gebundene signierte
  Buildidentität erneut geprüft.
- Ein Installerfehler verweist auf den vorhandenen r26-Rollback-/Fehlerbericht;
  Postflight und Rollback bleiben Aufgabe des in Phase 5 geprüften Installers.

## Oberfläche und Packaging

- Die einzige lokale PLwC-Konfigurationsoberfläche zeigt empfohlenes oder
  notwendiges Update, `zuletzt geprüft`, `letzte gültige Prüfung`,
  Releasehinweise und Sicherheitsfehler.
- Der Downloadplan zeigt Plan-ID, Dateiname, Größe, SHA-256 und Buildidentität.
- Download- und Installationsbestätigung sind separate UI-Schritte und separate
  authentisierte Loopback-Endpunkte.
- Release-Manifest- und Truststore-Schemas werden in den Gateway-Payload
  aufgenommen. Das Updatezentrum selbst wird als gemeinsames Python-Modul
  installiert.

## Produktions-Trustanker

`config/release-trust.json` ist absichtlich leer und arbeitet damit fail-closed.
Die positive Signaturprüfung verwendet ausschließlich einen synthetischen,
nicht produktiven Testschlüssel. Ein echter öffentlicher Release-Schlüssel darf
erst als kontrollierter Releaseinput provisioniert werden; ohne ihn kann kein
Live-Manifest als vertrauenswürdig gelten. Es befindet sich kein privater
Schlüssel im Repository.

Nachgelagerter Phase-8-Stand vom 2026-09-04: Der freigegebene öffentliche
RSA-4096-Verifikationsschlüssel wurde inzwischen in `release-trust.json`
gepinnt. Der private Schlüssel blieb außerhalb des Repositorys und
DPAPI-geschützt. Die obige Aussage beschreibt den bewussten Zustand beim
Abschluss des Phase-7-Gates.

## Ausgeführte Gates

- Updatezentrum positiv/negativ: **9/9 PASS**
  - gültige Signatur: PASS
  - manipuliertes bzw. nicht vertrauenswürdiges Manifest: abgelehnt
  - doppelter JSON-Schlüssel/unsichere URL: abgelehnt
  - Intervallbegrenzung und Offline-Cache: PASS
  - manipulierte Liveantwort ersetzt gültigen Cache nicht: PASS
  - getrennte Download-/Installationsbestätigung: PASS
  - falscher Hash und abgebrochener Download: abgelehnt, keine EXE bleibt zurück
  - Installerfehler referenziert r26-Rollbackbericht: PASS
- Update- und vollständige Konfigurations-UI-Zieltests: **28/28 PASS**
- JavaScript-Syntaxprüfung: PASS
- Vollständige Python-Suite: **104 PASS, 6 SKIPPED**
- Windows-Installervertrag: **72/72 PASS**
- Isoliertes `ValidateOnly`: PASS, ISCC nicht aufgerufen
- Kanonische `stage`-/`dist`-Bäume während `ValidateOnly`: bytegenau
  unverändert
- Isoliertes Payloadmanifest:
  - SHA-256:
    `85bf164935cd50930f57b603ac8b59c34bfbcd1bb9e69f1b12be3cff38c31fbb`
  - Revision: `installer-r26`
  - Browser-Erweiterung: `1.0.1`
  - Dateien: `3525`
  - Payload: `18089746` Byte
- Setup-EXEs im isolierten ValidateOnly-Ausgabebaum: **0**
- r26-Setup-EXEs in `dist`/`.unsigned-build-r26`: **0**

## Gate-Entscheidung

**PASS:** Manipuliertes Manifest und falscher Artefakthash werden abgelehnt;
ohne separate Bestätigung wird weder heruntergeladen noch installiert. Ein
Produktions-Trustanker und ein echtes signiertes Release-Manifest bleiben
bewusst Teil des noch nicht freigegebenen Releasegates.
