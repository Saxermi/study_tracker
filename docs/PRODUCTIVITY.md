# Execution-focused productivity workflow

This extension is **opt-in** and does not change existing Kanban statuses, exercise reviews,
semester handling, time tracking, or historical `planned_for` pins. It keeps all data locally
in the profile JSON (and the existing JSON backup).

## Six features

1. **Daily Top 3:** On **Today**, choose up to three priorities for the current local date.
   Priorities are a separate commitment layer. A task pinned in the classic Today view
   is not automatically a Top 3 priority. Incomplete priorities do not roll over to a new
   date; the prior day's plan is preserved in the local record. Click **Start** directly
   on a selected priority.
2. **Next Action:** Task edit form has a short optional next physical action (max 200
   characters); it is shown in Kanban, Today and the focus overlay.
3. **Time Budget:** Optionally enter available minutes (1-1440); the planner shows
   estimates and highlights when the selected tasks exceed capacity. Missing estimates
   are explicitly listed instead of counted as zero. When parent and child are both
   selected, the parent estimate is counted once.
4. **Focus Mode:** Starting a timer opens a quiet task-focused overlay by default,
   controlled through a setting at the bottom of Settings. Pausing, break, resume,
   and stop reuse the existing timer API. Closing the overlay leaves the timer running;
   use **Fokusansicht** on the overview timer to reopen it.
5. **Ready to Resume:** In Focus Mode, write an optional resume note for the active
   task (max 400 characters). Save explicitly or automatically on **Session speichern**.
   The note is retained on the task for next time. It is not recorded for unlinked sessions.
6. **Weekly Review:** On Today, open the optional weekly review. Enter what worked,
   obstacles, a future adjustment, and an optional if-then plan. Each review is keyed
   to the Monday of the user's local week.

## Optional weekly planning, recurring lectures and accomplishments

The **Week** page is separate from Today and is never required. Plan up to three weekly
outcomes and assign any open task to a Monday–Sunday day column; no task is moved
or pinned automatically. Weekly plans have their own records and do not affect Today
selections.

Enter a **recurring lecture** once with a subject, weekday, local start/end times,
first date, optional last date and IANA timezone. The timetable shows matching
occurrences. After the scheduled end, the next time the app is open on Week or Today,
an inline prompt asks **attended / missed / excused**, never inferring attendance from
the existence of a calendar entry. Prompts cover recent unconfirmed occurrences and
are shown only within StudyTracker. Deleting a recurring lecture removes its attendance
data; no OS notifications or calendar access is requested.

The **Accomplishments** page displays completed tasks from this week, the past
30 days, or all time. It puts user-chosen weekly outcomes first and avoids counting
a completed parent and its completed children as multiple separate outcomes.
It does not assign XP, streaks or scores.

Within Focus Mode, **Nur Session speichern** records time without marking the task
complete. **Aufgabe fertig + speichern** performs an atomic timer stop and linked
task completion. A single optional next-task suggestion is shown (prioritizing
user-selected daily and weekly goals); the user must explicitly choose to start.
**Timer verwerfen** retains the existing confirmation and discards unsaved time.

### New API endpoints

```http
PATCH /api/productivity/weekly-plan
{"week_start":"2026-11-16","outcome_ids":["task-id"],"days":{"2026-11-18":["task-id"]}}

POST /api/productivity/lectures
{"title":"Analysis II","subject_id":"mathe","weekday":0,
 "start_time":"09:00","end_time":"10:30",
 "first_date":"2026-11-16","last_date":null,"timezone":"Europe/Zurich"}

PATCH /api/productivity/lectures/{id}
DELETE /api/productivity/lectures/{id}
PATCH /api/productivity/lectures/{id}/attendance
{"date":"2026-11-16","status":"attended"}

POST /api/timer/stop
{"complete_task":true}
```

Dates are YYYY-MM-DD; weeks start Monday, weekdays are 0=Monday...6=Sunday.
A lecture ends in its declared timezone; attendance can only be saved afterward.
`complete_task` defaults to false for backward compatibility. For the underlying
peer-reviewed evidence and limitations, see [PSYCHOLOGY.md](PSYCHOLOGY.md).

## Persistence and API

`PATCH /api/productivity/daily-plan`:

```json
{"date":"2026-11-18","priority_ids":["existing-task-id"],"capacity_minutes":120}
```

`PATCH /api/productivity/weekly-review`:

```json
{"week_start":"2026-11-16","worked":"Finished chapter 2","obstacle":"Frequent interruptions","adjustment":"Smaller tasks","if_then":"If interrupted, write a resume note"}
```

`PATCH /api/tasks/{id}` supports optional `next_action` and `resume_note`.
`PATCH /api/settings` supports optional boolean `focus_mode_enabled`. Unrelated
settings are left unchanged if absent from the patch.

A profile can contain:

```json
{
  "productivity": {
    "daily_plans": {"2026-11-18": {"priority_ids": [], "capacity_minutes": null}},
    "weekly_reviews": {"2026-11-16": {
      "worked": "", "obstacle": "", "adjustment": "", "if_then": ""
    }}
  }
}
```

Existing profiles and old `version: 2` backups without these keys load normally.
JSON backup/restore validates data, references and size limits. Deleted tasks are removed
from daily plans; historical daily plan entries themselves remain. The new task fields
also appear in the Tasks CSV. No external data transfer or subscription is added.

## Design constraints

- Not all tasks require a next action, review or estimate.
- The planner does **not** add artificial deadlines or automatically reprioritize tasks.
- The 3-task default is a UI heuristic, not a proven optimal number.
- Focus Mode hides this application's dashboard, not other Ubuntu windows or browser tabs.
- The daily capacity is compared only to the selected Top 3 tasks.
- This is a workflow feature, not a clinical intervention or a validated productivity score.
- StudyTracker still supports only one computer actively editing synced JSON at a time.

## Testing

Run the existing complete suite plus the new regression tests:

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js
node --check static/productivity.js
TZ=Europe/Zurich node --test tests/*.cjs
```
