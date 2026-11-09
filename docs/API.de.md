# Lokale StudyTracker-API (Deutsch)

**English:** [API.md](API.md). Lokale HTTP-API an `127.0.0.1`, Anmeldung über SameSite- und HttpOnly-Session-Cookie. Nicht öffentlich ins Internet stellen.

## Anmeldung

- `GET /api/auth/status` — aktueller Benutzer und erster Einrichtungsstatus.
- `POST /api/auth/setup` — erstes Administratorkonto (`display_name`, `username`, `password`, mindestens 10 Zeichen).
- `POST /api/auth/login` / `/api/auth/logout` — an-/abmelden.
- `GET /api/users` / `POST /api/users` — Benutzerverwaltung für Administratoren.

## Lerndaten (mit Anmeldung)

- `GET /api/state` — Profil mit Fächern, Semestern, Tags, Aufgaben, Lernzeiten, Timer und Einstellungen.
- `POST /api/semesters`, `PATCH/DELETE /api/semesters/<id>`.
- `POST /api/subjects`, `PATCH /api/subjects/<id>` — Name, Farbe (`#RRGGBB`), optional `semester_id`, optional `weekly_goal_minutes` (`null` = ohne Ziel).
- `POST /api/tags`, `DELETE /api/tags/<id>`.
- `POST /api/tasks`, `PATCH/DELETE /api/tasks/<id>` — Titel, Fach, optional `parent_id`, optional `planned_minutes`, Status (`todo|doing|done`), Priorität (`low|normal|high`), Tags, Frist und `planned_for` (`YYYY-MM-DD`/null).
- `POST /api/sessions`, `PATCH/DELETE /api/sessions/<id>` — Lerneinheiten, optional mit `task_id`.
- Timer: `POST /api/timer/start`, `/pause`, `/resume`, `/break-start`, `/break-end`, `/stop`, `/discard`.
- `PATCH /api/settings` — optionales Wochenziel (mit `weekly_goal_minutes: null` entfernen).

### Unteraufgaben

`parent_id` referenziert die **interne** ID einer anderen Aufgabe. Nur eine Unteraufgabenebene, gleiches Fach, keine Zyklen. Jede Unteraufgabe ist eigenständig. Sind alle Teilaufgaben erledigt, wird die Hauptaufgabe automatisch erledigt. Hauptaufgabe explizit erledigen/wieder öffnen wirkt auf alle Teilaufgaben; eine einzelne Teilaufgabe wieder öffnen wirkt auf die Hauptaufgabe und lässt die anderen erledigten Teile bestehen. Beim Löschen einer Hauptaufgabe bleiben die Unteraufgaben erhalten. Schätzungen sind `null` oder positive ganze Minuten.

## Import und Export

- `POST /api/import/tasks` — JSON-Umschlag `studytracker.tasks.v1` mit `external_id` und optional `parent_external_id`. Schema: [`schemas/tasks-import.schema.json`](../schemas/tasks-import.schema.json); Verknüpfung unabhängig von der Reihenfolge.
- `POST /api/import/backup` — **vollständiges Benutzer-Backup** mit Bestätigung wiederherstellen; ersetzt das aktuelle Profil.
- `GET /api/export?format=json` — vollständiges JSON-Backup; aus Kompatibilitätsgründen weiterhin `version: 2`, ohne laufenden Timer.
- `GET /api/export?format=csv&kind=tasks|sessions` — Semikolon-getrennte CSVs mit UTF-8-BOM für LibreOffice. Aufgaben-CSV enthält Hauptaufgaben-ID, direkte Zeiten und aufsummierte Zeiten; Session-CSV enthält Fokus und Pausen.

**Das Agenten-JSON ist sprachunabhängig.** Schlüssel und Enumwerte bleiben auf Deutsch und Englisch gleich. Der Agent verwendet `semester` als Namen, die interne API `semester_id`.

## v4: Session-Kategorien und Archiv

`POST /api/timer/start` akzeptiert optional `category_tag_id` (`null` oder ID eines bestehenden Tags). Es überschreibt die erste Kategorie aus der Aufgabe. Beim Stoppen wird dieser Wert in der Session gespeichert. `POST/PATCH /api/sessions` unterstützt das gleiche Feld. `GET /api/state` und JSON-Exporte enthalten das Feld in Sessions; der CSV-Export `kind=sessions` erhält die zusätzliche Spalte `Kategorie`. Es gibt keinen neuen Archiv-Endpunkt: Die Oberfläche archiviert erledigte Aufgaben nach mindestens 48 Stunden seit `completed_at`; Wiederöffnen funktioniert über den vorhandenen Task-Endpunkt. Das Agentenimportformat bleibt unverändert.

## Focus interval extension / Fokusintervalle (4.1)

Timer-created sessions include an optional `focus_intervals` array of `{ "started_at": "...", "ended_at": "..." }` ISO-8601 pairs. These are recorded whenever focus changes to paused/break/stopped. Legacy sessions without intervals remain supported. Time-of-day statistics use these spans and exclude breaks; a legacy estimate is indicated when the precise timing is unavailable. JSON backup/restore preserves validated focus intervals.
