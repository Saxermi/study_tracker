# StudyTracker v2 — lokale HTTP-Schnittstelle

Der Server bindet an `127.0.0.1:8765` (Port anpassbar). Keine öffentliche Schnittstelle; kein Remotezugriff via Polybox. Alle Schreiboperationen brauchen `Content-Type: application/json`, einen gültigen Browser-Session-Cookie und dürfen keinen fremden Origin-Header haben.

| Methode | Pfad | Funktion |
|---|---|---|
| GET | `/api/auth/status` | Erststartstatus, angemeldeter Benutzer |
| POST | `/api/auth/setup` | Ersten Admin erstellen; `username`, `display_name`, `password` |
| POST | `/api/auth/login` | Passwortlogin; setzt `HttpOnly`/`SameSite=Strict` Session-Cookie |
| POST | `/api/auth/logout` | Sitzung abmelden |
| GET | `/api/users` | Benutzerliste, Admin |
| POST | `/api/users` | Benutzer anlegen, Admin |
| GET | `/api/state` | Vollständiges Datenprofil des eingeloggten Benutzers |
| POST | `/api/subjects` | Fach hinzufügen |
| PATCH | `/api/subjects/{id}` | Fach ändern, archivieren, Ziel ändern |
| POST | `/api/tags` | Tag hinzufügen |
| DELETE | `/api/tags/{id}` | Tag und Referenzen entfernen |
| PATCH | `/api/settings` | `weekly_goal_minutes` |
| POST | `/api/tasks` | Kanban-Aufgabe hinzufügen |
| PATCH | `/api/tasks/{id}` | Titel, Status, Fälligkeit, Priorität, Schätzung etc. ändern |
| DELETE | `/api/tasks/{id}` | Aufgabe löschen und Sessions-Aufgabenlinks lösen |
| POST | `/api/timer/start` | Timer starten mit `task_id` oder `subject_id`/`title` |
| POST | `/api/timer/break-start` | Fokus → Pause |
| POST | `/api/timer/break-end` | Pause → Fokus |
| POST | `/api/timer/pause` | Fokus → Unterbrochen (ohne gemessene Pause) |
| POST | `/api/timer/resume` | Unterbrochen → Fokus |
| POST | `/api/timer/stop` | Fokus/Pausen als Session abschließen |
| POST | `/api/timer/discard` | Timer verwerfen |
| POST | `/api/sessions` | Manuelle Fokus-Session hinzufügen |
| PATCH | `/api/sessions/{id}` | Session bearbeiten (bestehende Pausen bleiben) |
| DELETE | `/api/sessions/{id}` | Session löschen |
| GET | `/api/export?format=json` | Profilbackup ohne laufenden Timer und ohne Passwörter |
| GET | `/api/export?format=csv&kind=sessions` | Lernzeiten-CSV |
| GET | `/api/export?format=csv&kind=tasks` | Kanban/Schätzung/Ist-CSV |
| POST | `/api/import/tasks` | Idempotenter Agenten-JSON-Import, nur neue Tasks |
| POST | `/api/import/backup` | Vollständiges, validiertes Profilbackup ersetzen |

**Taskdaten**: `title`, `description`, `subject_id`, `planned_minutes`, `status` (`todo`/`doing`/`done`), `priority` (`low`/`normal`/`high`), `due_date` (`YYYY-MM-DD` oder `null`), `tags` (Tag-IDs). `actual_minutes` ist **berechnet aus `sessions`**, kein frei beschreibbares Feld.

**Sessiondaten**: `subject_id`, optional `task_id`, `title`, `started_at` (ISO-8601 mit Offset), `duration_seconds`, `tags` (IDs), `notes`. Timer-Sessions haben zusätzlich `break_seconds` und `breaks` mit Uhrzeiten und Dauern.

**Agentenpayload**: Siehe [`AGENTS.md`](../AGENTS.md) und [`schemas/tasks-import.schema.json`](../schemas/tasks-import.schema.json). Der Agentenimport akzeptiert **Fach- und Tag-Namen**, erzeugt Unbekannte automatisch und weist allen neuen Aufgaben den Status `todo` zu. Im normalen Task-CRUD werden stattdessen vorhandene `subject_id` und `tag`-IDs verwendet.

**Sicherheitsgrenze:** Accounts sind für vertrauenswürdige Personen an einem privaten Ubuntu-Gerät gedacht. Der lokale Dienst hat keine verschlüsselte Netzwerkverbindung, keine externe Multi-Device-Authentifizierung und ist nicht als öffentlich zugänglicher Webdienst gehärtet. Keine Weiterleitung des lokalen Ports ins Internet einrichten.
