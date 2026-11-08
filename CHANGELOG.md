# Changelog

## 2.0.0 — 2026-11-08

- Kanban-Board mit Aufgaben, Fächern, Prioritäten, Status und Fälligkeiten
- Zeitbudget pro Aufgabe und mehrteilige Zeiterfassung
- Soll-/Ist-Statistik, aggregierte Abweichung und kumulierter Verlauf
- Echte Lernpausen (Start/Ende/Dauer), getrennt von Unterbrechungen
- Mehrere lokale Benutzerkonten mit Passwort-Hashing und eigenständigen Profilen
- JSON-Agentenimport, automatische Polybox-Inbox, Duplikaterkennung
- CSV-Export für Aufgaben und Sessions inklusive Pausenzeiten
- JSON-Backups je Profil, tägliche Sicherungen, V1-Migrationspfad
- Überarbeitetes responsives Webdesign, Entwicklerdokumentation und Tests

## Hinweise zum Upgrade

StudyTracker v1 hat `data/state.json` verwendet. Beim Einrichten des **ersten Kontos** kann v2 diese Datei übernehmen, wenn sie sich im Datenordner befindet. Die Originaldatei bleibt zusätzlich als `legacy-state-v1.json` erhalten. Bitte vorher ein manuelles Backup erstellen.
