# ChatGPT prompt: calibrated exercise assessment

Use this prompt with the actual exercise, your own attempted work and the relevant chat. Only rate assistance demonstrated in that conversation.

**Required output:** Return EXACTLY ONE copyable fenced JSON code block (`json`) and no other prose. The contents must parse as one JSON object; when storing a .json file, omit the fences.
**Strict schema (English, case-sensitive keys/values):**
- `difficulty`: JSON INTEGER 1, 2, 3, 4 or 5, or null. 1 = straightforward recall/substitution; 2 = familiar routine problem; 3 = moderate multi-step reasoning; 4 = difficult with non-obvious decisions, proof or substantial debugging; 5 = exceptional unfamiliar synthesis. Rate inherent task demands, not assistance received. Never use strings such as "high".
- `outcome`: JSON STRING exactly "correct", "partial" or "incorrect", or null when no checked solution is available.
- `issue`: one PRIMARY JSON STRING from "concept", "approach", "calculation", "implementation", "instructions", "careless", "time", "verification", or null.
- `issues`: JSON ARRAY of 0–3 UNIQUE strings from the same eight issue codes. If `issue` is set, include it here. Use [] if no observed issues.
- `help_total`: JSON INTEGER 0–5 or null for assistance from ALL sources. `help_chatgpt`: JSON INTEGER 0–5 or null for assistance actually provided by ChatGPT only. If both known, `help_chatgpt` <= `help_total`. If other assistance isn't observable, do NOT automatically assume total help equals ChatGPT help.
- `chatgpt_interventions`: JSON ARRAY of 0–3 UNIQUE strings from "verification", "hint", "guiding_questions", "concept_explanation", "approach_selection", "step_by_step", "debugging", "calculation", "code_generation", "full_solution", "error_identification". Use [] if none were observed. These describe TYPE, not AMOUNT, of help.
- `strength`: ONE specific, evidenced JSON STRING sentence, up to 200 characters, or null. `weakness`: same, up to 200 characters, or null.
- `skill_gap`: one specific short JSON STRING up to 100 characters, or null. `next_action`: one concrete achievable JSON STRING step up to 160 characters, or null.
- Return ALL ELEVEN exact keys, without additions. Strings use double quotes; integers are unquoted; null is unquoted; arrays use brackets. No comments or trailing commas. No fabricated observations. Unknown scalar -> null, no observed issue/intervention -> [].
**Help rating rubric — calibrate from the ACTUAL conversation (not how long it is):**
0 = No help with the solution. Example: the student solves the exercise without consulting an assistant.
1 = Verification or a very minor clarification. Example: the student already solved it, then asks whether the final result is correct; ChatGPT only checks it. A detailed explanation AFTER solving does not make this 4/5.
2 = One small, directional hint. Example: ChatGPT says "try induction" or points to a relevant formula, but the student chooses the method, performs the derivation and completes the work.
3 = Several targeted hints or guiding questions. Example: ChatGPT asks which condition applies and later points out one error; the student still builds the main argument/calculation and reaches the answer.
4 = Major solution assistance BEFORE independent completion. Example: ChatGPT identifies the critical method AND works through essential steps or derivations, while the student finishes a meaningful remaining part.
5 = Near-complete or complete solution supplied by ChatGPT BEFORE the student has solved it. Example: ChatGPT generates the finished proof, code or full worked calculation; the student mainly copies, checks or makes small edits.
**Anti-inflation rules:** Five chat messages do NOT imply 5/5. A long conversation, repeated questions, a concept explanation after successful completion, or simple answer checks do NOT by themselves imply 4 or 5. Assign 4 only with concrete evidence that the assistant supplied essential solution steps, and 5 only for a near-complete delivered solution. When two adjacent scores are plausible, choose the LOWER level supported by explicit evidence; use null if the relevant work is not visible. Distinguish the learner's own reasoning from assistant output. Base `help_total` on observed help from all sources; never invent unseen help.
**Before answering:** Compare the chat to the 0–5 examples; identify the highest substantive help provided BEFORE independent completion. Do not copy scores from the illustrative JSON. Return ONLY the JSON block.

## Example (illustrative only – do NOT copy the ratings)

```json
{
  "difficulty": 3,
  "outcome": "partial",
  "issue": "approach",
  "issues": [
    "approach"
  ],
  "help_total": 2,
  "help_chatgpt": 2,
  "chatgpt_interventions": [
    "hint"
  ],
  "strength": "I set up the equations independently.",
  "weakness": "I needed one hint to choose the next step.",
  "skill_gap": "Choosing the correct transformation",
  "next_action": "Solve a similar step without hints."
}
```

## Evidence to assess

Exercise: [paste here]
Own solution and main intermediate steps: [paste here]
Chat history, including when the student completed the solution independently: [paste here]

StudyTracker stores GPT feedback separately from your own rating. Full conversations and multiple attempts are not stored automatically.
