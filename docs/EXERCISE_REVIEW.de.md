# Optionale Exercise-Bewertung

Eine Aufgabe speichert optional **eine** Bewertung im Feld `exercise_review` (kein Versuchstagebuch). Fehlende oder vollständig leere Bewertungen werden als `null` gespeichert. Alle Einzelfelder können unabhängig voneinander leer bleiben.

| Feld | Gültige Werte | Bedeutung |
| --- | --- | --- |
| `difficulty` | `null` oder 1–5 | empfundene Schwierigkeit |
| `outcome` | `null`, `correct`, `partial`, `incorrect` | richtig / teilweise / falsch |
| `issue` | `null`, `concept`, `approach`, `calculation`, `implementation`, `instructions`, `careless`, `time`, `verification` | Hauptproblem, acht Möglichkeiten |
| `help_total` | `null` oder 0–5 | Hilfe durch **alle Quellen** |
| `help_chatgpt` | `null` oder 0–5 | Anteil der Hilfe **durch ChatGPT** |

`0` bedeutet ausdrücklich keine Hilfe, `null` bedeutet nicht beantwortet. Wenn beide Hilfewerte vorhanden sind, muss `help_chatgpt <= help_total` gelten; nur eines der beiden Felder auszufüllen ist erlaubt.

API: `PATCH /api/tasks/{id}/review` mit JSON-Objekt, z. B. `{"difficulty":4,"outcome":"partial"}`. **Dieser Aufruf ersetzt die gesamte Bewertung**, nicht nur einzelne Felder. Ein leeres `{}` löscht die Bewertung. JSON-Backup und Task-CSV enthalten die Werte. Für ein altes Profil ohne `exercise_review` wird `null` angenommen.

Im Kanban (auch im Archiv) `Bewerten` öffnen. Für einen mit „Übungen“ markierten Task wird nach dem Abhaken optional der Dialog geöffnet und kann übersprungen werden. Prompt kopieren → ChatGPT-Antwort als JSON einfügen → Vorschläge übernehmen → selbst bestätigen und speichern. Es gibt keinen automatischen Netzwerkzugriff auf ChatGPT. Siehe [Prompt](../prompts/exercise-review.de.md).
