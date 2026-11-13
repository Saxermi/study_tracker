# Importing tasks from AI agents, emails and Polybox (English)

**Deutsch:** [IMPORT.de.md](IMPORT.de.md) · [English agent instructions](../AGENTS.md) · [German agent instructions](../AGENTS.de.md)

## Quick setup

1. Copy an email or assignment sheet to ChatGPT or another authorized agent using [the English prompt](../prompts/email-to-tasks.md).
2. Ask for **only** an import JSON object in the stable `studytracker.tasks.v1` format. Example: [`examples/email-task-import.json`](../examples/email-task-import.json).
3. Save the JSON as a file and either upload it in **Settings → Import → Import tasks JSON** or put it into the private local sync directory `data/inbox/<username>/`.
4. Keep StudyTracker running. It detects stable `.json` files every ~4 seconds, validates them as an atomic batch, adds only unseen task IDs and moves processed/rejected files accordingly.

## Example with independent subtasks

```json
{
  "format": "studytracker.tasks.v1",
  "batch_id": "source-mail-42-v1",
  "tasks": [
    {"external_id":"mail-42:1","subject":"Mathematik","semester":"Fall 2026","title":"Assignment 1","planned_minutes":120},
    {"external_id":"mail-42:1:B","parent_external_id":"mail-42:1","subject":"Mathematik","semester":"Fall 2026","title":"Part B","planned_minutes":30,"planned_for":null},
    {"external_id":"mail-42:1:C","parent_external_id":"mail-42:1","subject":"Mathematik","semester":"Fall 2026","title":"Part C","planned_minutes":null}
  ]
}
```

All tasks are independently visible on Kanban. Parent links are resolved even when the parent appears after its children in the JSON. To avoid an ambiguous subject with the same name in several semesters, specify the `semester` name. If absent and there is exactly one matching subject, the existing subject is used.

`planned_minutes` may be omitted/null; estimates do not have to be made up. New tasks are created in `todo` and never carry completed status or actual study time. `external_id` identifies a task across batches; `batch_id` identifies an entire source import. Use stable IDs to ensure idempotence.

## From a terminal

```bash
python3 scripts/add_tasks.py --user alex --file ~/Downloads/tasks.json
```

This safely stages a temporary file then renames it to `.json`. It does not retrieve email and it does not run the app. The app must be running for automated imports, or run `python3 server.py --import-once` when no other instance is active.

## Privacy, sync, limitations

Polybox only synchronizes local files. Writing into `data/inbox/` requires a program/agent with actual access to that directory; an ordinary ChatGPT conversation cannot place files there automatically. The app does not connect to Gmail/Outlook/IMAP or store mailbox credentials. Any email integration must be separately authorized.

Rejected input is moved to `data/inbox/<username>/rejected/` with a `.error.txt` explanation; accepted input goes to `processed/`. The entire batch is validated before committing changes. File limit: 1 MB; 1–150 tasks per file. JSON is treated as data and never executed as code. The importer does not silently update existing tasks.

### v4: Classify tasks for later study-time analytics

If the source is a lecture, add `"tags": ["Vorlesung"]`; for a video add `"tags": ["Videos"]`; for exercise work `"tags": ["Übungen"]`. These are **task tags**, not recorded time. Category selection happens when the user records a session. Do not add `category_tag_id` to an imported task: the task-import schema is unchanged.

## ID-targeted import (v4.4)

1. In Settings → Import assistant select an existing subject, and optionally an existing parent task.
2. Choose one of seven source types; copy or download the generated Markdown.
3. Give those instructions plus source material to ChatGPT/another agent.
4. Import its `studytracker.tasks.v1` JSON in Settings or via the private inbox.

`subject_id` is the exact ID of an existing subject in the signed-in profile. Optional `parent_id` is the ID of an **existing** root task in that subject. Unknown or mismatched IDs reject the entire import. New parents with children instead use `parent_external_id`. See [`examples/targeted-task-import.json`](../examples/targeted-task-import.json) and the source-specific Markdown files in [`prompts/import/`](../prompts/import/).


## Copyable AI output

Return **one copyable fenced JSON code block** (```json ... ```) with no surrounding prose. When saving an import `.json` file, omit the fences and save **only** the JSON content.
