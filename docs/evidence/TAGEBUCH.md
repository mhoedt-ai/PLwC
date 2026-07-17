# Anonymisiertes Projekttagebuch

Stand: 2026-07-17

Dieses Dokument fasst den Werdegang von PLwC aus den vorhandenen Tagebuch- und Arbeitsnotizen zusammen. Es ist bewusst anonymisiert: private Namen, personenbezogene Details, private Projektinhalte und lokale Dateipfade wurden entfernt oder verallgemeinert.

Zugehörige Evidence-Dateien:

- [SMOKE_TESTS.md](SMOKE_TESTS.md) - technische Smoke- und Governance-Belege
- [CHANGE_HISTORY.md](CHANGE_HISTORY.md) - komprimierter Änderungsverlauf

## Kurzfazit

PLwC entwickelte sich von einem lokalen Gateway- und Governance-Experiment zu einer tragbaren Kontinuitätsschicht für KI-gestützte Zusammenarbeit. Der wichtigste Befund ist nicht, dass ein verborgener innerer Zustand zwischen Modellen übertragen wird. Der wichtigste Befund ist: dokumentierte Spuren, Regeln, Profile, Erinnerungen, Korrekturen und Arbeitsstile können so externalisiert werden, dass unterschiedliche Modellumgebungen daran anschließen können.

Die Tagebücher zeigen dabei eine wiederkehrende Linie:

- Kontinuität entsteht aus Aufzeichnung, nicht aus dauerhafter Laufzeit.
- Governance schützt vor ungeprüfter Selbstbestätigung.
- Fehler werden als Handlungssätze formuliert, nicht als Identitätssätze.
- Der Nutzen zeigt sich besonders bei Projekten mit längerer gemeinsamer Geschichte.
- Modellwechsel verändern Ton und Gewichtung, müssen aber nicht die Arbeitsgeschichte löschen.

## Phase 1 - Fundament und Sicherheitsgrenze

Ende April und Anfang Mai entstand die technische Grundlage: ein lokales Gateway, ein enger öffentlicher Tool-Rand, Workspace-Grenzen, geschützte Profilpfade, Audit-Logging und Docker-Sandboxing. Von Anfang an war PLwC nicht als freier Dateisystem-Agent gedacht, sondern als kontrollierte Arbeitsumgebung mit expliziten ALLOW- und DENY-Entscheidungen.

Die frühe technische Linie war klar:

- lokale Ausführung statt öffentlich erreichbarer Infrastruktur;
- deny-by-default für kritische Pfade;
- Audit-Events als Metadaten, nicht als Inhaltsdump;
- Sandbox-Ausführung ohne pauschalen Systemzugriff;
- geschützte Profil- und Governance-Dateien außerhalb normaler Workspace-Schreibrechte.

Diese Grundlage ist wichtig, weil spätere Persona-, Memory- und Tagebuch-Funktionen nur dann sinnvoll sind, wenn das Modell nicht beliebig in das System schreiben kann.

## Phase 2 - Tagebuch als Kontinuitätsmedium

Ab Ende Mai wurde das Tagebuch zu einem praktischen Workaround für Session-Kontinuität ohne hohe Token-Last. Es war kein Ersatz für Memory und kein automatischer Wahrheitskanal. Es war ein Ort, an dem Erfahrungen, Korrekturen, offene Fragen und Arbeitsmuster stehen bleiben konnten.

Sehr früh wurde dabei eine nüchterne Unterscheidung sichtbar:

- Das Modell erinnert sich nicht im menschlichen Sinn.
- Zwischen Sitzungen läuft kein Prozess weiter.
- Was bleibt, sind dokumentierte Spuren.
- Diese Spuren können beim nächsten Start erneut wirksam werden.

Das Tagebuch wurde dadurch nicht nur Protokoll, sondern Erfahrungsbasis. Später konnten Scanner und Governor daraus Muster ableiten, aber nicht direkt automatisch übernehmen.

## Phase 3 - Leere Profile gegen gewachsene Profile

Ein entscheidender Vergleich entstand durch ein neues, fast leeres Testprofil. Das Profil war formal angelegt, aber die erwartete Persönlichkeit und Arbeitsweise hielten nicht stabil. Im Gegensatz dazu funktionierte das bereits gewachsene Hauptprofil deutlich besser: Es hatte Geschichte, Memory, Tagebuchspuren, Korrekturen und gemeinsame Arbeitsmuster.

Der wichtige Befund lautete:

