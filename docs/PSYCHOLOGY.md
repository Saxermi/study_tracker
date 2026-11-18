# Psychological evidence for StudyTracker's productivity features

This is an **evidence ledger**, not a claim that the specific StudyTracker UI has been scientifically validated.
Research on goal pursuit, self-regulation, interruptions and work performance provides hypotheses for designs.
The strongest evidence generally addresses **mechanisms**, not complete productivity applications.
The tool stays local-first and requests **no OS permissions**, website access, browser history, or notification interception.

## Time-first study planning: effort is not the same as task completion

The StudyTracker weekly planner now supports optional **subject-specific focus-time
budgets** (e.g., Mathematics 4 hours; Programming 2 hours) and compares the plan
with recorded focus sessions. The Today and Accomplishments pages acknowledge
focus time even when no task is marked completed. This is an effort/consistency
measure, **not evidence of mastery, efficiency or achievement**. Lectures marked
attended do not automatically add study time; breaks are excluded.

The best-supported model is **time budget first, meaningful tasks second**, not
replacing tasks with hour-only scores. Our evidence assessment:

- **Memmi & Etkin (2026)**, *Time before goals: the benefits of budgeting time
  first for multiple goal setting and pursuit*, *Organizational Behavior and
  Human Decision Processes*, 195, article 104498.
  https://doi.org/10.1016/j.obhdp.2026.104498
  Experimental research finds that allocating a limited time budget across
  competing goals *before* setting performance targets can improve realistic
  goal setting and subsequent progress. Workplace/multiple-goal tasks, not
  a direct evaluation of subject-level study-tracker UI.
- **Theobald (2025)**, *Study longer or study effectively? Better study strategies
  can compensate for less study time and predict goal achievement and lower
  negative affect*, *British Journal of Educational Psychology*, 95(2), 405–420.
  https://doi.org/10.1111/bjep.12725
  231 university students reported daily study time and strategies over 30
  days. Effective strategies can compensate for fewer study hours; time and
  quality should not be treated as equivalent.
- **Aeon, Faber & Panaccio (2021)**, *Does time management work? A meta-analysis*,
  *PLOS ONE*. https://doi.org/10.1371/journal.pone.0245066
  Time management correlates with achievement and well-being, but much evidence
  is correlational.
- **Oreopoulos & Petronijevic (2019)**, *Goal Setting, Academic Reminders, and
  College Success: A Large-Scale Field Experiment*,
  *Journal of Research on Educational Effectiveness*, 12(1), 38–66.
  https://doi.org/10.1080/19345747.2018.1517849
  A randomized field study found no evidence that goal-setting/reminder
  interventions improved credits, GPA, or persistence. More planning is not
  intrinsically successful.

**Design boundaries:** Weekly budget entries are optional, per user and week;
existing subject default goals can be copied into a week deliberately, but no
time budget is forced or automatically carried over. Historical time tracking
and completion states are unchanged. The time display is descriptive: the app
does not award points, punish missed budgets, or equate hitting a time target
with having learned a subject. Per-subject time is assigned to the local
week in which each focus session started, consistent with the existing weekly
summary; sessions crossing Sunday midnight are not split.

## New workflow decisions (November 2026)

| Feature | Design | Scientific rationale | Important limitation |
|---|---|---|---|
| **Optional weekly planner** | Select 0–3 weekly outcomes and assign tasks to each day; no forced calendar commitments | Weekly planning field research, specific plans, and lowering unfinished-work rumination [1,2,3] | Weekly planning itself can consume time; the seven-day board UI has not been experimentally validated |
| **Reusable lecture timetable** | Enter lecture once (subject, weekday, start/end, timezone, date range); render occurrences | Reduce repetitive manual capture and external-memory burden; design/ergonomics choice supported indirectly by cognitive offloading research [4] | Repeating timetable data itself has no demonstrated productivity effect in this exact context |
| **In-app lecture attendance check** | After scheduled end, show an unobtrusive prompt when app is opened; user explicitly selects attended, missed, excused | External cues and progress/self-monitoring [4,5] | No evidence that attendance questions alone increase actual attendance; avoid surveillance and unearned 'completed' credit |
| **Prominent accomplishments** | Separate Done page, showing meaningful outcomes rather than reward points; avoid counting parent and child twice | Experimental goal-progress monitoring and motivation framed around completed vs missing progress [5,6] | Highlighting completed work is not always more motivating. Goal commitment and task difficulty matter [6,7] |
| **Finish in Focus** | Atomically stop/save timer and complete linked task; distinguish from simply saving a session or discarding the timer | Reduce interaction friction; give truthful completion feedback and next step [5,8] | No direct trial of this specific button or recommendation algorithm |
| **Suggested next task** | Offer one deterministic suggestion based on *user-chosen* day and week priorities; require explicit click to start | Concrete next actions, goal pursuit and reducing ambiguity [2,3,8] | This is a user-interface hypothesis; never auto-start, force, or claim it is the objectively best task |

## Earlier features retained

- **Daily Top 3 and next action**: concrete goals and actionable plans. A small fixed number is a heuristic, not a proven optimum [2,3,5].
- **Time Budget**: forecasting mistakes motivate use of explicit estimates and review; human planning fallacy evidence is not proof that a capacity progress bar is effective [9].
- **Ready to Resume**: empirical work suggests short re-entry plans mitigate some attention-residue effects [10].
- **Weekly review**: benefits of planning and monitoring with limited burden, not a mandatory journaling habit [1,5].
- **Focus Mode**: removes StudyTracker's own distracting controls; external interruptions and OS/app monitoring are **out of scope** [10,11].

