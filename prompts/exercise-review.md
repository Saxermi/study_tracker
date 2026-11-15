# Prompt: ChatGPT exercise assessment with exact JSON output (English)

Copy these instructions and provide the exercise statement, your attempted solution and the relevant chat. Rate only evidence that is actually visible. Unknown values must remain unknown.

## Mandatory output contract

**Required output:** Return precisely ONE copyable fenced JSON code block with language json and NO other text. Pasteable JSON inside must parse as one object. Do not include markdown fences in the JSON file itself.
**Types and exact values (case-sensitive; field names always English):**
- **difficulty:** JSON integer 1, 2, 3, 4, or 5 (never strings such as high/medium/low; never decimals, percentages or 0); use null if you cannot judge.
- **difficulty calibration for the student's current course level:** 1 = straightforward recall/substitution, little reasoning; 2 = standard, familiar method with limited steps; 3 = moderate multi-step work requiring choices or combining known ideas; 4 = difficult task requiring several non-obvious decisions, proof, or substantial debugging; 5 = exceptionally challenging or unfamiliar synthesis requiring sustained independent reasoning. Judge intrinsic task demands, not how much help was received.
- **outcome:** exactly "correct", "partial" or "incorrect" (JSON string), or null. Only assess correctness when the actual solution and evidence are visible.
- **issue:** exactly one primary issue code from concept, approach, calculation, implementation, instructions, careless, time, verification; or null. Never output a natural-language description here.
- **issues:** JSON array of 0–3 UNIQUE strings chosen from the same eight issue codes; [] means none evidenced. If issue is non-null, include it in issues. No fourth entry.
- **help_total:** JSON integer 0–5, or null. This is the level of help from ALL sources, not hours or number of messages.
- **help_chatgpt:** JSON integer 0–5, or null. This is only the ChatGPT portion; if both help numbers are known, help_chatgpt <= help_total.
- **Help scale for both help fields:** 0 = no help, 1 = tiny hint/check, 2 = a little guidance, 3 = several substantive hints or explanations, 4 = major step-by-step assistance, 5 = practically the full method or solution supplied. Do not use words like high or low as JSON values.
- **chatgpt_interventions:** JSON array of 0–3 UNIQUE strings from verification, hint, guiding_questions, concept_explanation, approach_selection, step_by_step, debugging, calculation, code_generation, full_solution, error_identification; [] when none are evidenced. Never use human-readable labels instead of these codes.
- **strength:** one specific evidence-based sentence as a JSON string of MAX 200 characters, or null; **weakness:** likewise max 200 characters, or null.
- **skill_gap:** short specific skill as a JSON string of MAX 100 characters, or null; **next_action:** one concrete practice step as a JSON string of MAX 160 characters, or null.
- Include all 11 keys shown in the example, never rename or add keys. JSON strings have double quotes, null is unquoted, arrays use square brackets; no comments, trailing commas, or explanation outside the fenced code block.
- Never fabricate a strength, weakness, mistake, successful outcome, difficulty or intervention. Missing evidence -> null for a scalar, [] for an issue/intervention list.

## Example: valid, directly copyable JSON

```json
{
  "difficulty": 3,
  "outcome": "partial",
  "issue": "approach",
  "issues": [
    "approach",
    "concept"
  ],
  "help_total": 4,
  "help_chatgpt": 4,
  "chatgpt_interventions": [
    "guiding_questions",
    "concept_explanation"
  ],
  "strength": "I identified the constraints independently.",
  "weakness": "I needed help selecting the pivot variable.",
  "skill_gap": "Choosing simplex pivot variables",
  "next_action": "Solve another pivot-selection problem without hints."
}
```

## Evidence to assess

Exercise statement: [paste here]
Your solution and intermediate reasoning: [paste here]
Relevant chat and feedback: [paste here]

StudyTracker saves the result as a separate ChatGPT assessment; it never silently replaces your own rating. Full chat transcripts and repeated-attempt histories are not stored.
