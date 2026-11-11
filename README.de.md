# StudyTracker 4.2

**Kostenloser, lokal laufender Lerntracker für Ubuntu/Linux** mit Kanban, eigenständigen Unteraufgaben, Zeitmessung, Pausenprotokoll und Soll-Ist-Analysen. Die Daten können in deinem privaten Polybox-/Nextcloud-Synchronisationsordner liegen. Kein Abonnement, kein Datenbankserver, keine zusätzlichen Python-Pakete.

**Sprachen:** [Deutsch](README.de.md) · [English](README.md)  
**Agent-Anleitungen:** [Deutsch](AGENTS.de.md) · [English](AGENTS.md)

![StudyTracker Übersicht mit heutigen Lernzeiten](docs/screenshots/v4/01-Overview-Today.png)

## Funktionen

| Bereich | Möglichkeiten |
|---|---|
| **Kanban** | Geplant → In Arbeit → Erledigt, Drag & Drop, Fächer, Tags, Prioritäten, Fälligkeiten |
| **Unteraufgaben** | B/C/D als eigenständige, sichtbare Kanban-Karten mit Verknüpfung zur Hauptaufgabe |
| **Status-Verknüpfung** | Sind alle Unteraufgaben fertig, wird die Hauptaufgabe erledigt. Hauptaufgabe abhaken/öffnen wirkt auf alle Unteraufgaben; nur eine Unteraufgabe wieder öffnen wirkt auf die Hauptaufgabe |
| **Freie Zeitschätzungen** | Für Haupt- und Unteraufgaben optional; fehlende Schätzungen werden nicht als null Minuten behandelt |
| **Heutige Lernzeit** | Auf Übersicht und Heute die erfasste Lernzeit plus laufenden Fokus sehen; pro Fach auf Heute aufgeschlüsselt |
| **Tagesdiagramme** | In der Übersicht für Lernrhythmus und Fachverteilung *Heute* auswählen |
| **Kanban-Archiv** | Erledigte Aufgaben nach 48 Stunden automatisch im aufklappbaren Archiv; Filter für 10/30 Tage, alle Aufgaben, Fach und Text; jederzeit wieder öffnen |
| **Lernkategorien** | Kategorie je Session auswählen: **Vorlesung**, **Videos**, **Übungen** oder eigene Tags; Auswertung nach Zeitraum und Fach, ohne Doppelzählung |
| **Diagramm-Tooltips** | Modernere Hinweise beim Zeigen auf Balken, Kategorien, Legenden und Soll-Ist-Vergleiche |
| **Für heute** | Ganze Aufgaben oder beliebige einzelne Teile für heute markieren; die Tagesansicht zeigt die Auswahl |
| **Semester** | Semester anlegen, Fächer zuordnen, Fächer auch ohne Semester lassen |
| **Fächerfarben & Ziele** | Gut sichtbare Farbkacheln oder freier Farbwähler; Wochenziele vollständig optional |
| **Timer & Pausen** | Fokuszeit, echte Pausen mit Uhrzeiten, Unterbrechen/Fortsetzen, Session speichern |
| **Statistiken** | Lernzeit pro Fach, Wochen-/Monatsansichten, Soll-Ist-Differenz, kumulierter Verlauf |
| **Benutzer** | Administrator legt weitere lokale Benutzer an; getrennte Profile, Timer und Statistiken |
| **Daten** | JSON-Backup/Wiederherstellung, CSV-Export für Lernzeiten und Aufgaben |
| **Agentenimport** | JSON-Aufgaben aus E-Mails über Upload oder automatischen Polybox-Posteingang, Duplikate werden erkannt |
| **Oberfläche** | Deutsch/Englisch, Hell/Dunkel, Browser-Tab-Icon |

### Neu in Version 4

![Kanban mit Aufgabenarchiv](docs/screenshots/v4/03-Kanban-Archive.png)

*Neue Ansichten:* [Übersicht heute](docs/screenshots/v4/01-Overview-Today.png) · [Heute](docs/screenshots/v4/02-Today.png) · [Kanban-Archiv](docs/screenshots/v4/03-Kanban-Archive.png) · [Kategorieauswertung](docs/screenshots/v4/04-Insights-Categories.png) · [Englischer Dark Mode](docs/screenshots/v4/05-Insights-Dark-English.png) · [Schmale Dark-Mode-Ansicht](docs/screenshots/v4/06-Mobile-Dark.png) · [Tooltip](docs/screenshots/v4/07-Tooltip-Dark.png).

