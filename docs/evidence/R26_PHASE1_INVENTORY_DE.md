# PLwC 1.0 / Installer r26 – Phase 1: Inventar und Kompatibilität

Stand: 2. September 2026

## Zentraler Vertrag

`config/compatibility-matrix.json` ist die maschinenlesbare Quelle für die
PLwC-1.0-Kompatibilitätsfamilie. Das zugehörige JSON-Schema liegt in
`config/compatibility-matrix.schema.json`. Beide Dateien werden als gehashter
Gateway-Payload in den Windows-Installer aufgenommen.

Die Matrix trennt ausdrücklich:

- semantische Paket-/Produktversion,
- Protokoll- beziehungsweise Vertragsversion,
- Buildrevision,
- Build-ID und Build-Identity-Schemaversion,
- SHA-256 des konkreten Artefakts,
- lokale beziehungsweise Releasequelle und deren Vertrauensstatus.

Die Browser-Erweiterungsversionen `1.0.0` und `1.0.1` liegen beide im
unterstützten Paketbereich und verwenden weiterhin den Bridge-Vertrag `1.0.0`.
Eine höhere Paketversion ist damit kein Protokollbruch.

## Status- und Vertrauensmodell

Das gemeinsame Statusmodell umfasst:

`ready`, `compatible`, `recommended_update`, `required_update`, `missing`,
`optional`, `unknown` und `mixed_installation`.

Quellen werden als `verified_local`, `observed_local`, `trusted_release`,
`unverified` oder `unavailable` markiert. Nur eine `trusted_release`-Quelle darf
aus einer höheren verfügbaren Version eine Updateempfehlung oder ein
Pflichtupdate ableiten. Eine fehlende Onlineauskunft bleibt `unknown` und macht
eine lokal kompatible Installation nicht inkompatibel.

## Klassifizierer

`plwc_gateway.installation.component_inventory` validiert die Matrix und erzeugt
ein einheitliches Inventar für Konfigurationsseite, Doktor und Installer. Mehrere
aktive Laufzeitpfade haben Vorrang und ergeben `mixed_installation`. Ein
optionaler, nicht installierter Dienst ergibt `optional`; fehlende Belege ergeben
`unknown`. Build- und 8-Tool-Verträge werden fail-closed bewertet.

## Gate-Nachweis

Die Phase-1-Tests decken ab:

- Extension `1.0.1` mit Protokoll `1.0.0` als bereit/kompatibel,
- Extension `1.0.0` mit vertrauenswürdigem `1.0.1`-Hinweis als kompatibles,
  empfohlenes Update,
- inkompatibles Protokoll und 7/8 Werkzeuge als Pflichtupdate,
- parallele `bridge`-/`chat-bridge`-Pfade als Mischinstallation,
- fehlende optionale und unbekannte Komponenten,
- nicht vertrauenswürdige Onlineversion ohne Updateklassifikation,
- getrennte Produktversion, Protokollversion, Buildrevision, Build-ID und Hash,
- Ablehnung unbekannter Komponenten und fremder Matrix-Schemaversionen.