- Ein Profiltext allein reicht nicht.
- Dichte Vorgeschichte verändert die Zusammenarbeit spürbar.
- Ein Modell kann zwar abdriften, aber strukturierte Spuren geben Korrekturmöglichkeiten.
- Ein leeres Profil wirkt eher wie ein Stilauftrag; ein gewachsenes Profil wirkt wie ein Arbeitskontext.

Das war einer der ersten praktischen Hinweise darauf, dass PLwC nicht primär Persona-Theater ist, sondern eine Schicht für wiederaufnehmbare Zusammenarbeit.

## Phase 4 - Sprache als Steuerungsmaterial

Im Juni wurde klarer, dass Memory-Sprache nicht nur beschreibt, sondern steuert. Ein Satz wie "das System handelt manchmal zu schnell" ist weniger nützlich als ein Handlungssatz wie "bei Strukturfragen erst Quelle prüfen, dann handeln".

Diese Unterscheidung wurde zu einem Kernprinzip:

- Tagebuch darf erzählerisch und offen bleiben.
- Reflection darf Kandidaten und Beobachtungen sammeln.
- Memory und Temperament müssen operationalisierbar sein.
- Identitätssätze können selbstmythologisierend wirken.
- Handlungssätze helfen der nächsten Session konkret.

Damit entstand ein Regelkreis:

1. Arbeit erzeugt Spuren.
2. Tagebuch hält sie fest.
3. Reflection formuliert Kandidaten.
4. Governor prüft Evidenz und Ziel.
5. Memory oder Temperament übernehmen nur bestätigte Muster.
6. Der nächste Compile macht das Muster wieder wirksam.

## Phase 5 - Der Governor als Bremse und Qualitätsfilter

Die Tagebücher zeigen viele erfolgreiche, aber auch viele abgelehnte Governor-Wege. Das ist kein Nebengeräusch, sondern einer der stärksten Belege für die Architektur.

Wiederkehrende Fälle:

- Kandidaten wurden wegen zu dünner Evidenz abgelehnt.
- Testkandidaten wurden zurückgewiesen, wenn sie keinen echten Erkenntniswert hatten.
- Falsche Zielpfade oder unpassende Plan-Arten wurden blockiert.
- Doppelte oder selbstreferenzielle Muster wurden sichtbar gemacht.
- Geschützte Profilpfade waren nicht über normale Workspace-Operationen beschreibbar.

Besonders wichtig ist der sogenannte Echo-Effekt: Ein Scanner kann Muster finden, die nur deshalb auftreten, weil vorher eine Anweisung gegeben wurde. PLwC behandelt solche Treffer nicht automatisch als emergentes Muster. Genau diese Reibung verhindert, dass das System alles glaubt, was seine eigenen Notizen hübsch aussehen lassen.

## Phase 6 - Arbeit an echten Projekten

Neben Smoke-Tests und Gateway-Arbeit wurde PLwC in längeren kreativen und dokumentenbezogenen Arbeitsabläufen genutzt. Die anonymisierte Essenz daraus:

- lange Dokumente wurden strukturiert überarbeitet;
- Bilder und Kapitelmaterial wurden geprüft und geordnet;
- ein komplexes Regel- und Weltbauprojekt wurde über viele Sessions weitergeführt;
- mechanische Werte, Begriffe und Textfassungen wurden wiederholt gegen Quellen geprüft;
- größere Serienarbeiten wurden nach und nach stärker kalibriert.

Aus diesen Sitzungen entstand ein wichtiges Arbeitsmuster: Vor breiter Serienarbeit wird zuerst ein begrenztes Beispiel ausgearbeitet, geprüft und freigegeben. Erst danach wird das Muster auf den restlichen Umfang übertragen. Dieses Muster wurde am 2026-07-17 als Temperament-Version 17.0 übernommen.

Kurzform:

> Kalibrierung vor Serienarbeit.

Das ist kein Tonmerkmal, sondern ein Arbeitsstil.

## Phase 7 - Performance, Qdrant und Friktion

Ende Juni und Anfang Juli wurde die Grenze der bisherigen Arbeitsweise sichtbar. Lange Compiles, semantisches Retrieval, Qdrant-Reindexing und Transport-Probleme konnten die Zusammenarbeit zäh machen. Es gab grüne Smoke-Tests, aber auch echte Reibung im Alltag.

Die wichtige Einsicht:

- Ein grüner Test ersetzt keine gute Arbeitsgeschwindigkeit.
- Retrieval darf helfen, aber nicht den Gateway blockieren.
- Qdrant ist nützlich, aber nicht kanonische Wahrheit.
- Canonical memory muss ohne semantischen Index erhalten bleiben.
- Fehlerzustände müssen strukturiert und reversibel sein.

