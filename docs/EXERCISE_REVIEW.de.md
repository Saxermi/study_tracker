# Übungsbewertungen (StudyTracker 4.3)

Eine Aufgabe kann **zwei getrennte optionale Bewertungen** enthalten, kein Versuchstagebuch:

- `exercise_review`: **deine eigene** Bewertung.
- `exercise_review_gpt`: die **Einschätzung von ChatGPT**, getrennt gespeichert.

Beide Quellen werden klar beschriftet und verglichen. Mit **Übernehmen** wählst du einzelne GPT-Werte ausdrücklich aus; sie ersetzen deine eigene Einschätzung niemals automatisch. Der Prompt ist aufklappbar. Das JSON-Beispiel wird **nicht** automatisch gespeichert.

## Beispiel

```json
{"difficulty":3,"outcome":"partial","issue":"concept","help_total":4,"help_chatgpt":4}
```

Jedes Feld kann leer bleiben: `difficulty` (1–5), `outcome` (`correct|partial|incorrect`), `issue` (`concept|approach|calculation|implementation|instructions|careless|time|verification`), `help_total` (0–5), `help_chatgpt` (0–5). `null` = keine Angabe, `0` = keine Hilfe. ChatGPT-Hilfe darf bei bekannten Werten nicht größer als Gesamthilfe sein.

## API

`PATCH /api/tasks/{id}/review` unterstützt:

```json
{"self":{"difficulty":2},"gpt":{"difficulty":3,"outcome":"partial","issue":"concept","help_total":4,"help_chatgpt":4}}
```

Ausgelassene Quellen bleiben erhalten, `null` löscht die Quelle. Alte flache Anfragen bearbeiten weiterhin **nur deine eigene Bewertung**. Bestehende Profile ohne `exercise_review_gpt` bleiben gültig. Beide Quellen erscheinen getrennt in JSON-Backups und CSV. Chatverläufe werden nicht gespeichert.


## Kopierbare KI-Ausgaben

Gib im Chat einen **kopierbaren JSON-Codeblock** (```json ... ```) ohne weiteren Text zurück. Importdateien enthalten ausschließlich den JSON-Inhalt **ohne** Codezäune.

Additional optional feedback: `issues` (up to three issue codes); `strength` and `weakness` (one sentence each, max 200 characters); `skill_gap` (max 100); `next_action` (max 160); `chatgpt_interventions` (up to three of `verification`, `hint`, `guiding_questions`, `concept_explanation`, `approach_selection`, `step_by_step`, `debugging`, `calculation`, `code_generation`, `full_solution`, `error_identification`). Existing `issue` remains the primary issue. Sources remain separate and optional. No transcripts or attempt histories.
