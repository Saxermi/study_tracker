# ChatGPT prompt: assess one exercise (English)

Copy this prompt into ChatGPT after an exercise, together with the actual exercise, your solution and the relevant chat. ChatGPT cannot reliably assess independence without this evidence. The prompt is also available in the StudyTracker assessment dialog.

> Assess how independently I solved this exercise, using **only** the exercise statement, my own solution and our chat. Do not invent observations, mistakes, or assistance. Use `null` for anything you cannot assess.
>
> Return **one JSON object only** with individually optional fields: `difficulty` (1–5; 1=easy), `outcome` (`correct`, `partial`, `incorrect`), `issue` (`concept`, `approach`, `calculation`, `implementation`, `instructions`, `careless`, `time`, `verification`), `help_total` (0–5), `help_chatgpt` (0–5). `0` means no help; `null` means not assessed. ChatGPT help may not exceed total help when both are known. No prose outside the copyable JSON code block.
>
> If evidence is unavailable, use `null` instead of guessing. I will review the assessment myself before saving.

Example: `{"difficulty": 4, "outcome": "partial", "issue": "approach", "help_total": 3, "help_chatgpt": 2}`

Paste the response into the JSON field in the assessment dialog, choose **Apply ChatGPT response**, review values, and save. All fields are optional. Currently there is **only one assessment per task**, not one per attempt, and no exam or repeat-attempt mode.

**StudyTracker 4.3:** Your JSON will be stored as GPT feedback, distinct from the student's own assessment. Never copy the student's self-rating without independent evidence; use `null` for unsupported values.


**Copyable output format**: Return exactly one fenced `json` code block (```json … ```) with no other text, so the response has a Copy control. Save only its contents (without fences) in a `.json` file.

Optional additional assessment fields: `issues` (up to three distinct codes from `concept`, `approach`, `calculation`, `implementation`, `instructions`, `careless`, `time`, `verification`), `strength` and `weakness` (one specific evidence-based sentence, max 200 characters each), `skill_gap` (max 100), `next_action` (max 160), `chatgpt_interventions` (up to three of `verification`, `hint`, `guiding_questions`, `concept_explanation`, `approach_selection`, `step_by_step`, `debugging`, `calculation`, `code_generation`, `full_solution`, `error_identification`). Never invent observations; unsupported values may be null. `issue` remains the primary issue and must be included in `issues` when both are present.