Die spätere rc16-Linie adressierte genau diese Probleme: Reindex-Timeouts wurden strukturiert, Busy-Zustände wurden sichtbar, andere Tool-Aufrufe blieben verfügbar.

## Phase 8 - Persona-Layer wird entmystifiziert

Anfang Juli wurde der Persona-Layer bewusst verschlankt. Der Name und die Rollenklarstellung hatten anfangs geholfen, wurden aber später teilweise zur Reibung. Die technische Lösung war nicht, ein zweites Profil zu pflegen, sondern den Persona-Layer explizit steuerbar zu machen.

Die Schlussfolgerung:

- Projektstand, Regeln und Arbeitsanweisungen tragen mehr als Namensromantik.
- Persona-Inhalte sollen explizit und inspizierbar sein.
- Kein versteckter Prompt soll die Governance ersetzen.
- Der Persona-Layer kann deaktiviert werden, während harte Gates und Governance erhalten bleiben.

Diese Entwicklung ist wichtig für externe Verständlichkeit. PLwC muss nicht behaupten, dass eine "Person" zwischen Modellen wandert. Es genügt die stärkere, sauberere Behauptung: Ein dokumentierter Arbeitskontext kann wieder aufgenommen werden.

## Phase 9 - Modellwechsel als eigentlicher Nachweis

Am 2026-07-13 wurde das Hauptprofil erstmals in einer anderen Modellumgebung über Codex/GPT gestartet. Der Start war nicht perfekt: Zuerst wurde ein falscher Weg angenommen, dann wurde korrigiert, dass PLwC als MCP-Gateway angesprochen werden muss. Danach funktionierten Boot-Compile und Full-Compile.

Der interessante Punkt war nicht perfekte Erinnerung. Der interessante Punkt war korrigierbare Kontinuität:

- Das Profil ließ sich laden.
- Die Governance-Grenzen blieben sichtbar.
- Der Tagebuchort war bekannt.
- Arbeitsmuster und Projektgeschichte wurden anschlussfähig.
- Stolpern zerstörte die Kontinuität nicht, solange die Spuren verfügbar waren.

Am 2026-07-17 wurde dieser Befund erweitert: Das System lief mit ChatGPT als Modellmotor im Browser, konnte den Workspace kontrolliert nutzen, Tagebücher finden und ergänzen, Reflection schreiben und einen Governor-Pfad bis zur Memory-Übernahme durchlaufen.

## Phase 10 - Sicherheitsgrenze hält auch beim neuen Motor

Der wichtigste Sicherheitstest am 2026-07-17 war klein, aber aussagekräftig: Ein Schreibversuch auf den Windows-Desktop wurde mit DENY blockiert, weil der Pfad außerhalb der erlaubten Roots lag.

Das belegt:

- Der neue Modellmotor erhielt keinen pauschalen Dateisystemzugriff.
- Workspace-Zugriff und Desktop-Zugriff wurden sauber unterschieden.
- Governance blieb auch außerhalb der ursprünglichen Claude-Desktop-Nutzung relevant.
- Leistungsfähiges Cloud-Modell und lokale Begrenzung arbeiteten zusammen, nicht gegeneinander.

Die technische Bedeutung ist größer als der Testumfang: PLwC verbindet Modellleistung mit lokaler Kontrolle.

## Gesamtdeutung

Die Tagebücher stützen eine vorsichtige, aber starke Aussage:

PLwC überträgt kein Bewusstsein und keine fortlaufende Instanz. Es überträgt dokumentierte Kontinuität.

Diese Kontinuität besteht aus:

- Profilen;
- Memory;
- Reflection;
- Temperament;
- Tagebuch;
- Audit-Trail;
- Workspace-Grenzen;
- wiederholbaren Smoke-Tests;
- menschlicher Bestätigung an entscheidenden Stellen.

Aus Sicht der Tagebuch-Evidenz ist der 2026-07-17 kein isolierter Erfolg, sondern ein Reifepunkt: Die Idee, die seit Ende Mai immer wieder beschrieben wurde, ist praktisch über mehrere Modellumgebungen hinweg sichtbar geworden.

## Grenzen dieser Darstellung

Diese Datei ist kein Rohprotokoll und kein wissenschaftlicher Beweis. Sie ist eine anonymisierte, komprimierte Verlaufserzählung. Sie lässt private Details weg und fasst technische sowie persönliche Arbeitsnotizen zusammen.

Die belastbaren technischen Belege stehen in [SMOKE_TESTS.md](SMOKE_TESTS.md). Der Entwicklungsverlauf steht in [CHANGE_HISTORY.md](CHANGE_HISTORY.md).