**Kategorien:** Beim Timer und beim manuellen Erfassen/Bearbeiten einer Lerneinheit gibt es ein eigenes Feld *Kategorie*. Im JSON wird die Tag-ID als `category_tag_id` gespeichert. Sonstige Tags bleiben erhalten; pro Session wird die Fokuszeit genau **einer** Kategorie zugeordnet. Bei alten Sessions ohne Feld dient der erste Tag als Rückfallwert. Nicht kategorisierte Lernzeit bleibt sichtbar. Neue und bestehende Profile erhalten einmalig die Tags *Vorlesung* und *Videos* neben *Übungen* (anschließend frei bearbeitbar). Ein gewählter Timer-Kategoriewert ersetzt die automatische Standardkategorie aus der Aufgabe.

**Heute und Mitternacht:** Tageswerte und Stundenbalken werden an der lokalen Mitternacht geteilt. Laufende Fokuszeit zählt auch dann, wenn der Timer gestern gestartet wurde. Pausen zählen nicht zur Lernzeit. Bei älteren Einträgen ohne Fokusintervalle ist die Verteilung nach Uhrzeit eine Näherung.

**Archiv:** Die App berechnet die Archivansicht allein anhand von `status=done` und einem `completed_at`, das mindestens 48 Stunden zurückliegt. Keine Aufgaben werden gelöscht oder aus dem JSON verschoben. Die Verknüpfung von Haupt- und Unteraufgaben bleibt erhalten. Durch Wiederöffnen kehrt eine Aufgabe ins Board zurück. Die Filter beziehen sich auf das Abschlussdatum.


### Lernzeit nach Uhrzeit

![Lernzeit-Heatmap auf Deutsch](docs/screenshots/v4/08-Heatmap-DE.png)

Unter **Auswertungen → Deine Lernzeiten nach Uhrzeit** wählst du **letzte 24 Stunden**, **letzte 48 Stunden**, **typische Woche (Durchschnitt pro aktiver Woche)** oder **Wochenmuster (Gesamt über alle erfassten Wochen)**. Mit dem Fachfilter darüber kannst du beispielsweise NumCSE betrachten. Eine Vorlesung am Freitag von 08:00 bis 10:00 wird in den Freitagsfeldern angezeigt. Vier insgesamt geleistete Stunden zwischen 01:00 und 02:00 werden in der Gesamtansicht addiert. Hover oder Tastaturfokus zeigen die Dauer an. Der Wochendurchschnitt wird durch die Anzahl der Kalenderwochen **mit erfasster Lernzeit** geteilt; die Ansichten für 24/48 Stunden verwenden ein gleitendes Zeitfenster mit ggf. angefangener erster/letzter Stunde. Zeitzone ist die lokale Browser-Zeitzone. Pausen zählen nicht.

Neue Timer-Sessions speichern `focus_intervals` (ISO-8601-Zeitpaare in UTC), damit auch Unterbrechungen und die Grenze um Mitternacht korrekt abgebildet werden. Alte Profile bleiben gültig. Bei älteren Sessions ohne Fokusintervalle ist die stundenweise Zuordnung eine Schätzung anhand von Beginn, Ende, Fokusdauer und dokumentierten Pausen; die Oberfläche weist darauf hin. JSON-Backups enthalten die genauen Fokusintervalle, CSV enthält weiterhin die Gesamtfokuszeit.

### Screenshots

[Dashboard](docs/screenshots/01-Dashboard.png) · [Kanban mit Unteraufgaben](docs/screenshots/02-Kanban.png) · [Unteraufgabe bearbeiten](docs/screenshots/03-Subtask.png) · [Heute](docs/screenshots/04-Today.png) · [Auswertungen](docs/screenshots/05-Insights.png) · [Semester](docs/screenshots/06-Semesters.png) · [Farbauswahl](docs/screenshots/07-Colors.png) · [Einstellungen](docs/screenshots/08-Settings.png) · [Englisch](docs/screenshots/09-Settings-English.png) · [Dark Mode](docs/screenshots/10-Kanban-Dark.png) · [Timer](docs/screenshots/11-Timer-Dark.png) · [Schmales Display](docs/screenshots/12-Mobile.png)
 · [Laufende Pause](docs/screenshots/13-Break-Dark.png) · [Lernhistorie](docs/screenshots/14-History-Dark.png)

> Die Screenshots wurden mit Beispieldaten und einer **simulierten Browser-API** erstellt. Die reale Python-Schnittstelle wurde gesondert getestet; ein vollständiger Browser-zu-Localhost-Test war in der Testumgebung blockiert.

## Installation unter Ubuntu

Voraussetzung: Python **3.10+** und ein moderner Browser. Es wird **kein** `pip install` benötigt.

```bash
cd ~/Nextcloud/study_tracker  # oder dein Projektordner
chmod +x start.sh
./start.sh
```

Die App erreichst du unter **http://127.0.0.1:8765**. Beim ersten Start richtest du ein Administratorkonto mit mindestens zehn Zeichen Passwort ein. Danach kannst du Fächer, Semester, Aufgaben und Unteraufgaben erstellen.

