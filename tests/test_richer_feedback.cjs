'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const helper=require('../static/exercise_review_import.js'),wizard=require('../static/import_wizard.js');
test('fenced GPT JSON supports multiple issues, concise observations and assistance types',()=>{
 const data={difficulty:3,outcome:'partial',issue:'concept',issues:['concept','approach'],strength:'Correct constraints.',weakness:'Needed pivot help.',skill_gap:'Pivot selection',next_action:'Retry unaided.',chatgpt_interventions:['hint','concept_explanation'],help_total:4,help_chatgpt:4};
 const fence=String.fromCharCode(96).repeat(3);
 assert.deepEqual(helper.parseFeedback(fence+'json\n'+JSON.stringify(data)+'\n'+fence),data);
});
test('invalid issues and oversize observations are rejected',()=>{
 for(const x of [{issues:['concept','concept']},{issues:['concept','approach','time','careless']},{strength:'x'.repeat(201)},{skill_gap:'x'.repeat(101)},{chatgpt_interventions:['invalid']},{issue:'concept',issues:['approach']}])assert.throws(()=>helper.parseFeedback(JSON.stringify(x)));
});
test('unknown GPT fields preserve existing manual ratings',()=>assert.equal(helper.applySuggestion('{"difficulty":null,"weakness":"Needs work"}',{difficulty:2}).difficulty,2));
test('every source provides copyable instructions in both languages',()=>{
 for(const lang of ['de','en'])for(const source of wizard.sourceKeys){const text=wizard.build({lang,source,subject:{id:'subject-1',name:'NumCSE'},parent:null,semester:null});assert.match(text,lang==='de'?/kopierbaren/:/copyable/)}
});


const vm=require('node:vm'),fs=require('node:fs');
test('new review overlay loads in a minimal browser context and requests copyable JSON',()=>{
 const context={
  openTaskReview(){},renderReviewComparison(){},reviewPromptFor(){},
  StudyI18n:{language:'en'},document:{querySelector(){return null},addEventListener(){}},
  escapeHtml(text){return String(text)},reviewLang(){return {issues:['Concept','Approach']}},
  reviewDraft:{},gptAssessmentFromDialog(){return {data:null,error:null}}
 };
 vm.runInNewContext(fs.readFileSync(require.resolve('../static/rich_feedback.js'),'utf8'),context);
 const value=context.reviewPromptFor({title:'Simplex',description:'Find a pivot'});
 assert.match(value,/copyable fenced JSON/);
 assert.match(value,/issues/);
 assert.match(value,/skill_gap/);
 assert.match(value,/chatgpt_interventions/);
});
test('Today selection remains pinned after midnight until explicitly removed',()=>{
 const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
 const source=app.match(/function isTodayPinned\(t\)\{[^}]*\}/)?.[0];
 assert.ok(source,'Today helper exists');
 const context={dateKey(){return '2026-11-13'},Date};
 vm.runInNewContext(source,context);
 assert.equal(context.isTodayPinned({planned_for:'2026-11-12'}),true);
 assert.equal(context.isTodayPinned({planned_for:'2026-11-13'}),true);
 assert.equal(context.isTodayPinned({planned_for:'2026-11-14'}),false);
 assert.equal(context.isTodayPinned({planned_for:null}),false);
});
