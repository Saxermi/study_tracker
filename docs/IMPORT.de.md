# Aufgabenimport aus E-Mails, KI-Agenten und Polybox (Deutsch)

**English:** [IMPORT.md](IMPORT.md) · [Agentenanleitung Deutsch](../AGENTS.de.md) · [English](../AGENTS.md)

## Schnellstart

1. E-Mail oder Übungsblatt mit [diesem Prompt](../prompts/email-to-tasks.de.md) an ChatGPT/einen autorisierten Agenten geben.
2. Ein **einziges gültiges Import-JSON** im Format `studytracker.tasks.v1` erzeugen lassen. Beispiel: [`examples/email-task-import.json`](../examples/email-task-import.json).
3. Als Datei speichern und unter **Einstellungen → Import → Aufgaben-JSON importieren** auswählen oder in den privaten synchronisierten Ordner `data/inbox/<benutzername>/` ablegen.
4. StudyTracker laufen lassen. Alle etwa vier Sekunden werden stabile `.json`-Dateien geprüft, atomar importiert und nach `processed/` bzw. `rejected/` verschoben.

## Beispiel mit eigenständigen Unteraufgaben

```json
{
  "format": "studytracker.tasks.v1",
  "batch_id": "mail-42-version-1",
  "tasks": [
    {"external_id":"mail-42:1","subject":"Mathematik","semester":"Herbstsemester 2026","title":"Übungsblatt 1","planned_minutes":120},
    {"external_id":"mail-42:1:B","parent_external_id":"mail-42:1","subject":"Mathematik","semester":"Herbstsemester 2026","title":"Teil B","planned_minutes":30},
    {"external_id":"mail-42:1:C","parent_external_id":"mail-42:1","subject":"Mathematik","semester":"Herbstsemester 2026","title":"Teil C","planned_minutes":null}
  ]
}
```

Alle Aufgaben sind im Kanban einzeln sichtbar. Die Verknüpfung wird auch dann richtig aufgelöst, wenn die Hauptaufgabe erst **nach** den Unteraufgaben in der Datei steht. Existieren gleichnamige Fächer in mehreren Semestern, muss der `semester`-Name angegeben werden. Andernfalls wird ein eindeutig vorhandenes Fach verwendet.

`planned_minutes` ist optional/null – keine Schätzung erfinden. Neue Aufgaben starten unter `todo` ohne bereits erfasste Lernzeit. `external_id` bleibt für dieselbe Aufgabe stabil; `batch_id` für denselben Quellstand. Damit werden wiederholte Importe nicht doppelt angelegt.

## Im Terminal

```bash
python3 scripts/add_tasks.py --user alex --file ~/Downloads/aufgaben.json
```

Das Skript schreibt atomar über eine temporäre Datei. Es liest weder E-Mails noch startet es den Server. Für Autoimport muss die App laufen; alternativ `python3 server.py --import-once`, wenn sonst keine Instanz aktiv ist.

## Datenschutz und Grenzen

Polybox synchronisiert Dateien, liest aber keine E-Mails. Ein Agent muss **tatsächlich Zugriff** auf den privaten Inbox-Ordner haben, um dort Dateien automatisch abzulegen. Aus einem normalen ChatGPT-Chat heraus ist das ohne zusätzliche Verbindung nicht möglich. Die App verwendet keine Gmail-/Outlook-/IMAP-Zugangsdaten und benötigt für Mailimport eine separat eingerichtete, autorisierte Verbindung.

Fehlerhafte JSON-Dateien landen in `rejected/` mit einer `.error.txt`, erfolgreiche in `processed/`. Der Import schreibt erst nach Validierung **der ganzen Datei**. Pro Datei: höchstens 1 MB, 1–150 Aufgaben. JSON wird nur als Daten gelesen, nicht als Code ausgeführt. Vorhandene Aufgaben werden nicht still überschrieben.

### v4: Aufgaben für spätere Kategorieauswertungen markieren

Passende Aufgaben können `"tags": ["Vorlesung"]`, `"tags": ["Videos"]` oder `"tags": ["Übungen"]` erhalten. Das sind nur **Aufgaben-Tags**, keine erfassten Lernzeiten. Die Kategorie wird beim Erfassen einer Lernsession bestimmt. `category_tag_id` gehört nicht ins Agenten-Aufgabenformat; das Importschema bleibt unverändert.

## Gezielter Import per Fach-ID (v4.4)

1. In Einstellungen → Import-Assistent ein vorhandenes Fach wählen (und gegebenenfalls die Hauptaufgabe).
2. Quellentyp auswählen, generierte Markdown-Anleitung kopieren oder speichern.
3. Quellmaterial nach der Anleitung an ChatGPT/den Agenten geben.
4. Das vom Agenten ausgegebene `studytracker.tasks.v1`-JSON importieren.

`subject_id` ist die exakte ID des Fachs im aktuellen Profil. Optionaler `parent_id` ist die ID einer **bestehenden** Hauptaufgabe im selben Fach. Ein unpassender oder fremder Wert führt zum Abbruch der ganzen Importdatei. Bei neuen Hauptaufgaben/Teilaufgaben wird stattdessen `parent_external_id` verwendet. Beispiel: [`examples/targeted-task-import.json`](../examples/targeted-task-import.json). Die detaillierten Quellentemplates liegen unter [`prompts/import/`](../prompts/import/).
