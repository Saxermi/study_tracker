# Aufgabenimport aus ChatGPT, E-Mails oder anderen Agenten

## Schnellstart (ohne Mail-Integration)

1. Leite eine E-Mail an ChatGPT weiter oder kopiere ihren Text und nutze [`prompts/email-to-tasks.md`](../prompts/email-to-tasks.md).
2. Bitte um eine **JSON-Datei** gemäß [`AGENTS.md`](../AGENTS.md). Ein Beispiel ist [`examples/email-task-import.json`](../examples/email-task-import.json).
3. Importiere die Datei unter **Einstellungen → Import → Aufgaben-JSON importieren**. Alternativ kopiere sie nach `data/inbox/<benutzername>/`.
4. Nach einigen Sekunden erscheinen neue Karten unter **Kanban → Geplant**. Neue Fächer oder Tags werden bei Bedarf automatisch angelegt.

Die App prüft den Inbox-Ordner alle vier Sekunden. Eine Datei muss mindestens drei Sekunden lang unverändert sein, damit ein halbfertiger Polybox-Sync nicht als Importfehler gilt.

## Minimaler Beispieldatensatz

```json
{
  "format": "studytracker.tasks.v1",
  "batch_id": "mail-kurs-2026-11-08-uebungen",
  "tasks": [
    {"external_id": "kurs-2026-11-08:1", "subject": "Mathematik", "title": "Blatt 6 lösen", "planned_minutes": 75, "priority": "normal", "due_date": null, "tags": ["Übungsblatt"]}
  ]
}
```

Das ist das verbindliche Austauschformat. `external_id` wird innerhalb eines Benutzerprofils zum dauerhaften Duplikatabgleich verwendet, und `batch_id` wird für vollständige Importdateien geprüft. Ein zweiter Import derselben Datei erzeugt **keine doppelten Aufgaben**.

## Ein einziges Terminalkommando

```bash
python3 scripts/add_tasks.py --user alex --file ~/Downloads/aufgaben.json
```

Dieser Helfer schreibt zuerst einen temporären Dateinamen und benennt ihn atomar in `.json` um. Er startet die App nicht selbst. Die App muss für den automatischen Import laufen. Alternativ `python3 server.py --import-once`, wenn keine andere StudyTracker-Instanz dieselben Daten bearbeitet.

## Was ist wirklich automatisiert?

- Das **Einlesen** einer bereits vorhandenen Importdatei ist automatisch, solange StudyTracker läuft.
- Das **Extrahieren aus einer Mail** erfordert einen Agenten mit Zugriff auf die Mail (oder manuelles Einfügen in ChatGPT).
- Das **Ablegen auf Polybox** erfordert Schreibzugriff auf den synchronisierten lokalen Ordner. Das ist ohne separate Integration nicht automatisch aus einem ChatGPT-Chat heraus möglich.
- Keine SMTP-, IMAP- oder Gmail-Zugangsdaten müssen im StudyTracker gespeichert werden.

Ein externer Workflow (z. B. E-Mail-Connector + genehmigte Automatisierung auf deinem eigenen Rechner) kann die JSON-Datei automatisch nach `data/inbox/<user>/` schreiben. Dieser Workflow ist **nicht** Teil der App, denn Mailzugang erfordert eine separate ausdrückliche Einrichtung.

## Fehlerdiagnose

Fehlerhafte oder nicht valide JSON-Dateien landen in `data/inbox/<user>/rejected/` mit derselben Basis und einer `.error.txt`. Erfolgreiche Dateien wandern nach `processed/`. Ungültige Aufgaben in einer Datei sorgen dafür, dass **die ganze Importdatei zurückgewiesen wird**, sodass kein Teilzustand entsteht.

Begrenzungen: 1 MB pro Inbox-JSON, maximal 150 Aufgaben pro Datei. IDs und Texte werden validiert, HTML im Browser entschärft, **nichts wird aus dem importierten Text ausgeführt**.