## Research and design guidance

1. **Uhlig et al. (2023)**. *A field experiment on the effects of weekly planning behaviour on work engagement, unfinished tasks, rumination, and cognitive flexibility*. Journal of Occupational and Organizational Psychology. https://doi.org/10.1111/joop.12430 — Field experiment, N=208; planning reduced unfinished tasks and rumination; no significant benefit to work engagement.
2. **Gollwitzer & Sheeran (2006)**. *Implementation intentions and goal achievement: A meta-analysis of effects and processes*. Advances in Experimental Social Psychology. https://doi.org/10.1016/S0065-2601(06)38002-1 — Evidence for specifying when/how actions happen; no proof of a particular calendar layout.
3. **Masicampo & Baumeister (2011)**. *Consider it done! Plan making can eliminate the cognitive effects of unfulfilled goals*. Journal of Personality and Social Psychology. https://pubmed.ncbi.nlm.nih.gov/21688924/ — Plans can reduce intrusive thoughts about unfinished intentions.
4. **Gilbert (2015)**. *Strategic offloading of delayed intentions into the external environment*. Quarterly Journal of Experimental Psychology. https://pubmed.ncbi.nlm.nih.gov/25404057/ — Reminder strategies support delayed intentions; lecture scheduling is not equivalent to tested reminder interventions.
5. **Harkin et al. (2016)**. *Does monitoring goal progress promote goal attainment? A meta-analysis of the experimental evidence*. Psychological Bulletin. https://doi.org/10.1037/bul0000025 — Monitoring goal progress can aid attainment; avoid confusing logging activity with making progress.
6. **Koo & Fishbach (2008)**. *Dynamics of self-regulation: How (un)accomplished goal actions affect motivation*. Journal of Personality and Social Psychology. https://pubmed.ncbi.nlm.nih.gov/18211171/ — The motivational effect of showing done vs remaining work depends on context and goal commitment.
7. **Kluger & DeNisi (1996)**. *The effects of feedback interventions on performance: A historical review, a meta-analysis, and a preliminary feedback intervention theory*. Psychological Bulletin. https://doi.org/10.1037/0033-2909.119.2.254 — Feedback improves performance on average, but a substantial minority of interventions reduce it.
8. **Locke & Latham (2002)**. *Building a practically useful theory of goal setting and task motivation*. American Psychologist. https://doi.org/10.1037/0003-066X.57.9.705 — Importance of specific goals, appropriate difficulty, and feedback; not an endorsement of automated task ranking.
9. **Buehler, Griffin & Ross (1994)**. *Exploring the planning fallacy: Why people underestimate their task completion times*. Journal of Personality and Social Psychology. https://doi.org/10.1037/0022-3514.67.3.366 — Supports estimation calibration rather than blind belief in initial estimates.
10. **Leroy & Glomb (2018)**. *Tasks interrupted ... ready-to-resume plan mitigates the effects*. Organization Science. https://doi.org/10.1287/orsc.2017.1184 — Attention residue from interruptions and mitigating re-entry plans.
11. **Rubinstein, Meyer & Evans (2001)**. *Executive control of cognitive processes in task switching*. Journal of Experimental Psychology: Human Perception and Performance. https://pubmed.ncbi.nlm.nih.gov/11518143/ — Switching tasks imposes measurable cognitive costs.
12. **Aeon, Faber & Panaccio (2021)**. *Does time management work? A meta-analysis*. PLOS ONE. https://pmc.ncbi.nlm.nih.gov/articles/PMC7799745/ — Time-management behavior has associations with performance and well-being; largely noncausal.
13. **Albulescu et al. (2022)**. *Give me a break! A systematic review and meta-analysis on the efficacy of micro-breaks*. PLOS ONE. https://pmc.ncbi.nlm.nih.gov/articles/PMC9432722/ — Breaks can benefit fatigue and vigor; does not justify forced Pomodoro intervals.
14. **Sirois & Pychyl (2013)**. *Procrastination and the priority of short-term mood regulation: Consequences for future self*. Social and Personality Psychology Compass. https://doi.org/10.1111/spc3.12011 — Why purely planning-focused tools may be insufficient for avoidance and aversive tasks.

## Evaluation, privacy and anti-patterns

**Measure outcomes, not points.** A reasonable informal within-person evaluation compares planned high-priority outcomes achieved, time spent managing the app, and the ease of resuming work. These are distinct measures; do **not** collapse them into a definitive productivity score.

**User agency:** no lecture is marked attended automatically, no timer auto-starts, no punishment for missed lectures, no artificial deadlines, no mandatory planning or review, no forced gamification or streaks. Missed/unknown attendance is not a personal failure metric.

**Data:** Weekly plans, lecture rules, explicit attendance decisions and task completion all live in the same per-user local JSON and the existing version-2 backup. Week planning is opt-in, and lecture attendance prompts appear only while StudyTracker is open, on the Week/Today pages. No background OS reminders.

**Trade-off:** Research supports the underlying mechanisms to varying degrees; success of these particular controls is a testable design hypothesis rather than an established clinical or productivity claim.
