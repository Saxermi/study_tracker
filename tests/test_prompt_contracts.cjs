'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const wizard=require('../static/import_wizard.js');
const review=require('../static/exercise_review_import.js');
const ROOT=path.resolve(__dirname,'..');
const get=p=>fs.readFileSync(path.join(ROOT,p),'utf8');
const fence=String.fromCharCode(96).repeat(3);
function jsonBlocks(text) {
  const regex=new RegExp(fence+'json\\n([\\s\\S]*?)\\n'+fence,'g');
  return [...text.matchAll(regex)].map(m=>JSON.parse(m[1]));
}
const reviewKeys=['difficulty','outcome','issue','issues','help_total','help_chatgpt','chatgpt_interventions','strength','weakness','skill_gap','next_action'].sort();
const taskKeys=['format','batch_id','tasks','external_id','title','subject_id','subject','semester','description','planned_minutes','priority','due_date','planned_for','tags','parent_id','parent_external_id'];

function assertReviewExample(text,source){
 const examples=jsonBlocks(text);
 assert.ok(examples.length>0,source+' must include copyable JSON');
 const data=examples[0];
 assert.deepEqual(Object.keys(data).sort(),reviewKeys,source+' must show all 11 JSON keys');
 assert.equal(Number.isInteger(data.difficulty),true,source+' difficulty must be integer');
 assert.ok(data.difficulty>=1&&data.difficulty<=5);
 assert.equal(typeof data.outcome,'string');
 assert.ok(Array.isArray(data.issues));
 assert.ok(Array.isArray(data.chatgpt_interventions));
 assert.deepEqual(review.parseFeedback(JSON.stringify(data)),data,source+' must be importable');
 assert.match(text,/difficulty/);
 assert.match(text,/help_total/);
 assert.match(text,/help_chatgpt/);
 assert.match(text,/chatgpt_interventions/);
 assert.match(text,/strength/);
 assert.match(text,/weakness/);
 assert.match(text,/skill_gap/);
 assert.match(text,/next_action/);
 assert.match(text,/1\s*=/,source+' must explain difficulty level 1');
 assert.match(text,/5\s*=/,source+' must explain difficulty level 5');
}
test('standalone exercise feedback prompts specify types and valid examples in both languages',()=>{
 for(const lang of ['en','de']){
  const source='prompts/exercise-review'+(lang==='de'?'.de':'')+'.md';
  const text=get(source);
  assertReviewExample(text,source);
  assert.match(text,/correct/);
  assert.match(text,/partial/);
  assert.match(text,/incorrect/);
  assert.match(text,/concept/);
  assert.match(text,/approach/);
  assert.match(text,/calculation/);
  assert.match(text,/implementation/);
  assert.match(text,/instructions/);
  assert.match(text,/careless/);
  assert.match(text,/time/);
  assert.match(text,/verification/);
 }
});
test('in-app GPT prompt enforces the same strict 11-field response in both languages',()=>{
 for(const lang of ['en','de']){
  const context={
   openTaskReview(){},renderReviewComparison(){},reviewPromptFor(){},
   StudyI18n:{language:lang},
   document:{querySelector(){return null},addEventListener(){}},
   escapeHtml(v){return String(v)},reviewLang(){return {issues:['Concept']}},
   reviewDraft:{},gptAssessmentFromDialog(){return {data:null,error:null}}
  };
  vm.runInNewContext(get('static/rich_feedback.js'),context);
  const prompt=context.reviewPromptFor({title:'Simplex',description:'Choose a pivot'});
  assertReviewExample(prompt,'in-app '+lang);
  assert.match(prompt,/JSON/);
  assert.match(prompt,/integer|Ganzzahl|GANZZAHL/);
  assert.match(prompt,/null/);
 }
});
test('invalid AI feedback types and enums are rejected rather than accepted as prose',()=>{
 for(const bad of [
  {difficulty:'high'},{difficulty:'medium'},{difficulty:3.5},
  {outcome:'mostly correct'},{issue:'conceptual mistake'},
  {issues:'concept'},{issues:['concept','concept']},
  {help_total:'4'},{help_chatgpt:'a little'},
  {chatgpt_interventions:['helpful explanation']},
  {strength:42},{weakness:'x'.repeat(201)},
  {skill_gap:'x'.repeat(101)},{next_action:'x'.repeat(161)}
 ])assert.throws(()=>review.parseFeedback(JSON.stringify(bad)),undefined,JSON.stringify(bad));
});
test('all 14 static source prompts and both standalone email prompts give complete typed task contracts',()=>{
 const standalone=[
  'prompts/email-to-tasks.md','prompts/email-to-tasks.de.md',
  ...wizard.sourceKeys.flatMap(s=>['prompts/import/'+s+'.md','prompts/import/'+s+'.de.md'])
 ];
 assert.equal(standalone.length,16);
 for(const source of standalone){
  const text=get(source);
  for(const field of taskKeys)assert.ok(text.includes(field),source+' missing '+field);
  assert.match(text,/1.?150/,source+' must define tasks array length');
  assert.match(text,/1(?:[–-]| bis )100000/,source+' must define numeric estimate');
  assert.match(text,/null/);
  assert.match(text,/low/);
  assert.match(text,/normal/);
  assert.match(text,/high/);
  assert.match(text,/YYYY-MM-DD/);
  const examples=jsonBlocks(text);
  assert.ok(examples.length>0,source+' should contain a JSON example');
  const example=examples[examples.length-1];
  assert.equal(example.format,'studytracker.tasks.v1');
  assert.ok(Array.isArray(example.tasks)&&example.tasks.length>0);
  assert.ok(example.tasks.every(t=>typeof t.external_id==='string' && typeof t.title==='string'));
  assert.ok(example.tasks.every(t=>typeof t.subject==='string'||typeof t.subject_id==='string'));
  assert.ok(example.tasks.every(t=>t.planned_minutes==null||Number.isInteger(t.planned_minutes)));
 }
});
test('every live wizard source in both languages emits typed instructions and exact selected IDs',()=>{
 const subject={id:'course-ABC-123',name:'Numerical Optimization'};
 for(const lang of ['en','de'])for(const source of wizard.sourceKeys){
  const text=wizard.build({lang,source,subject});
  const typed=lang==='en'?'## Exact JSON field types':'## Exakte JSON-Feldtypen';
  assert.ok(text.includes(typed),source+' '+lang+' lacks strict schema');
  for(const field of taskKeys)assert.ok(text.includes(field),source+' '+lang+' missing '+field);
  assert.match(text,/1(?:[–-]| bis )100000/);
  assert.match(text,/YYYY-MM-DD/);
  const examples=jsonBlocks(text);
  const obj=examples[examples.length-1];
  assert.equal(obj.format,'studytracker.tasks.v1');
  assert.ok(obj.tasks.every(t=>t.subject_id===subject.id),'wizard example must use exact selected ID');
  assert.ok(obj.tasks.every(t=>t.planned_minutes==null||Number.isInteger(t.planned_minutes)));
  assert.ok(text.includes(subject.id));
 }
});
