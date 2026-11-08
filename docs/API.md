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
