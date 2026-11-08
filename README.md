# StudyTracker 2.0 — Lernzeit, Kanban, Pausen & Agentenimporte

**Ein kostenloses, lokal laufendes Lernstudio für Ubuntu/Linux**, mit mehreren Benutzerkonten und vollständiger Datenkontrolle. Funktioniert mit deinem bestehenden **Polybox-Synchronisationsordner** – ohne Hosting, ohne bezahlten Server und ohne zusätzliche Python-Pakete.

![Dashboard](docs/screenshots/Dashboard.png)

## Funktionen

| Bereich | Funktionen |
|---|---|
| **Kanban-Board** | Geplant → In Arbeit → Erledigt, Drag & Drop, Aufgabentitel, Fach, Beschreibung, Fälligkeit, Priorität, Tags |
| **Zeitschätzungen** | Jede Aufgabe hat eine Schätzung in Minuten; beliebig viele Lerneinheiten können derselben Aufgabe zugeordnet werden |
| **Plan vs. Ist** | Aufgabenauswertung mit Minuten- und Prozentabweichung sowie kumuliertem Trend über alle abgeschlossenen, gemessenen Aufgaben |
| **Timer & Pausen** | Fokus starten, echte Pause starten/beenden, unterbrechen/fortsetzen, Session speichern; Pausen werden separat mit Uhrzeiten erfasst |
| **Benutzer** | Erstes Konto ist Administrator; weitere Konten anlegen; Login mit Passwort; getrennte Profildaten, Timer und Aufgaben |
| **Lernhistorie** | Sessions nachtragen, bearbeiten, löschen, einem Fach und optional einer Aufgabe zuweisen |
| **Auswertung** | 7/14/30 Tage, 13 Wochen, 12 Monate, Gesamtzeit, Fächerverteilung, Woche, Ziele, Pausenstatistik |
| **Export** | JSON-Profilbackup, Lernzeiten-CSV und Aufgaben-CSV (UTF-8 mit BOM, Semikolon als Trennzeichen) |
| **Agentenimport** | Aufgaben-JSON aus E-Mails über Datei-Upload oder automatisch aus dem Polybox-Inbox-Ordner; Duplikaterkennung |

### Screenshots mit Beispieldaten

| Oberfläche | Ansicht |
|---|---|
| Dashboard | [Dashboard.png](docs/screenshots/Dashboard.png) |
| Kanban-Board | [Kanban.png](docs/screenshots/Kanban.png) |
| Aufgabe anlegen | [Aufgabe-anlegen.png](docs/screenshots/Aufgabe-anlegen.png) |
| Soll/Ist-Analyse | [Statistik.png](docs/screenshots/Statistik.png) |
| Lernhistorie | [Lernhistorie.png](docs/screenshots/Lernhistorie.png) |
| Einstellungen inkl. Benutzer | [Einstellungen.png](docs/screenshots/Einstellungen.png) |
| Laufender Timer | [Timer.png](docs/screenshots/Timer.png) |
| Laufende Pause | [Pause-laeuft.png](docs/screenshots/Pause-laeuft.png) |
| Uhrzeiten der Pausen | [Pausen-Details.png](docs/screenshots/Pausen-Details.png) |
| Mobile Browser-Breite | [Mobil.png](docs/screenshots/Mobil.png) |
| Erstes Konto | [Anmeldung.png](docs/screenshots/Anmeldung.png) |

## Installation auf Ubuntu

**Voraussetzung:** Python 3.10 oder neuer (`python3 --version`), ein aktueller Browser und ein funktionierender Polybox-Synchronisationsclient. Es ist **kein** `pip install` nötig.

1. ZIP herunterladen, entpacken und den ganzen Projektordner nach Möglichkeit in deinen **lokal synchronisierten Polybox-Ordner** verschieben.
2. Terminal im Projektordner öffnen:

```bash
chmod +x start.sh
./start.sh
```

3. Die lokale Seite `http://127.0.0.1:8765` öffnet sich normalerweise selbst. Alternativ diese Adresse manuell im Browser aufrufen.
4. Beim ersten Start ein Administratorkonto mit **mindestens 10 Zeichen Passwort** anlegen.
5. Fächer erstellen oder die Beispiel-Fächer umbenennen; Aufgaben im Kanban hinzufügen; per Karten-Button `Start` den Timer aktivieren.
6. Unter **Einstellungen → Benutzerkonten** weitere Personen mit eigenen Konten anlegen.

**Port ändern** (wenn 8765 schon belegt ist): `./start.sh --port 8766`. **Ohne Browser öffnen** (z. B. für Inbox-Verarbeitung): `./start.sh --no-browser`.

