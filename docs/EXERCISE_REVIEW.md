# Optional exercise assessment

Every task optionally stores **one** assessment as `exercise_review`, **not per attempt**. Missing or completely blank assessments are represented by `null`. Each field is independently optional.

| Field | Allowed values | Meaning |
| --- | --- | --- |
| `difficulty` | `null` or 1–5 | perceived difficulty |
| `outcome` | `null`, `correct`, `partial`, `incorrect` | fully/partially/incorrectly solved |
| `issue` | `null`, `concept`, `approach`, `calculation`, `implementation`, `instructions`, `careless`, `time`, `verification` | main problem; eight choices |
| `help_total` | `null` or 0–5 | total help from **all sources** |
| `help_chatgpt` | `null` or 0–5 | amount of help **attributable to ChatGPT** |

`0` explicitly means no help; `null` means unanswered. If both help values are provided, `help_chatgpt <= help_total` must hold. Either can be provided independently.

API: `PATCH /api/tasks/{id}/review` with a JSON object such as `{"difficulty":4,"outcome":"partial"}`. **This replaces the whole assessment**; it is not a merge-patch. `{}` clears it. JSON backup and task CSV include values; legacy tasks with no `exercise_review` are treated as unassessed.

Choose `Rate` on the Kanban board (including archived tasks). Checking off a task tagged “Exercises” optionally opens the dialog, which can be skipped. Copy prompt → ask ChatGPT → paste JSON response → apply suggestions → verify and save. No automated ChatGPT network access. See [prompt](../prompts/exercise-review.md).


### Pasted ChatGPT JSON and saving (bug fix)

Pasting ChatGPT's JSON into the optional response field is now sufficient: clicking **Save assessment** validates and applies a pending response, even if **Apply ChatGPT response** was not clicked first. **Apply** remains available to preview the suggested values. Null or missing suggestions never erase saved or manually entered ratings; a value explicitly selected in this dialog takes precedence. Use the `—` button to clear a rating yourself. Malformed or invalid JSON prevents saving and shows an error rather than silently discarding pasted feedback.

After saving, the task card, Today's tasks and archive display a concise summary (difficulty, outcome and assistance when available), and reopening the dialog loads the persisted assessment.
