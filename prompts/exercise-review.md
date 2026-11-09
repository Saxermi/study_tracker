# ChatGPT prompt: assess one exercise (English)

Copy this prompt into ChatGPT after an exercise, together with the actual exercise, your solution and the relevant chat. ChatGPT cannot reliably assess independence without this evidence. The prompt is also available in the StudyTracker assessment dialog.

> Assess how independently I solved this exercise, using **only** the exercise statement, my own solution and our chat. Do not invent observations, mistakes, or assistance. Use `null` for anything you cannot assess.
>
> Return **one JSON object only** with individually optional fields: `difficulty` (1–5; 1=easy), `outcome` (`correct`, `partial`, `incorrect`), `issue` (`concept`, `approach`, `calculation`, `implementation`, `instructions`, `careless`, `time`, `verification`), `help_total` (0–5), `help_chatgpt` (0–5). `0` means no help; `null` means not assessed. ChatGPT help may not exceed total help when both are known. No explanation or code fences.
>
> If evidence is unavailable, use `null` instead of guessing. I will review the assessment myself before saving.

Example: `{"difficulty": 4, "outcome": "partial", "issue": "approach", "help_total": 3, "help_chatgpt": 2}`

Paste the response into the JSON field in the assessment dialog, choose **Apply ChatGPT response**, review values, and save. All fields are optional. Currently there is **only one assessment per task**, not one per attempt, and no exam or repeat-attempt mode.