> Die App hört ausschließlich auf `127.0.0.1`. Sie ist **nicht** aus dem Internet und nicht automatisch von einem anderen Computer erreichbar. Benutzerkonten funktionieren für unterschiedliche Personen am selben Computer bzw. lokalem Server. Polybox ist Dateisynchronisation, **kein** Hosting oder gemeinsam genutztes Datenbanksystem.

### Polybox-Synchronisierung

Am einfachsten bleibt das gesamte Projekt im lokalen Polybox-Ordner. Deine Benutzerdaten liegen in:

```text
StudyTracker-Polybox-v2/
├── server.py                 # Lokaler Webserver / API
├── static/                   # Benutzeroberfläche
├── data/                     # Persönliche Daten, wird nach Start angelegt
│   ├── accounts.json         # Benutzernamen + gesalzene Passwort-Hashes
│   ├── profiles/<id>.json    # Fächer, Aufgaben, Sessions, Pausen pro Person
│   ├── inbox/<name>/         # Automatische Aufgabenimporte
│   │   ├── processed/        # Erfolgreich verarbeitete Dateien
│   │   └── rejected/         # Fehlerhafte Dateien + Hinweise
│   └── legacy-state-v1.json  # Nur bei einer Migration aus Version 1
├── AGENTS.md                 # Agentenanleitung
└── tests/                    # Tests
```

**Wichtig:** Bitte **nicht gleichzeitig auf zwei Rechnern** mit denselben Polybox-Dateien arbeiten. Polybox synchronisiert Dateien, löst aber keine konkurrierenden Datenbankänderungen. Mehrere Benutzer **in einer laufenden App-Instanz** sind dagegen durch getrennte Profile und eine Schreibsperre unterstützt. Bei Gerätewechsel: App schließen, Polybox vollständig synchronisieren lassen, dann auf dem anderen Gerät starten.

Vertrauliche Daten sind in `profiles/*.json` auf der Festplatte/Polybox **nicht verschlüsselt**. Passwörter werden nur gesalzen und mit PBKDF2-HMAC-SHA256 gehasht gespeichert. Verwende dafür ein eigenes, nicht öffentlich geteiltes Polybox-Verzeichnis. Zugangsdaten stehen **nicht** im JSON-Profilbackup.

### Bereits StudyTracker 1.0 verwendet?

Wenn im ursprünglichen Polybox-Projekt eine `data/state.json` der Version 1 liegt, kopiere diese Datei nach `data/state.json` dieses neuen Projektordners, **bevor du den ersten Benutzer anlegst**. Bei der Erstellung des ersten Kontos werden Fächer, Tags, Sessions und das Wochenziel übernommen. Das Original bleibt als `data/legacy-state-v1.json` erhalten. Eine möglicherweise unterbrochene Live-Timer-Session wird **nicht** übernommen. Erstelle vorher zusätzlich ein manuelles Backup deiner alten Version.

## Kanban und Soll-Ist-Statistik

1. Lege eine Aufgabe an, z. B. **„Lineare Algebra: Serie 4“** mit **60 Minuten** Schätzung.
2. Starte den Timer von der Karte; alle folgenden Sessions werden dieser Aufgabe zugeordnet.
3. Verwende `Pause starten`/`Pause beenden`, wenn du eine tatsächliche Lernpause machst. Unterbrechen ist eine getrennte Funktion (keine Pausenmessung).
4. Beende deine Fokuszeit und speichere die Session. Wiederhole das bei Bedarf.
5. Schiebe die Aufgabe nach **Erledigt** (Drag & Drop oder über das Bearbeitungsformular).
6. Unter **Auswertungen** siehst du Schätzung, Ist-Wert, Abweichung pro Aufgabe und aggregiert.

**Beispiel:** 60 min geschätzt, zwei Fokus-Sessions von 20 min und 25 min, plus 10 min Pause → **45 min Ist**, **−15 min** bzw. **25 % schneller als geschätzt**. Die Pause erscheint **nicht** in der Ist-Lernzeit, aber in der Pausenstatistik.

**Aggregation:** In den Plan/Ist-Kennzahlen zählen nur *abgeschlossene Aufgaben mit tatsächlicher Zeitmessung*. Offene Aufgaben und erledigte Aufgaben ohne Messung zählen nicht – sonst würden Aufgaben ohne Lernzeit künstlich als „sehr schnell“ erscheinen. In der Historie bleiben alle Sessions erhalten.

## Automatisierter Aufgabenimport

Die komplette Anleitung für ChatGPT/Codex-Agenten steht in [`AGENTS.md`](AGENTS.md), und einen kopierfertigen Prompt findest du unter [`prompts/email-to-tasks.md`](prompts/email-to-tasks.md). Beispiel: [`examples/email-task-import.json`](examples/email-task-import.json).

