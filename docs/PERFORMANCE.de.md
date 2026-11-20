# Performance und Energieeffizienz

## Energiesparender Hintergrundbetrieb (aktuell)

Ziel ist weniger unnötige Arbeit, nicht die Änderung von Linux-Energieeinstellungen. Lernzeit und Pausen werden anhand von Zeitstempeln erfasst; die Frequenz der Browser-Anzeige, Tab-Drosselung und das Neuladen der Seite verändern diese Berechnung nicht. Wie bisher zählt ein laufender Timer die verstrichene Zeit auch im Standby weiter; vor dem Schlafmodus pausieren, wenn diese Zeit nicht als Lernzeit gelten soll.

### Änderungen

- **Uhr:** sekündliche Anzeige nur bei laufender Fokus-/Pausenzeit und sichtbarer Uhr (Übersicht oder Fokusoverlay). Keine sekündlichen Callbacks im Leerlauf, bei unterbrochenem Timer, auf anderen Seiten oder verstecktem Tab. Bei Rückkehr sofort aktualisieren; unveränderte Zahlen nicht neu schreiben.
- **Statistik:** abgeschlossene Sessions pro Profil-Snapshot und Kalenderfenster zwischenspeichern, laufende Session separat zurechnen. Cache bei neuen Session-Daten und Datumsgrenzen erneuern; zukünftige manuelle Sessions und rückwärts laufende Systemzeit berücksichtigen. Keine sekündlichen Historien-Scans; aktive sichtbare Statistik maximal einmal pro Minute bzw. sofort bei Profiländerung/Rückkehr aktualisieren.
- **Rendering:** nur sichtbare Seite neu zeichnen; bei verstecktem Tab bis zur Rückkehr warten. Indizes pro Snapshot wiederverwenden. Anwesenheitsabfrage nur in Heute/Woche, Zeitzonen-Formatter wiederverwenden und identisches Markup beibehalten. Uhr-Mutationen lösen keine vollständige Übersetzung aus. Keine dauerhaften CSS-Animationen festgestellt; kurze UI-Übergänge und statische Filter bleiben erhalten.
- **HTTP:** 15 s sichtbar, 60 s versteckt; sofortige Abfrage bei Rückkehr. Keine überlappenden Synchronisierungsabfragen, 10 s Zeitlimit, exponentieller Backoff bis 5 min. Ganzes Profil nur bei geänderter Revision. Veraltete Antworten nach Mutationen/Kontowechsel verwerfen; keine Abfragen nach Abmeldung.
- **Backend:** Inbox-Abfrage adaptiv 30 s im Leerlauf, 4 s bei Aktivität. Drei Sekunden Dateiruhe bleiben erforderlich; zusätzliche Prüfung nach dem Lesen. Kleine Kontendatei wird anhand von dev/inode/Größe/mtime/ctime und defensiven Kopien sicher zwischengespeichert. Keine erneute Profildatei-Schreibung bei identischer Batch-ID. Revision erkennt auch Dateiersatz. HTTP-Server wartet bis zu 10 s auf den nächsten internen Leerlauf-Check, eingehende Anfragen wecken ihn sofort.
- **Mehrere Tabs:** separate kleine Revisionsabfragen. Keine BroadcastChannel-Leader-Wahl: Drosselung im Hintergrund, Ausfall des führenden Tabs und Kontowechsel erschweren zuverlässige Synchronisation.

`STUDYTRACKER_INBOX_IDLE_SECONDS=4` stellt die frühere Leerlauf-Latenz wieder her. Standard 30 s, gültiger Bereich 4–300 s. Dateien können bis etwa zum nächsten Leerlauf-Intervall plus Wartezeit auf Stabilität und Sync-Latenz benötigen. Direktes Einfügen/Hochladen bleibt sofort möglich.

### Rechnerische Aktivitätsraten (keine Hardwaremessung)

| Vorgang pro Stunde | Vorher | Nachher |
|---|---:|---:|
| Sekundenuhr, sichtbarer Leerlauf | 3.600 | 0 |
| Sekundenuhr, sichtbarer aktiver Timer | 3.600 | 3.600 (nur Anzeige) |
| Sekundenuhr, versteckter aktiver Timer | 3.600 | 0 |
| Revisionsabfragen, sichtbarer Tab | 720 | 240 |
| Revisionsabfragen, versteckter Tab | 720 | 60 |
| Revisionsabfragen, 1 sichtbarer + 2 versteckte Tabs | 2.160 | 360 |
| Leere Inbox-Scans | 900 | 120 |
| HTTP-Wartezeitabläufe ohne Anfragen | 7.200 | 360 |

