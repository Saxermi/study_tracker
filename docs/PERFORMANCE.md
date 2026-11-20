# Performance and energy efficiency

## Low-power background operation (current)

The primary objective is to eliminate work, not change Linux power settings. StudyTracker stores timer state and interval endpoints as timestamps. Browser refresh frequency, timer throttling, tab visibility and suspend do not alter the persisted focus/break calculation. As before, a running session keeps counting wall-clock time through system suspend; pause the timer first if sleep should not count as study time.

### What changed

- **Clock:** one-second display callbacks exist only when a running focus/break timer is visible (dashboard or focus overlay). No one-second timer while idle, paused, on an unrelated page or in a hidden tab. Returning immediately refreshes elapsed values. Only changed clock labels are written.
- **Statistics:** bounded cached completed-session windows tied to the immutable session-array snapshot and local calendar boundary. Live intervals are clipped separately; future-dated manual sessions and backwards wall-clock corrections are not frozen in the cache. State changes conservatively invalidate cached windows. No per-second history scan; visible statistics refresh on state change, foreground return and at most once per minute while active.
- **Rendering:** rebuild only the selected page; hidden-tab updates defer rendering until foreground return. Indexes are reused for the same snapshot. Attendance runs only on Today/Week, with shared timezone formatters and unchanged markup retained. Clock-only mutations bypass the translation observer. No continuous CSS animation was found; existing short interaction transitions and static filters retain their appearance.
- **Synchronization:** a single request chain per tab, 15 s foreground / 60 s background, immediate revision check upon visibility return, a 10 s combined request timeout and exponential backoff capped at 5 min. Fetch the full profile only on revision change; reject a stale poll response after a local mutation or account change. No polling signed out.
- **Backend:** adaptive inbox polling waits 30 s when idle and 4 s around incoming files. The three-second quiet-file check remains, with an additional metadata check after reading. The small account file is cached safely using device/inode/size/mtime/ctime and defensive copies. No profile rewrite for a duplicate batch. Profile revision includes replacement metadata. The HTTP server's select timeout is 10 s; a ready connection still wakes it immediately.
- **Multi-tab:** each tab independently polls a small revision token. BroadcastChannel leader election was considered but not added: hidden-tab throttling, failed leaders and account changes would complicate reliable synchronization. Multiple tabs do not share private profile data through a new channel.

Set `STUDYTRACKER_INBOX_IDLE_SECONDS=4` for the former idle latency, or leave the default of 30 (valid range 4–300 s). The quick scan remains 4 s. Fresh files can take roughly the idle interval plus the quiet period/next quick scan and sync latency. Direct pasted/file-upload JSON imports are still immediate.

### Scheduled workload estimates (not hardware measurements)

Steady-state theoretical maximum callbacks/requests per hour, ignoring request duration, browser timer throttling and visibility changes. The former hidden-clock number is the requested frequency, not what Chromium necessarily executed.

| Workload | Before | After |
|---|---:|---:|
| One-second clock callbacks, visible idle | 3,600 | 0 |
| One-second clock callbacks, visible running timer | 3,600 | 3,600 (lightweight display only) |
| One-second clock callbacks, hidden running timer | 3,600 | 0 |
| Revision GETs, one visible tab | 720 | 240 |
| Revision GETs, one hidden tab | 720 | 60 |
| Revision GETs, one visible + two hidden tabs | 2,160 | 360 |
| Empty inbox scans | 900 | 120 |
| HTTP server select timeouts, no requests | 7,200 | 360 |

Idle visible pages still check time-sensitive calendar/attendance state through the polling loop; no extra idle one-second interval. Revision polling may cause one additional full-state request when changed. HTTP timeout counts and inbox scans are not equivalent to hardware wakeups.

### Measured before/after results — Linux CI, 20 November 2026