```bash
./start.sh --port 8766       # anderer Port
./start.sh --no-browser      # Browser nicht automatisch öffnen
```

**Update von StudyTracker 2.x:** Sichere zuerst den gesamten Ordner `data/`. Ersetze nur die Programmdateien, nicht deine bestehenden `data/accounts.json` und `data/profiles/`. Die neuen Felder sind rückwärtskompatibel; JSON-Backups verwenden weiterhin `version: 2`.

## Unteraufgaben sinnvoll nutzen

Beispiel: Hauptaufgabe **Aufgabe 1**, Teilaufgaben **B**, **C**, **D**.

1. Hauptaufgabe im Kanban erstellen.
2. Auf **+ Teil** auf ihrer Karte klicken oder beim Anlegen einer Aufgabe die **Hauptaufgabe** auswählen.
3. B/C/D erscheinen **direkt als eigene Kanban-Karten**, nicht versteckt in einem Dialog.
4. Du kannst beispielsweise nur B und C **für heute markieren**, einzeln mit dem Timer bearbeiten oder abhaken. Markierst du stattdessen Aufgabe 1 für heute, erscheinen auch ihre Teilaufgaben in der Tagesansicht.
5. Für jede Aufgabe ist die Zeitschätzung **optional**; auch das Erfassen von Lernzeit ist je Aufgabe separat möglich.
6. Sobald B, C und D erledigt sind, wird automatisch Aufgabe 1 abgeschlossen. Wenn du Aufgabe 1 abhaken willst, werden alle Teilaufgaben abgeschlossen. Wird die Hauptaufgabe wieder geöffnet, werden alle Teilaufgaben auf **Geplant** gesetzt; öffnest du nur C wieder, bleiben B und D erledigt.

Der Einfachheit halber gibt es **eine Unteraufgabenebene**. Haupt- und Unteraufgaben müssen zum gleichen Fach gehören. Wenn du eine Hauptaufgabe löschst, bleiben die Unteraufgaben als eigenständige Aufgaben erhalten.

### Statistiken ohne Doppelzählung

In der Gesamt-Soll-Ist-Auswertung wird jede **Hauptaufgabe/eigenständige Aufgabe nur einmal** gezählt. Die Ist-Zeit einer Hauptaufgabe umfasst ihre eigenen Sessions **und** die der Teilaufgaben. Die Schätzung der Hauptaufgabe dient als Gesamtbudget. Ist sie leer, werden die Schätzungen aller Unteraufgaben addiert, aber nur, wenn **alle** geschätzt wurden. Unbekannte Schätzungen werden aus dem Gesamtvergleich ausgeschlossen. Details der einzelnen Unteraufgaben bleiben in der Tabelle sichtbar. Im CSV stehen direkte Werte und aufsummierte Gesamtwerte getrennt.

Pausen zählen **nicht** als Lernzeit.

## Datenspeicherung und Polybox

Die App speichert ihre Daten standardmäßig unter `data/`:

```text
study_tracker/
├── server.py
├── start.sh
├── static/
├── AGENTS.md                 # Agentenanleitung Englisch
├── AGENTS.de.md              # Agentenanleitung Deutsch
└── data/                     # beim Start erstellt, von Git ignoriert
    ├── accounts.json        # Benutzer und gesalzene Passwort-Hashes
    ├── profiles/<id>.json   # Aufgaben, Semester, Sessions, Pausen pro Person
    └── inbox/<name>/        # Importordner für Agenten
        ├── processed/
        └── rejected/
```

Wenn der Ordner in einem **privaten** Polybox-/Nextcloud-Verzeichnis liegt, synchronisiert dein Client die Dateien. Polybox stellt aber **keinen Webserver** bereit. StudyTracker ist ausschließlich an `127.0.0.1` erreichbar. Verwende denselben Datenbestand **nicht gleichzeitig auf mehreren Computern**; konkurrierende Synchronisationsänderungen können Daten überschreiben. Mehrere Benutzer **innerhalb einer laufenden App** werden unterstützt.

Datenspeicher separat setzen:

```bash
STUDYTRACKER_DATA_DIR="$HOME/Nextcloud/private-study-data" ./start.sh
```

Zusätzliche tägliche Sicherungen liegen standardmäßig unter `~/.local/share/studytracker/backups/` (maximal 30 pro Benutzer). Bei Bedarf lässt sich das mit `STUDYTRACKER_BACKUP_DIR` ändern. Die Profil-JSON-Dateien sind **nicht verschlüsselt**; nur die Passwörter werden als gesalzene PBKDF2-Hashes gespeichert.

### Git-Sicherheit

Die `.gitignore` schützt insbesondere `/data/`, `/exports/`, `/backups/` und typische persönliche Exportdateien. Vor dem Push:

