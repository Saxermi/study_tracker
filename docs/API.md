# StudyTracker local API (English)

**Deutsch:** [API.de.md](API.de.md). Local HTTP API, bound to `127.0.0.1` and authenticated through a same-site, HttpOnly session cookie. Do not expose this development service to the Internet.

## Authentication

- `GET /api/auth/status` — current user and whether initial setup is required.
- `POST /api/auth/setup` — first local administrator (`display_name`, `username`, `password`, min 10 chars).
- `POST /api/auth/login` — authenticate by username/password.
- `POST /api/auth/logout` — close the current session.
- `GET /api/users` / `POST /api/users` — administrator-only user management.

## Study data (authenticated)

- `GET /api/state` — per-user profile (subjects, semesters, tags, tasks, sessions, timer and settings).
- `POST /api/semesters`, `PATCH/DELETE /api/semesters/<id>`.
- `POST /api/subjects`, `PATCH /api/subjects/<id>` — name, color (`#RRGGBB`), optional `semester_id`, optional `weekly_goal_minutes` (`null` = no target).
- `POST /api/tags`, `DELETE /api/tags/<id>`.
- `POST /api/tasks`, `PATCH/DELETE /api/tasks/<id>` — title, subject, optional `parent_id`, optional `planned_minutes`, status (`todo|doing|done`), priority (`low|normal|high`), tags, due_date, `planned_for` (`YYYY-MM-DD`/null).
- `POST /api/sessions`, `PATCH/DELETE /api/sessions/<id>` — study sessions, with optional `task_id`.
- Timer endpoints: `POST /api/timer/start`, `/pause`, `/resume`, `/break-start`, `/break-end`, `/stop`, `/discard`.
- `PATCH /api/settings` — optional weekly goal (`weekly_goal_minutes: null` removes it).

### Parent and child task rules

`parent_id` is another task's **internal** ID; one level deep only, same subject, no cycles. Every child is an independent task. Completing all children completes the parent automatically; explicitly completing/reopening a parent cascades to every child. Reopening a single child reopens its parent, leaving other completed children unchanged. Deleting a parent detaches its children. Optional estimates are null or positive integers.

## Import / export

- `POST /api/import/tasks` — upload a complete JSON envelope (`studytracker.tasks.v1`) with `external_id`/`parent_external_id`. Full schema: [`schemas/tasks-import.schema.json`](../schemas/tasks-import.schema.json). Parent links resolve in a second pass.
- `POST /api/import/backup` — restore a **complete per-user** StudyTracker JSON backup after explicit user confirmation; replaces profile data.
- `GET /api/export?format=json` — complete JSON backup, `version: 2` for compatibility, with active timer intentionally omitted.
- `GET /api/export?format=csv&kind=tasks|sessions` — UTF-8-BOM CSV, semicolon-delimited for LibreOffice. Task CSV includes internal parent task ID, direct task time, and separate parent roll-up columns. Session CSV includes focus and break durations.

The agent JSON format is **identical** for German and English: property names and enum values never change. A task's `semester` in the agent format is a human-readable name; the internal API uses `semester_id`.

## v4: Session categories and archive rules

`POST /api/timer/start` accepts optional `category_tag_id` (`null` or the ID of an existing tag). This overrides the task's first tag; the selected category is written to the active timer and final session. `POST/PATCH /api/sessions` accepts the same field. `GET /api/state` and JSON exports include it on sessions. CSV `kind=sessions` appends a `Kategorie` column. No new archive endpoint exists: the UI archives a task when `status == "done"` and `completed_at` is at least 48 hours old; edit/reopen via the existing task endpoint. The agent task-import schema is unchanged.

## Focus interval extension / Fokusintervalle (4.1)

Timer-created sessions include an optional `focus_intervals` array of `{ "started_at": "...", "ended_at": "..." }` ISO-8601 pairs. These are recorded whenever focus changes to paused/break/stopped. Legacy sessions without intervals remain supported. Time-of-day statistics use these spans and exclude breaks; a legacy estimate is indicated when the precise timing is unavailable. JSON backup/restore preserves validated focus intervals.

## Optional exercise assessment
`PATCH /api/tasks/{id}/review` sets the full optional `exercise_review` object. All values are independently nullable; `{}` clears it. The field appears in task responses and JSON backups. Task CSV contains five columns. See [exercise review](EXERCISE_REVIEW.md).

## 4.3 — Two-source exercise ratings and profile revision

`PATCH /api/tasks/{id}/review` supports an atomic payload `{"self":{"difficulty":2},"gpt":{"difficulty":3}}`. A missing source is preserved; an explicit `null` clears that source. The legacy flat payload still modifies only the self rating. Tasks/JSON exports include `exercise_review` and `exercise_review_gpt`, both optional; tasks CSV includes distinct columns.

Authenticated `GET /api/profile/revision` returns a small opaque string `revision`; `GET /api/state` and mutation responses include the same revision, so a client need not download unchanged profiles.

## Import assistant ID fields (v4.4)

`POST /api/import/tasks` accepts optional `subject_id` instead of `subject`; IDs must exist in the authenticated profile. If both are supplied, they must refer to the same subject, and an optional `semester` must match its assignment. `parent_id` attaches a new child to an existing root task in the same subject; for newly created parent tasks use `parent_external_id`. Both parent keys together are invalid. Invalid IDs reject the entire batch atomically. The envelope remains `studytracker.tasks.v1`.
