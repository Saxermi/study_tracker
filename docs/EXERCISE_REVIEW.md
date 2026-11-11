# Exercise ratings (StudyTracker 4.3)

There are **two separate optional ratings per exercise**, not a history of attempts:

- `exercise_review`: **your own** assessment.
- `exercise_review_gpt`: ChatGPT’s **suggested** assessment, saved separately after you paste JSON and click Save.

The dialog labels each source, displays a comparison, and provides **Use GPT** per field. GPT never silently replaces your rating. The copyable prompt is collapsible. The example JSON in the UI is illustrative and **not automatically saved**.

## Example response

```json
{"difficulty":3,"outcome":"partial","issue":"concept","help_total":4,"help_chatgpt":4}
```

All five fields may be left blank, independently: `difficulty` (1–5), `outcome` (`correct|partial|incorrect`), `issue` (one of `concept|approach|calculation|implementation|instructions|careless|time|verification`), `help_total` (0–5), `help_chatgpt` (0–5). `null` means not assessed; `0` means no help. If both help values are known, ChatGPT assistance must not exceed total help.

## API

`PATCH /api/tasks/{id}/review` accepts a combined atomic payload:

```json
{"self":{"difficulty":2},"gpt":{"difficulty":3,"outcome":"partial","issue":"concept","help_total":4,"help_chatgpt":4}}
```

Omit a source to preserve it; explicitly send `null` to clear it. Old clients may still send a flat `{"difficulty":2}` payload; it updates **only** the self-rating. Older profiles lacking `exercise_review_gpt` load normally. Both sources are exported in backups and separate CSV columns. Chat transcripts are not stored.