```bash
git check-ignore -v data/accounts.json
git ls-files data/   # keine Ausgabe erwartet
```

Bereits getrackte Dateien werden durch `.gitignore` nicht nachträglich entfernt. Niemals persönliche JSON-Backups oder CSV-Dateien committen.

## Aufgaben aus E-Mails automatisch importieren

Anleitungen: **[AGENTS.de.md](AGENTS.de.md)** ([English](AGENTS.md)), [Importanleitung](docs/IMPORT.de.md) ([English](docs/IMPORT.md)) und [Agent-Prompt](prompts/email-to-tasks.de.md) ([English](prompts/email-to-tasks.md)). Das maschinenlesbare Format steht in [`schemas/tasks-import.schema.json`](schemas/tasks-import.schema.json), ein Beispiel in [`examples/email-task-import.json`](examples/email-task-import.json).

```json
{
  "format": "studytracker.tasks.v1",
  "batch_id": "mail-analysis-2026-11-08",
  "tasks": [
    {"external_id":"mail-x:1","subject":"Mathematik","semester":"Herbstsemester 2026","title":"Übungsblatt 1","planned_minutes":120},
    {"external_id":"mail-x:1:B","parent_external_id":"mail-x:1","subject":"Mathematik","semester":"Herbstsemester 2026","title":"Teil B","planned_minutes":null},
    {"external_id":"mail-x:1:C","parent_external_id":"mail-x:1","subject":"Mathematik","semester":"Herbstsemester 2026","title":"Teil C","planned_minutes":35}
  ]
}
```

Die Verknüpfung funktioniert unabhängig von der Reihenfolge in der Datei. `batch_id` und `external_id` müssen bei wiederholten Importen gleich bleiben. **Die JSON-Schlüssel sind in beiden Sprachen identisch.**

Die fertige Datei kannst du in `data/inbox/<benutzername>/` ablegen oder über **Einstellungen → Import** hochladen. Die laufende App verarbeitet sie und verschiebt sie nach `processed/` bzw. `rejected/`. **E-Mails selbst werden nicht automatisch gelesen**; dafür brauchst du einen separat autorisierten Agenten/Connector.

## Tests

```bash
python3 -m unittest discover -s tests -v
node --check static/app.js
node --check static/i18n.js
```

**21 erfolgreiche Tests** für Kontentrennung, CSV/JSON, Pausen, sichere Importe, Status-Verknüpfung von Unteraufgaben, Löschen und Backup. Die Oberfläche wurde zusätzlich im Chromium-Browser mit simulierten Daten geprüft.

## Weitere Dokumente

- [API Deutsch](docs/API.de.md) · [API English](docs/API.md)
- [Import Deutsch](docs/IMPORT.de.md) · [Import English](docs/IMPORT.md)
- [Changelog Deutsch](CHANGELOG.de.md) · [Changelog English](CHANGELOG.md)
- [MIT-Lizenz](LICENSE)

## Optionale Exercise-Bewertung (StudyTracker 4.2)

Über **Bewerten** auf einer Kanban-Karte (auch im Archiv) kann jede Aufgabe höchstens **eine Bewertung** erhalten: Schwierigkeit (1–5), Lösungserfolg (richtig/teilweise/falsch), acht mögliche Hauptprobleme, Gesamthilfe (0–5) und ChatGPT-Hilfe (0–5). Alle Angaben sind freiwillig, auch die gesamte Bewertung kann leer bleiben. `0` bedeutet ausdrücklich keine Hilfe, ein leeres Feld **nicht bewertet**. Dies ist **kein** Versuchstagebuch oder Prüfungsmodus.

Im Dialog gibt es einen kopierbaren ChatGPT-Prompt und ein Feld zum Einfügen einer JSON-Antwort. Vorschläge werden erst nach deiner Überprüfung und Bestätigung gespeichert. JSON-Backup und Aufgaben-CSV enthalten die Bewertung. Siehe [Bewertungsformat](docs/EXERCISE_REVIEW.de.md) und [deutscher Prompt](prompts/exercise-review.de.md).


### ChatGPT-Bewertung speichern (Korrektur 4.2.1)

Wenn du eine JSON-Antwort im Bewertungsdialog einfügst, übernimmt **Bewertung speichern** noch nicht angewendete Rückmeldungen direkt. Die Schaltfläche **ChatGPT-Antwort übernehmen** bleibt optional. Fehlende oder `null`-Werte überschreiben keine gespeicherten oder manuell gewählten Angaben; manuelle Werte haben Vorrang. Ungültiges JSON zeigt einen Fehler und verhindert das Speichern. Gespeicherte Bewertungen sind auch auf Aufgabenkarten, in Heute und im Archiv sichtbar.