Ideale Raten ohne Browser-Drosselung, Request-Laufzeiten, Sichtbarkeitswechsel und Profiländerungen. Die ursprünglich angeforderte Hintergrundfrequenz ist nicht zwingend die ausgeführte Frequenz. Ein HTTP-Timeout ist kein Hardware-Wakeup. Im sichtbaren Leerlauf prüft der Polling-Loop noch Datum und zeitabhängige Anwesenheit; keine zusätzliche Sekundenuhr.

### Reproduzierbarer Vergleich

Die Benchmarks verwenden ausschließlich temporäre synthetische Profile, keine persönlichen Daten. Der alte Stand bleibt in einem getrennten Git-Worktree.

```bash
git worktree add --detach /tmp/studytracker-before abff5db13679775d32db5ae4d8fd909ec377343d
TZ=Europe/Zurich node scripts/benchmark_frontend.cjs /tmp/studytracker-before 60
python3 scripts/benchmark_performance.py /tmp/studytracker-before --seconds 60 --requests 100
python3 scripts/benchmark_performance.py /tmp/studytracker-before --seconds 60 --tasks 5000 --sessions 20000
git worktree remove /tmp/studytracker-before
```

Das Frontend-Skript misst echte JS-Funktionen mit simuliertem DOM und 1.000/5.000 sowie 5.000/20.000 Aufgaben/Sessions. Es meldet JS- und CPU-Zeit, simulierte DOM-Zuweisungen, Callbacks und Heap-Differenz; keine echte Browser-GPU-/RAM-Messung. Der Linux-Test startet die echten Server ohne Browser, misst Prozess-CPU/RSS und beobachtet Kontextwechsel aus /proc, sendet 100 echte authentifizierte Revisionsanfragen, zählt ausgewählte Python-Dateioperationen bei 100 leeren Scans und testet einen echten eingehenden Import. Kontextwechsel sind nur ein Näherungsindikator für Scheduling, keine Hardware-Wakeups. Dateiaufrufe sind keine vollständige Syscall-Zählung. Mehrtab-Raten sind berechnet.

### Auf Ubuntu messen

Gleiche Helligkeit, Browser-Version, Erweiterungen, Netz, Ladezustand und Energieprofil für beide Stände. Mehrmals je 5–10 Minuten messen. Für Akku-Messung Netzteil abziehen und sonstige Hintergrundlast möglichst konstant halten.

```bash
sudo apt install powertop sysstat lm-sensors
pgrep -af 'python.*server.py'
pidstat -u -w -r -p PID 5 60
sudo powertop --time=60 --html=studytracker-power.html
sensors
grep -H . /sys/class/power_supply/BAT*/power_now 2>/dev/null
grep -H . /sys/class/power_supply/BAT*/energy_now 2>/dev/null
```

PID durch die Prozessnummer ersetzen. Keine Optionen --auto-tune oder --calibrate verwenden. pidstat zeigt CPU, RSS und Kontextwechsel; PowerTOP zeigt Aktivität/Wakeups und gegebenenfalls geschätzte Leistung. Akkuwerte üblicherweise in µW bzw. µWh; Mittelwerte vergleichen. Falls verfügbar, Energiezähler unter /sys/class/powercap auslesen; unterstützte APU-Domänen hängen von Treiber/Hardware ab. sensors zeigt Temperaturen und ggf. Leistung. Gesamte Akkuentladung lässt sich nicht direkt StudyTracker zuordnen.

Im Browser DevTools → Performance monitor/Network bzw. Browser-Taskmanager vergleichen: ohne Tab, sichtbare Übersicht ohne Timer, mit Timer, versteckter aktiver Tab sowie mehrere Tabs. DevTools vor Akku-Messungen schließen. Timer mit Stoppuhr prüfen, inklusive Wechsel der Sichtbarkeit, Reload, Standby und Wochenwechsel; neuen Inbox-Import separat testen.

### Grenzen

Datei-Schreibvorgänge und geänderte Profilantworten serialisieren weiterhin das ganze JSON. Große sichtbare Kanban-/Historienansichten können viele DOM-Knoten enthalten; Heatmap wird bei Bedarf gerechnet. Der Window-Cache hält maximal zwei Kalenderfenster pro aktivem Session-Snapshot. Kein dauerhaftes Profil-Cache im Backend und keine zusätzliche Datenbank, Abhängigkeit oder OS-Dienst. Portables adaptives Polling statt plattformspezifischem Watcher. Keine Messwerte für echte Akku-Leistung, APU-Energie oder Temperatur ohne Messung auf dem Laptop.

---

## Historischer 4.3-Check (frühere Optimierung)


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
