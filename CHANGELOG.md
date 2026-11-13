# Changelog (English)

## 4.4 — ID-aware import assistant

- Added an in-app import assistant with selected subject and optional existing parent task.
- Seven source-specific prompt types, English/German Markdown documents and a copy/save flow.
- Generated instructions include real `subject_id`/`parent_id` values and direct-child task rules.
- Backend validates ID-based assignments atomically; older name-based import files still work.


## 4.1 — Study-time heatmap (24h / 48h / typical week)

- Added a local-time 24-hour / 48-hour / typical-week heatmap, subject filtering, accessible hover/focus tooltips and both average and total weekly views.
- Exact focus intervals are now persisted across timer breaks, pause/resume and midnight; JSON backup round-trips them.
- Fixed Today totals and Today hourly bars for cross-midnight sessions; legacy sessions display estimated timing where necessary.
- Added JavaScript unit tests and Node CI job.

## 4.0 — Today, completed-task archive and category breakdown

- Live today focus total on Overview and Today; per-subject totals on Today.
- Today-only hourly rhythm and subject charts on Overview; a Today option in Insights.
- Calculated 48-hour archive on Kanban with 10/30-day/all-time, subject and text filters.
- Optional `category_tag_id` on timer and sessions; new Vorlesung/Videos tags, single-count category insights with subject/date filtering.
- Improved interactive chart tooltips and refined dashboard layout.
- Backward-compatible JSON profiles, additional CSV category column, bilingual agent/API documentation and regression tests.

## 3.0 — Linked tasks, bilingual UI and theme

- Separate Kanban cards for subtasks, linked to parents through `parent_id`.
- Bidirectional parent/child completion, independent timer and Today selection.
- Optional time estimates; parent roll-up statistics avoid double counting.
- JSON task import supports stable `parent_external_id` and optional `semester`, with validation and deduplication.
- Semesters for grouping subjects and optional per-subject/global weekly goals.
- Functional custom subject color picker and fixed CSP for dynamic color styles.
- Day planner, German/English UI, light/dark mode and browser favicon.
- Extended CSV columns, backward-compatible JSON profiles, bilingual docs and regression tests.

## 2.x — Initial study tracker

- Kanban, multi-user profiles, timer with breaks, analytics, JSON/CSV exports and task inbox.

## 4.2 — Optional exercise assessment
- One optional review per task, with independently optional difficulty, outcome, eight problem codes, total help, and ChatGPT help.
- Copyable German/English ChatGPT prompt and manual JSON suggestion import in the assessment dialog.
- Reviews in task CSV and backup JSON; legacy and unassessed tasks remain supported. No exam mode or attempt history.


## 4.2.1 — Exercise review persistence & ChatGPT JSON save fix

- Saving a pasted ChatGPT JSON response now applies it, even without first clicking **Apply ChatGPT response**.
- Manual ratings take precedence; unknown (`null`) AI values do not erase existing ratings. Invalid JSON blocks save with an error.
- Saved difficulty, solution outcome and assistance appear on task cards, Today and the Kanban archive.
- Added Node regression tests and CI coverage of JSON feedback imports.

## 4.3 — Separate self/GPT ratings and lighter idle polling

- GPT exercise feedback and personal ratings are stored separately, visible side by side, and preserved in backups and CSV.
- The dialog shows an explicit JSON example, not a misleading placeholder. Copying individual GPT values into the personal assessment is always manual.
- Added single-response save semantics, input validation and regression tests.
- Replaced full-state idle polling with a small revision token; indexed repeated task/session lookups and lazy-rendered hidden views. Added performance documentation.


## Copyable AI output

Return **one copyable fenced JSON code block** (```json ... ```) with no surrounding prose. When saving an import `.json` file, omit the fences and save **only** the JSON content.


**New:** Multi-issue feedback, optional concise strength and weakness sentences from user and GPT, skill gap, next action and GPT assistance types. Today tasks stay pinned after midnight. Kanban has an import shortcut. Copyable JSON output is requested in AI prompts.