Baseline `abff5db`, optimization/benchmark commit `89dc794`. [Successful benchmark run #44762074271](https://github.com/Saxermi/study_tracker/actions/runs/44762074271). One sample on a hosted Linux runner; not measurements of the user's laptop. Frontend times measure the clock/Today-statistics functions over 60 simulated seconds, not total dashboard rendering or real browser resource usage (chart, attendance and browser rendering are outside this microbenchmark).

| Workload (60 simulated seconds) | Before: JS elapsed | After: JS elapsed | Mock DOM assignments before → after |
|---|---:|---:|---:|
| 1,000 tasks / 5,000 sessions, visible idle | 293.33 ms | 0.09 ms | 420 → 0 |
| Same profile, visible running timer | 328.78 ms | 0.74 ms | 420 → 63 |
| Same profile, hidden running timer | 266.97 ms | <0.01 ms | 420 → 0 |
| 5,000 tasks / 20,000 sessions, visible idle | 1,039.66 ms | <0.01 ms | 420 → 0 |
| Large profile, visible running timer | 1,097.18 ms | 0.46 ms | 420 → 63 |
| Large profile, hidden running timer | 1,094.63 ms | <0.01 ms | 420 → 0 |

Values reported as 0.00 ms by the script are below the reporting resolution, not proof of literally zero CPU. The visible running-timer loop executed 60 display callbacks both before and after; Today-statistics calls fell from 60 to one. No claim about GPU or whole-appliance power is implied. Initial large-profile active Today-statistics calculation was 28.10 ms before and 25.13 ms after; periodic work, not every initial load, is the main win.

| Real server / filesystem workload (1,000 / 5,000) | Before | After |
|---|---:|---:|
| Idle sample, no browser (12 s): process CPU | 10 ms | below 10 ms accounting resolution |
| Idle sample: observed thread context-switch delta | 26 | 2 |
| Idle server RSS | 29,444 KiB | 29,660 KiB |
| 100 authenticated revision GETs, elapsed | 79 ms | 73 ms |
| Same burst, server process CPU | 60 ms | 40 ms |
| 100 warmed empty inbox scans, process CPU | 11.97 ms | 6.37 ms |
| Account file reads / mkdir calls in 100 scans | 100 / 100 | 0 / 0 |
| Stat calls / glob calls in 100 scans | 300 / 100 | 300 / 100 |
| New file arrival through successful import + verification | 4.07 s | 22.09 s |

The new revision string includes inode/ctime information, increasing the measured revision payload from 35 to 76 bytes, while substantially lowering request frequency. At 240 visible requests/hour, the response body traffic is still only about 18 KiB/hour, versus 25 KiB/hour previously (excluding headers and changed state). RSS is essentially unchanged; no broad memory-reduction claim. The import delay is the intended energy/latency trade-off. Timing and CPU measurements vary with the runner, scheduling and file-arrival phase.

### Reproduce the benchmark

Use a clean worktree of the exact pre-optimization commit; never benchmark by switching your live synced profile back and forth. The scripts allocate temporary synthetic accounts and profiles and never operate on your live data. Linux /proc, Python 3.10+, and Node 18+ are enough.

```bash
git worktree add --detach /tmp/studytracker-before abff5db13679775d32db5ae4d8fd909ec377343d
TZ=Europe/Zurich node scripts/benchmark_frontend.cjs /tmp/studytracker-before 60
python3 scripts/benchmark_performance.py /tmp/studytracker-before --seconds 60 --requests 100
python3 scripts/benchmark_performance.py /tmp/studytracker-before --seconds 60 --tasks 5000 --sessions 20000
git worktree remove /tmp/studytracker-before
```

GitHub Actions also runs an abbreviated benchmark when the benchmarking scripts change. The frontend measures actual clock/statistics functions under Node with a simulated DOM, synthetic 1,000/5,000 and 5,000/20,000 task/session profiles, visible idle/active and hidden active scenarios. It reports elapsed JS/process CPU time, mock DOM assignments, callback counts, and heap deltas (GC can make them negative). It does **not** measure a real browser's rendering, CPU usage or memory. Initial rendering is measured separately from the warmed loop.

The Linux benchmark starts the actual old/new HTTP servers with no opened browser, times idle CPU and RSS from /proc, performs a real authenticated 100-request revision burst, counts selected Python Path operations over 100 empty inbox scans, and submits a new file to measure import latency. The context-switch delta is meaningful for the idle live threads only; it is a proxy for scheduling activity, not hardware wakeups. The filesystem counters instrument selected Python calls, not every kernel syscall. The multi-tab rate is a schedule estimate; for real multi-tab and browser energy measurements see below.

### Validate on an Ubuntu laptop

Use the same battery charge range, screen brightness, network, power profile, browser version, extensions and comparable workload for before/after. Pause unrelated background sync activity during controlled comparisons, but test incoming sync files separately. Unplug AC only for battery-discharge measurements. Perform several 5–10 minute repetitions, allowing the machine to settle first.

```bash
sudo apt install powertop sysstat lm-sensors
pgrep -af 'python.*server.py'
# Substitute the actual server PID from the previous command.
pidstat -u -w -r -p PID 5 60
# Read-only observation; do NOT use --auto-tune or --calibrate.
sudo powertop --time=60 --html=studytracker-power.html
sensors
grep -H . /sys/class/power_supply/BAT*/power_now 2>/dev/null
grep -H . /sys/class/power_supply/BAT*/energy_now 2>/dev/null
```

PowerTOP reports activity/wakeups and estimated power where supported. pidstat reports process CPU, voluntary/involuntary context switches and RSS; context switches are not identical to hardware wakeups. Battery power_now is typically microwatts; energy_now is typically microwatt-hours. Compare averages, not an isolated reading. If exposed by the kernel, package energy counters under /sys/class/powercap can also be sampled before and after; availability and domain coverage vary by APU/platform. sensors reports temperatures and sometimes power, depending on drivers. Whole-device battery power does not isolate StudyTracker or the APU.

For the browser, open Developer Tools → Performance monitor (CPU usage, JS heap, DOM nodes) and Network; record 5–10 minutes for no tab, idle dashboard, active dashboard, hidden active tab, and one foreground + two background tabs. Avoid leaving DevTools recording during battery tests; it changes the workload. The browser's task manager can show tab CPU when DevTools is closed. Verify focus/break totals with a stopwatch, including a visibility change, reload and suspend/resume. Verify Sunday/Monday boundaries and the incoming-file path using a synthetic JSON import.

### Remaining limits

Full-profile writes and changed-state responses still serialize the complete JSON profile. Large visible Kanban/history views can create many DOM nodes. Completed-window caches are bounded to two windows per live session snapshot; no permanent timer history or full-profile backend cache added. The heatmap is still computed when the Insights view needs it. No external or hardware-specific OS service or filesystem watcher was added; portable polling retains Nextcloud compatibility. The notebook's actual CPU wakeups, battery draw and temperature need measurement on that notebook. The app does not tune the OS.

---

## Historical 4.3 audit (previous optimization)


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