1. Agent extrahiert aus einer Mail oder einem PDF Lernaufgaben und erstellt `studytracker.tasks.v1`-JSON.
2. Importieren unter **Einstellungen → Import → Aufgaben-JSON importieren**, oder die Datei in `data/inbox/<benutzername>/` ablegen.
3. Sobald StudyTracker läuft, liest es vollständige JSON-Dateien automatisch ein. Es erzeugt bei Bedarf Fächer und Tags, ordnet alle Karten **Geplant** zu und überspringt Duplikate.

Das Ablegen geht auch per Befehl:

```bash
python3 scripts/add_tasks.py --user alex --file ~/Downloads/aufgaben.json
```

**Nicht Teil der App:** Selbstständiger Zugriff auf Gmail/Outlook oder automatisches Auslesen von Nachrichten ohne vorher von dir eingerichtete Verbindung. Der **Import nach Vorliegen einer JSON-Datei** läuft hingegen ohne weitere Klicks. Details in [`docs/IMPORT.md`](docs/IMPORT.md).

## Backup & Exporte

Unter Einstellungen:

- **Vollständiges JSON-Backup**: nur das aktuell angemeldete Benutzerprofil (Fächer, Tags, Tasks, Sessions, Pausensegmente, Ziele, Importjournal); kein Passwort, kein Browser-Login und kein laufender Timer.
- **Lernzeiten als CSV**: Sitzung, Fach, Aufgabe, Start/Ende (UTC), Fokusminuten, Pausenminuten, Pausenintervalle mit Uhrzeiten, Tags und Notizen.
- **Aufgaben als CSV**: Fach, Status, Priorität, Schätzung, Ist-Zeit, absolute und prozentuale Abweichung.
- **JSON-Backup wiederherstellen**: ersetzt nur das derzeit angemeldete Profil nach expliziter Bestätigung.

Zusätzlich legt die Anwendung vor dem ersten Profil-Änderungsvorgang pro Tag eine **lokale Sicherung** unter `~/.local/share/studytracker/backups/` an (die letzten 30 Tagesdateien je Profil). Diese liegt absichtlich außerhalb des Polybox-Projektordners und schützt vor einzelnen Sync-Fehlern. Sicher dir auch `data/accounts.json`, wenn du Konten auf einem anderen Computer wiederherstellen möchtest.

## Für Entwickler

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile server.py
node --check static/app.js        # optional, wenn Node vorhanden ist
```

Dateistruktur:

```text
.
├── .github/workflows/tests.yml
├── .gitignore
├── AGENTS.md
├── LICENSE
├── README.md
├── server.py
├── start.sh
├── static/{index.html,app.css,app.js}
├── schemas/tasks-import.schema.json
├── docs/{IMPORT.md,API.md,screenshots/}
├── prompts/email-to-tasks.md
├── examples/email-task-import.json
├── scripts/add_tasks.py
└── tests/{test_server.py,test_http.py}
```

CLI: `python3 server.py --help`. HTTP-Endpunkte sind in [`docs/API.md`](docs/API.md) erklärt. Reine Python-Standardbibliothek; kein externes Analytics-Tracking, kein CDN und kein API-Schlüssel.

### GitHub veröffentlichen

Der Projektordner ist ein **GitHub-fertiges Repository**, nicht automatisch ein bereits veröffentlichtes Remote-Repository.

```bash
git init
git add .
git commit -m "Initial StudyTracker v2"
git branch -M main
# Danach auf GitHub ein leeres Repository anlegen und dessen eigene Remote-URL verwenden:
git remote add origin <DEINE-GITHUB-REPOSITORY-URL>
git push -u origin main
```

`.gitignore` schließt deine persönlichen Daten, Konten und lokale Dateien aus. **Achtung:** Public GitHub-Repositories sind für sensible Daten ungeeignet – vor dem Push prüfen, dass nichts aus `data/` ins Repository gelangt.

## Einschränkungen

- Kein öffentliches Webhosting, keine serverübergreifende Echtzeit-Datenbank und keine gleichzeitige Bearbeitung desselben Polybox-Verzeichnisses auf mehreren Rechnern.
- Kein automatisches Abrufen von E-Mails; dafür ist ein separat eingerichteter Dienst/Agent nötig.
- Aktive Timer laufen auf Basis gespeicherter Zeitstempel weiter, wenn die Seite geschlossen wird, solange derselbe lokale Server und die Profildatei bestehen. Nach einem Rechnerneustart zeigt die App die vergangene Zeit seit dem letzten aktiven Fokus-/Pausenstart; die Sitzung muss ggf. manuell korrigiert oder verworfen werden.
- Benutzerkonten haben derzeit keinen Selbstbedienungs-Passwortreset; bei Verlust des Passworts brauchst du administrative Wiederherstellung über ein Backup des Kontenbestands.

## Lizenz

MIT. Siehe [LICENSE](LICENSE).
