/* Optional exercise-assessment JSON import. Shared by the UI and Node tests. */
'use strict';
(function (root, factory) {
  const helpers = factory();
  if (typeof module === 'object' && module.exports) module.exports = helpers;
  root.StudyExerciseReview = helpers;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const FIELDS = ['difficulty', 'outcome', 'issue', 'help_total', 'help_chatgpt'];
  const ISSUES = ['concept', 'approach', 'calculation', 'implementation', 'instructions', 'careless', 'time', 'verification'];

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
      }
      if (!protectedFields.has(key)) updated[key] = v;
    }
    if (updated.help_total != null && updated.help_chatgpt != null && updated.help_chatgpt > updated.help_total)
      throw new Error('ChatGPT help exceeds total help');
    return updated;
  }

  return {applySuggestion};
});
