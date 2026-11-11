# Changelog (Deutsch)

## 4.1 — Lernzeit-Heatmap (24h / 48h / typische Woche)

- Neue Heatmap mit 24-/48-Stunden-Ansicht und typischer Woche (Durchschnitt oder Summe), Fachfilter und zugänglichen Tooltips.
- Genaue Fokusintervalle werden bei Pausen und Wiederaufnahme gespeichert und über JSON gesichert.
- Tageswerte berücksichtigen Sessions über Mitternacht; ältere Sessions werden bei fehlenden Fokusintervallen als Schätzung angezeigt.
- Neue JavaScript-Tests sowie Node-Tests in GitHub Actions.

## 4.0 — Tageszeit, Aufgabenarchiv und Kategorieauswertungen

- Laufende und gespeicherte Lernzeit von heute auf Übersicht und Heute, Fächerverteilung auf Heute.
- „Heute“-Option für Stundenverlauf und Fachdiagramm sowie in den Auswertungen.
- Kanban-Archiv nach 48 Stunden mit 10-/30-Tage-/Gesamt-, Fach- und Textfilter.
- `category_tag_id` für Timer und Sessions, Tags Vorlesung/Videos; Kategorieauswertung ohne Doppelzählung.
- Schönere Diagramm-Tooltips und verbesserte KPI-Anordnung.
- Abwärtskompatible JSON-Profile, zusätzliche CSV-Kategoriespalte, zweisprachige Agent-/API-Dokumentation und Tests.

## 3.0 — Unteraufgaben, Sprachen und Themes

- Unteraufgaben als eigene Kanban-Karten, verknüpft über `parent_id`.
- Gegenseitig verknüpfte Erledigt-Stati, Timer und Heute-Auswahl je Aufgabe.
- Optionale Zeitschätzungen; aufsummierte Hauptaufgaben-Statistiken ohne Doppelzählung.
- Aufgaben-JSON-Import mit stabiler `parent_external_id`, optionalem `semester`, Validierung und Duplikatschutz.
- Semester zur Fächergruppierung und optionale globale und fachspezifische Wochenziele.
- Reparierte Farbauswahl samt CSP-Freigabe für dynamische Farbstile.
- Heute-Ansicht, deutsch/englische Oberfläche, Hell/Dunkel und Browser-Icon.
- Erweiterte CSV-Spalten, kompatible JSON-Profile, zweisprachige Dokumentation und Regressionstests.

## 2.x — Erste Version

- Kanban, Mehrbenutzerprofile, Timer mit Pausen, Statistiken, JSON-/CSV-Exporte und Importordner.

## 4.2 — Optionale Exercise-Bewertung
- Je Aufgabe eine freiwillige Bewertung mit unabhängig optionalen Werten für Schwierigkeit, Ergebnis, acht Fehlerarten sowie Gesamt- und ChatGPT-Hilfe.
- Kopierbarer ChatGPT-Prompt (DE/EN) und manuelle Übernahme von JSON-Vorschlägen.
- Bewertungen im Task-CSV und JSON-Backup; alte Aufgaben bleiben kompatibel. Kein Prüfungsmodus und keine Versuchshistorie.


## 4.2.1 — Exercise-Bewertungen und ChatGPT-JSON speichern

- Eingefügtes ChatGPT-JSON wird auch direkt mit **Bewertung speichern** übernommen.
- Manuelle Bewertungen haben Vorrang; unbekannte (`null`) Vorschläge löschen keine vorhandenen Werte. Bei ungültigem JSON wird nicht gespeichert.
- Gespeicherte Schwierigkeit, Ergebnis und Hilfe werden in Kanban, Heute und im Archiv angezeigt.
- Neue JavaScript-Regressionsprüfungen in GitHub Actions.

## 4.3 — Eigene Bewertung vs. GPT und weniger Leerlauf-Daten

- Eigene Übungsbewertungen und GPT-Feedback werden getrennt gespeichert, verglichen und als JSON/CSV exportiert.
- Der Dialog zeigt ein klares JSON-Beispiel statt eines irreführenden Platzhalters. Einzelne Werte werden nur bewusst übernommen.
- Speichern verarbeitet eingefügtes JSON direkt; neue Prüfungen gegen ungültige Daten.
- Kleine Änderungskennung statt vollständiger Profilabfrage alle fünf Sekunden; indexierte Lookups und verzögertes Rendern unsichtbarer Ansichten. Performance-Dokumentation ergänzt.
