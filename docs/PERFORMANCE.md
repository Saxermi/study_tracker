# Performance audit (StudyTracker 4.3)

StudyTracker uses one local JSON profile per user and no external Python dependencies. It is suitable for personal use, but not a concurrent multi-writer database.

## Changes

- Idle browser polling previously fetched the *entire profile* every five seconds. Now `GET /api/profile/revision` returns an approximately 35-byte change token, and the full profile is fetched **only if changed**.
- Frontend task, subject, tag and session lookups are indexed once on state refresh, rather than repeatedly scanning every session for each task.
- Hidden Kanban, History and Insights views are updated on opening; a closed archive does not render hidden cards. The heatmap is not recomputed every idle second.
- GPT feedback uses five optional scalar fields per task. No conversation transcripts are saved.

## Synthetic measurements

Measured in the development test container, not on the user's Ubuntu computer. These are **approximate Python process peak RSS** values, including interpreter/runtime baseline; browser RAM was not measured.

| Tasks / sessions | JSON profile file | HTTP profile response | Python peak RSS | Old idle polling traffic/h | Revised idle traffic/h |
|---|---:|---:|---:|---:|---:|
| 100 / 250 | 0.20 MiB | 0.15 MiB | 95 MiB | 104 MiB | ~0.024 MiB |
| 1,000 / 5,000 | 3.34 MiB | 2.47 MiB | 109 MiB | 1,775 MiB | ~0.024 MiB |
| 5,000 / 20,000 | 13.95 MiB | 10.33 MiB | 154 MiB | 7,437 MiB | ~0.024 MiB |

Assumes one open tab and 720 idle polls/hour. Traffic is *uncompressed response size*, not RAM consumption or disk writes.

## Limits and local audit

Profile writes and changed-state responses still serialize the whole profile, so memory and I/O scale with recorded sessions. Opening all historical rows can still create many DOM elements; pagination would be a future improvement for very large profiles. Polybox/Nextcloud is not a multi-writer database.

Run `python3 scripts/memory_audit.py` to see your own profile file sizes and counts, without printing study content. For live server RAM on Ubuntu, use `ps -o pid,rss,cmd -p <PID>` (RSS shown in KiB). No new runtime dependencies or telemetry are introduced.
