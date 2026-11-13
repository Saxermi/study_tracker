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
  return {applySuggestion,parseFeedback,ISSUES,HELP_TYPES,TEXT_LIMITS};
});
