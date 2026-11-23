/* Optional exercise-assessment JSON import. Shared by the UI and Node tests. */
'use strict';
(function (root, factory) {
  const helpers = factory();
  if (typeof module === 'object' && module.exports) module.exports = helpers;
  root.StudyExerciseReview = helpers;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const FIELDS = ['difficulty', 'outcome', 'issue', 'help_total', 'help_chatgpt', 'issues', 'strength', 'weakness', 'skill_gap', 'next_action', 'chatgpt_interventions'];
  const ISSUES = ['concept', 'approach', 'calculation', 'implementation', 'instructions', 'careless', 'time', 'verification'];
  const HELP_TYPES = ['verification','hint','guiding_questions','concept_explanation','approach_selection','step_by_step','debugging','calculation','code_generation','full_solution','error_identification'];
  const TEXT_LIMITS = {strength:200,weakness:200,skill_gap:100,next_action:160};

  /** Merge AI suggestions into the user's assessment. Unknown/null suggestions
   *  never erase an existing value. Explicit human changes always win.
   *  A malformed JSON response raises an error rather than silently saving an
   *  incomplete assessment. Clearing an answer remains a user action (—).
   */
  function applySuggestion(raw, current = {}, manuallyEdited = []) {
    const value = String(raw || '').trim().replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();
    const data = JSON.parse(value);
    if (!data || typeof data !== 'object' || Array.isArray(data)) throw new Error('JSON object expected');
    const protectedFields = new Set(manuallyEdited);
    const updated = {...current};
    for (const key of FIELDS) {
      if (!Object.prototype.hasOwnProperty.call(data, key)) continue;
      const v = data[key];
      // A missing/unknown AI estimate must not erase a manual or saved answer.
      if (v === null || v === '') continue;
      if (['difficulty', 'help_total', 'help_chatgpt'].includes(key)) {
        if (!Number.isInteger(v) || v < (key === 'difficulty' ? 1 : 0) || v > 5)
          throw new Error('Invalid value: ' + key);
      } else if (key === 'outcome') {
        if (!['correct', 'partial', 'incorrect'].includes(v)) throw new Error('Invalid outcome');
      } else if (key === 'issue') {
        if (!ISSUES.includes(v)) throw new Error('Invalid issue');
      } else if (key === 'issues' || key === 'chatgpt_interventions') {
        const allowed = key === 'issues' ? ISSUES : HELP_TYPES;
        if (!Array.isArray(v) || v.length > 3 || new Set(v).size !== v.length || v.some(x=>!allowed.includes(x))) throw new Error('Invalid '+key);
      } else if (Object.prototype.hasOwnProperty.call(TEXT_LIMITS,key)) {
        if (typeof v !== 'string' || v.length > TEXT_LIMITS[key]) throw new Error('Invalid '+key);
      }
      if (!protectedFields.has(key)) updated[key] = v;
    }
    if (updated.issues && updated.issues.length && !updated.issue) updated.issue = updated.issues[0];
    if (updated.issue && updated.issues && updated.issues.length && !updated.issues.includes(updated.issue)) throw new Error('Primary issue must be in issues');
    if (updated.help_total != null && updated.help_chatgpt != null && updated.help_chatgpt > updated.help_total)
      throw new Error('ChatGPT help exceeds total help');
    return updated;
  }

  function parseFeedback(raw){
    const content=String(raw||'').trim().replace(/^\`\`\`(?:json)?\s*/i,'').replace(/\s*\`\`\`$/,'').trim();
    const data=JSON.parse(content);
    if(!data||typeof data!=='object'||Array.isArray(data))throw Error('JSON object expected');
    if(!FIELDS.some(k=>Object.prototype.hasOwnProperty.call(data,k)))throw Error('No recognized assessment fields');
    const validated=applySuggestion(content,{},[]);
    return Object.keys(validated).length?validated:null;
  }

  const PROMPT_RULES = {en:["**Required output:** Return EXACTLY ONE copyable fenced JSON code block (`json`) and no other prose. The contents must parse as one JSON object; when storing a .json file, omit the fences.","**Strict schema (English, case-sensitive keys/values):**","- `difficulty`: JSON INTEGER 1, 2, 3, 4 or 5, or null. 1 = straightforward recall/substitution; 2 = familiar routine problem; 3 = moderate multi-step reasoning; 4 = difficult with non-obvious decisions, proof or substantial debugging; 5 = exceptional unfamiliar synthesis. Rate inherent task demands, not assistance received. Never use strings such as \"high\".","- `outcome`: JSON STRING exactly \"correct\", \"partial\" or \"incorrect\", or null when no checked solution is available.","- `issue`: one PRIMARY JSON STRING from \"concept\", \"approach\", \"calculation\", \"implementation\", \"instructions\", \"careless\", \"time\", \"verification\", or null.","- `issues`: JSON ARRAY of 0–3 UNIQUE strings from the same eight issue codes. If `issue` is set, include it here. Use [] if no observed issues.","- `help_total`: JSON INTEGER 0–5 or null for assistance from ALL sources. `help_chatgpt`: JSON INTEGER 0–5 or null for assistance actually provided by ChatGPT only. If both known, `help_chatgpt` <= `help_total`. If other assistance isn't observable, do NOT automatically assume total help equals ChatGPT help.","- `chatgpt_interventions`: JSON ARRAY of 0–3 UNIQUE strings from \"verification\", \"hint\", \"guiding_questions\", \"concept_explanation\", \"approach_selection\", \"step_by_step\", \"debugging\", \"calculation\", \"code_generation\", \"full_solution\", \"error_identification\". Use [] if none were observed. These describe TYPE, not AMOUNT, of help.","- `strength`: ONE specific, evidenced JSON STRING sentence, up to 200 characters, or null. `weakness`: same, up to 200 characters, or null.","- `skill_gap`: one specific short JSON STRING up to 100 characters, or null. `next_action`: one concrete achievable JSON STRING step up to 160 characters, or null.","- Return ALL ELEVEN exact keys, without additions. Strings use double quotes; integers are unquoted; null is unquoted; arrays use brackets. No comments or trailing commas. No fabricated observations. Unknown scalar -> null, no observed issue/intervention -> [].","**Help rating rubric — calibrate from the ACTUAL conversation (not how long it is):**","0 = No help with the solution. Example: the student solves the exercise without consulting an assistant.","1 = Verification or a very minor clarification. Example: the student already solved it, then asks whether the final result is correct; ChatGPT only checks it. A detailed explanation AFTER solving does not make this 4/5.","2 = One small, directional hint. Example: ChatGPT says \"try induction\" or points to a relevant formula, but the student chooses the method, performs the derivation and completes the work.","3 = Several targeted hints or guiding questions. Example: ChatGPT asks which condition applies and later points out one error; the student still builds the main argument/calculation and reaches the answer.","4 = Major solution assistance BEFORE independent completion. Example: ChatGPT identifies the critical method AND works through essential steps or derivations, while the student finishes a meaningful remaining part.","5 = Near-complete or complete solution supplied by ChatGPT BEFORE the student has solved it. Example: ChatGPT generates the finished proof, code or full worked calculation; the student mainly copies, checks or makes small edits.","**Anti-inflation rules:** Five chat messages do NOT imply 5/5. A long conversation, repeated questions, a concept explanation after successful completion, or simple answer checks do NOT by themselves imply 4 or 5. Assign 4 only with concrete evidence that the assistant supplied essential solution steps, and 5 only for a near-complete delivered solution. When two adjacent scores are plausible, choose the LOWER level supported by explicit evidence; use null if the relevant work is not visible. Distinguish the learner's own reasoning from assistant output. Base `help_total` on observed help from all sources; never invent unseen help.","**Before answering:** Compare the chat to the 0–5 examples; identify the highest substantive help provided BEFORE independent completion. Do not copy scores from the illustrative JSON. Return ONLY the JSON block."],de:["**Verbindliche Ausgabe:** Antworte mit GENAU EINEM kopierbaren JSON-Codeblock (`json`) OHNE Text davor oder danach. Darin steht ein gültiges JSON-Objekt. Als .json-Datei nur den Inhalt ohne Codezäune speichern.","**Exakte JSON-Typen und Werte (Schlüssel und Enum-Codes bleiben Englisch):**","- `difficulty`: JSON-GANZZAHL 1, 2, 3, 4 oder 5, oder null. 1 = direktes Abrufen/Einsetzen; 2 = bekannte Routineaufgabe; 3 = mittelschwer mit mehreren Schritten; 4 = schwierig mit nicht offensichtlichen Entscheidungen, Beweisen oder aufwendigem Debugging; 5 = außergewöhnliche unbekannte Synthese. Schwierigkeit der Aufgabe bewerten, NICHT die erhaltene Hilfe. Keine Strings wie \"high\".","- `outcome`: JSON-STRING exakt \"correct\", \"partial\" oder \"incorrect\", sonst null, wenn eine überprüfte Lösung fehlt.","- `issue`: genau EIN primärer JSON-STRING aus \"concept\", \"approach\", \"calculation\", \"implementation\", \"instructions\", \"careless\", \"time\", \"verification\", oder null.","- `issues`: JSON-LISTE mit 0–3 VERSCHIEDENEN Codes aus denselben acht Problemen. Falls `issue` gesetzt, muss es in `issues` enthalten sein. Sonst [] bei keinen beobachteten Problemen.","- `help_total`: JSON-GANZZAHL 0–5 oder null, für ALLE Hilfsquellen. `help_chatgpt`: JSON-GANZZAHL 0–5 oder null, nur für tatsächlich durch ChatGPT geleistete Hilfe. Wenn beide bekannt, muss `help_chatgpt` <= `help_total` gelten. Unbekannte andere Hilfsquellen NICHT automatisch als null oder ChatGPT-Hilfe bewerten.","- `chatgpt_interventions`: JSON-LISTE mit 0–3 VERSCHIEDENEN Strings aus \"verification\", \"hint\", \"guiding_questions\", \"concept_explanation\", \"approach_selection\", \"step_by_step\", \"debugging\", \"calculation\", \"code_generation\", \"full_solution\", \"error_identification\". Sonst []. Dies sind ARTEN der Hilfe, nicht ihre MENGE.","- `strength`: EIN belegter konkreter Satz als JSON-STRING mit max. 200 Zeichen, sonst null. `weakness`: ebenfalls max. 200 Zeichen oder null.","- `skill_gap`: konkrete Kompetenzlücke als kurzer JSON-STRING mit max. 100 Zeichen oder null. `next_action`: konkreter nächster Übungsschritt als JSON-STRING mit max. 160 Zeichen oder null.","- Genau ALLE ELF Felder ausgeben, keine weiteren Schlüssel. Strings in doppelten Anführungszeichen, Zahlen ohne Anführungszeichen, null ohne Anführungszeichen, Listen in eckigen Klammern. Keine Kommentare/überzählige Kommata; keine Vermutungen. Fehlender Einzelwert = null, unbelegte Listen = [].","**Hilfeskala — anhand des tatsächlichen Gesprächs kalibrieren (NICHT anhand der Chatlänge):**","0 = Keine Hilfe beim Lösen. Beispiel: Die Aufgabe wurde selbstständig ohne Assistent gelöst.","1 = Kontrolle oder winzige Klarstellung. Beispiel: Die eigene Lösung steht bereits fest und ChatGPT prüft nur das Resultat. Eine ausführliche NACHBESPRECHUNG macht daraus keine 4/5.","2 = Ein kleiner richtungsweisender Hinweis. Beispiel: ChatGPT weist auf Induktion oder eine passende Formel hin; der Lernende wählt den Lösungsweg, rechnet und schließt selbstständig ab.","3 = Mehrere gezielte Hinweise/Leitfragen. Beispiel: ChatGPT fragt nach einer Bedingung und macht auf einen Fehler aufmerksam; die wesentlichen Lösungsschritte stammen weiterhin vom Lernenden.","4 = Wesentliche Hilfe VOR dem selbstständigen Abschluss. Beispiel: ChatGPT liefert die entscheidende Methode UND mehrere zentrale Rechen-/Beweisschritte, während der Lernende einen bedeutenden Rest selbst fertigstellt.","5 = Nahezu vollständige oder vollständige Lösung VOR dem eigenen Lösungsversuch. Beispiel: ChatGPT schreibt den gesamten Beweis, Code oder Rechenweg, den der Lernende hauptsächlich übernimmt oder nur leicht korrigiert.","**Gegen Inflation:** Fünf Chat-Nachrichten sind NICHT automatisch 5/5. Viele Rückfragen, lange Gespräche, Konzept-Erklärungen NACH erfolgreicher Lösung und reine Antwortkontrolle sind nicht automatisch 4 oder 5. Für 4 müssen zentrale vom Assistenten gelieferte Lösungsschritte erkennbar sein; für 5 eine nahezu vollständige Lösung. Sind zwei benachbarte Werte möglich, wähle den NIEDRIGEREN durch Belege gestützten Wert; fehlt der Lösungsablauf, null. Eigenständige Schritte von ChatGPT-Beiträgen unterscheiden. Unbekannte externe Hilfen nicht erfinden.","**Vor der Ausgabe:** Gespräch mit den Beispielen 0–5 abgleichen; entscheidende Hilfe VOR der eigenständigen Lösung identifizieren. Werte aus dem JSON-Muster NICHT kopieren. Nur JSON-Codeblock ausgeben."]};
  const PROMPT_EXAMPLES = {en:{"difficulty":3,"outcome":"partial","issue":"approach","issues":["approach"],"help_total":2,"help_chatgpt":2,"chatgpt_interventions":["hint"],"strength":"I set up the equations independently.","weakness":"I needed one hint to choose the next step.","skill_gap":"Choosing the correct transformation","next_action":"Solve a similar step without hints."},de:{"difficulty":3,"outcome":"partial","issue":"approach","issues":["approach"],"help_total":2,"help_chatgpt":2,"chatgpt_interventions":["hint"],"strength":"Ich habe die Gleichungen selbst aufgestellt.","weakness":"Für den nächsten Schritt brauchte ich einen Hinweis.","skill_gap":"Passende Umformung auswählen","next_action":"Eine ähnliche Umformung ohne Hinweise lösen."}};

  function buildReviewPrompt(task, language='en') {
    const de=language==='de',fence=String.fromCharCode(96).repeat(3),lang=de?'de':'en';
    return [
      de?'Bewerte, wie selbstständig ich die Aufgabe gelöst habe. Nutze ausschließlich Belege aus diesem Chat.':'Assess how independently I solved this exercise using only evidence from the conversation.',
      ...PROMPT_RULES[lang],'',
      de?'Beispiel (FIKTIV: Zahlen NICHT übernehmen):':'Example (ILLUSTRATIVE ONLY: DO NOT copy scores):','',
      fence+'json',JSON.stringify(PROMPT_EXAMPLES[lang],null,2),fence,'',
      (de?'Aufgabe: ':'Exercise: ')+(task?.title||'-'),
      (de?'Beschreibung: ':'Description: ')+(task?.description||'-'),
      de?'Aufgabenstellung, eigene Lösung, relevante Chatnachrichten:':'Exercise statement, my work and relevant chat messages:',
      '[ ... ]'
    ].join('\n');
  }

  /** Validate the exact assessment echoed by the server before claiming success.
   * Server normalization can add derived issue lists and normalize empty arrays.
   */
  function matchesPersistedFeedback(expected, saved) {
    if(expected==null)return saved==null;
    if(!saved||typeof saved!=='object')return false;
    return Object.entries(expected).every(([key,value])=>{
      const stored=saved[key];
      if(Array.isArray(value)&&value.length===0)return stored==null||(Array.isArray(stored)&&stored.length===0);
      if(typeof value==='string'&&['strength','weakness','skill_gap','next_action'].includes(key))return value.trim()===(stored||'');
      return JSON.stringify(value)===JSON.stringify(stored);
    });
  }

  return {applySuggestion,parseFeedback,ISSUES,HELP_TYPES,TEXT_LIMITS,buildReviewPrompt,matchesPersistedFeedback};
});
