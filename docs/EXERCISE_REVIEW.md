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


## Copyable AI output

Return **one copyable fenced JSON code block** (```json ... ```) with no surrounding prose. When saving an import `.json` file, omit the fences and save **only** the JSON content.

Additional optional feedback: `issues` (up to three issue codes); `strength` and `weakness` (one sentence each, max 200 characters); `skill_gap` (max 100); `next_action` (max 160); `chatgpt_interventions` (up to three of `verification`, `hint`, `guiding_questions`, `concept_explanation`, `approach_selection`, `step_by_step`, `debugging`, `calculation`, `code_generation`, `full_solution`, `error_identification`). Existing `issue` remains the primary issue. Sources remain separate and optional. No transcripts or attempt histories.
