# ChatGPT-Prompt: eine Exercise bewerten (Deutsch)

Kopiere diesen Prompt nach einer Übung in ChatGPT zusammen mit der Aufgabenstellung, deiner eigenen Lösung und dem relevanten Chatverlauf. Ohne diese Inhalte kann ChatGPT deine Selbstständigkeit nicht zuverlässig beurteilen. Der Prompt erscheint auch direkt im StudyTracker-Bewertungsdialog.

> Beurteile, wie selbstständig ich diese Übung gelöst habe, ausschließlich anhand der vorliegenden Aufgabenstellung, meiner Lösung und unseres Dialogs. Erfinde keine Beobachtungen, Fehler oder Hilfen. Wenn du etwas nicht beurteilen kannst, verwende `null`.
>
> Gib **nur ein einzelnes JSON-Objekt** zurück mit den optionalen Feldern:
> `difficulty` (1–5, 1=leicht), `outcome` (`correct`, `partial`, `incorrect`), `issue` (`concept`, `approach`, `calculation`, `implementation`, `instructions`, `careless`, `time`, `verification`), `help_total` (0–5), `help_chatgpt` (0–5). `0` bedeutet keine Hilfe; `null` bedeutet nicht bewertet. ChatGPT-Hilfe darf nicht höher als die gesamte Hilfe sein, wenn beide Zahlen bekannt sind. Keine Erläuterungen oder Codeblöcke.
>
> Frage nicht nach nicht sichtbaren Daten, sondern verwende für diese `null`. Ich bestätige die Bewertung selbst in StudyTracker.

Beispiel: `{"difficulty": 4, "outcome": "partial", "issue": "approach", "help_total": 3, "help_chatgpt": 2}`

Du kannst das Ergebnis direkt in das JSON-Feld im Bewertungsdialog einfügen, auf **ChatGPT-Antwort übernehmen** klicken, die Werte prüfen und sie dann speichern. Keine Angaben sind verpflichtend. Es gibt aktuell **nur eine Bewertung pro Aufgabe** und keinen Prüfungs- oder Wiederholungsmodus.
