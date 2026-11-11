# Speicher- und Performance-Prüfung (StudyTracker 4.3)

StudyTracker verwendet lokale JSON-Profile, keine separate Datenbank und keine zusätzlichen Python-Pakete. Für persönliches Lerntracking geeignet, nicht für gleichzeitige Schreiber auf mehreren Rechnern.

## Optimierungen

- Bisher wurde alle fünf Sekunden das komplette Profil als JSON an den Browser übertragen. Nun wird eine circa 35 Byte große Änderungskennung (`GET /api/profile/revision`) abgefragt und das Profil nur bei Änderungen geladen.
- Aufgaben, Unteraufgaben, Fächer, Tags und Zeitwerte werden beim Rendern in Maps indexiert.
- Versteckte Historie-/Kanban-/Auswertungsansichten sowie ein geschlossenes Archiv erzeugen nicht unnötig viele DOM-Elemente. Die Heatmap wird im Leerlauf nicht sekündlich neu berechnet.
- Pro Aufgabe nur fünf optionale GPT-Felder; keine Speicherung des gesamten Chatverlaufs.

## Synthetische Messungen

Ermittelt in der Testumgebung, **nicht auf deinem ThinkPad**. Python-Spitzen-RSS enthält den Interpreter-Grundverbrauch; Browser-RAM wurde nicht gemessen.

| Aufgaben / Sessions | JSON-Datei | Profil-Antwort | Python-RSS Spitze | Bisheriger Leerlauf-Traffic/h | Neu/h |
|---|---:|---:|---:|---:|---:|
| 100 / 250 | 0,20 MiB | 0,15 MiB | 95 MiB | 104 MiB | ca. 0,024 MiB |
| 1.000 / 5.000 | 3,34 MiB | 2,47 MiB | 109 MiB | 1.775 MiB | ca. 0,024 MiB |
| 5.000 / 20.000 | 13,95 MiB | 10,33 MiB | 154 MiB | 7.437 MiB | ca. 0,024 MiB |

Annahme: ein geöffneter Tab, 720 Abfragen pro Stunde ohne Änderungen. Die Zahlen zum Traffic betreffen übertragene Bytes, nicht RAM- oder Festplattenverbrauch.

## Grenzen

Bei Änderungen wird weiterhin das vollständige Profil geladen und gespeichert. Sehr große Historien erzeugen beim Öffnen viele DOM-Zeilen; Paginierung wäre bei Zehntausenden Einträgen sinnvoll. Polybox erlaubt keinen konfliktfreien gleichzeitigen Schreibzugriff auf dasselbe Profil.

`python3 scripts/memory_audit.py` zeigt lokale Dateigrößen und Summen ohne persönliche Inhalte. Für laufenden Server-RAM auf Ubuntu: `ps -o pid,rss,cmd -p <PID>` (RSS in KiB). Keine neue Telemetrie oder Abhängigkeit.
