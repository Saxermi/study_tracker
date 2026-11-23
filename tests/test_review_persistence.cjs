'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const review=require('../static/exercise_review_import.js');
const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
const clip=(from,to)=>{const a=app.indexOf(from),b=app.indexOf(to,a);assert.ok(a>=0&&b>a,from+' missing');return app.slice(a,b)};
const fields=['difficulty','outcome','issue','help_total','help_chatgpt'];
const sample={difficulty:3,outcome:'partial',issue:'approach',issues:['approach'],help_total:2,help_chatgpt:2,chatgpt_interventions:['hint'],strength:'I set up the equations myself.'};
const labels={difficulty:'Difficulty',outcome:'Outcome',issue:'Problem',help_total:'Overall help',help_chatgpt:'ChatGPT help',issues:['Concept','Approach','Calculation','Implementation','Instructions','Careless','Time','Verification']};
function context(saved){
 const raw=saved?JSON.stringify(saved,null,2):'';
 const status={textContent:'',classList:{toggle(){},add(){}}};
 const table={innerHTML:''};
 const elements={'#review-json':{value:raw},'#review-gpt-status':status,'#review-source-comparison':table};
 const ctx={$:s=>elements[s],StudyExerciseReview:review,StudyI18n:{language:'en'},
  REVIEW_FIELDS:fields,REVIEW_ISSUES:review.ISSUES,reviewLang:()=>labels,reviewDraft:{difficulty:2,outcome:'partial',issue:'approach',help_total:1,help_chatgpt:1},
  reviewGptDraft:saved,reviewGptCleared:false,reviewGptOriginalText:raw,reviewSaving:false,editId:'exercise',
  escapeHtml:value=>String(value),document:{querySelectorAll(){return[]}},toast(){},modalClose(){},mutate:async()=>null};
 vm.createContext(ctx);
 vm.runInContext(clip('function gptAssessmentFromDialog(){','function enhanceReviewDialog(task){'),ctx);
 vm.runInContext(clip('async function saveExerciseReview(){','async function handleModalSubmit(e){'),ctx);
 return {ctx,elements,status,table};
}
test('reopening an already saved full GPT review shows persisted numeric ratings, not an unsaved preview',()=>{
 const {ctx,status,table}=context(sample);
 ctx.renderReviewComparison();
 assert.match(status.textContent,/Saved GPT feedback/);
 assert.doesNotMatch(status.textContent,/Unsaved GPT preview/);
 assert.match(table.innerHTML,/3\/5/);
 assert.match(table.innerHTML,/2\/5/);
 const g=ctx.gptAssessmentFromDialog();assert.equal(g.saved,true);
 assert.deepEqual(JSON.parse(JSON.stringify(g.data)),sample);
});
test('GPT edit is identified as a preview until it is saved',()=>{
 const {ctx,status,elements}=context(sample);
 elements['#review-json'].value=JSON.stringify({...sample,help_chatgpt:1,help_total:1});
 ctx.renderReviewComparison();
 assert.match(status.textContent,/Unsaved GPT preview/);
 assert.equal(ctx.gptAssessmentFromDialog().saved,false);
});
test('saved metadata-only GPT feedback remains visible with explicit missing-rating explanation',()=>{
 const {ctx,status,table}=context({chatgpt_interventions:['hint','verification'],strength:'Asked an effective clarifying question.'});
 ctx.renderReviewComparison();
 assert.match(status.textContent,/Saved GPT feedback/);
 assert.match(status.textContent,/No difficulty, outcome, issue or help ratings/);
 assert.match(table.innerHTML,/review-gpt-value/);
});
test('clearing a saved GPT assessment is pending until Save; an unsaved change is not persisted automatically',async()=>{
 const {ctx,status,elements}=context(sample);
 ctx.reviewGptCleared=true;elements['#review-json'].value='';
 ctx.renderReviewComparison();
 assert.match(status.textContent,/will be removed when you save/);
 assert.equal(ctx.gptAssessmentFromDialog().data,null);
 let closed=0,call;
 ctx.mutate=async(path,method,body)=>{call={path,method,body};return {state:{tasks:[{id:'exercise',exercise_review_gpt:null}]}}};
 ctx.modalClose=()=>closed++;
 assert.equal(await ctx.saveExerciseReview(),true);
 assert.equal(closed,1);
 assert.equal(call.path,'/api/tasks/exercise/review');
 assert.equal(call.method,'PATCH');
 assert.equal(call.body.gpt,null);
});
test('server-confirmed GPT rating can be saved, preserving the independent personal rating',async()=>{
 const {ctx,status}=context(null);let closed=0,body;
 ctx.$('#review-json').value=JSON.stringify(sample);
 ctx.mutate=async(path,method,data)=>{body=data;return {state:{tasks:[{id:'exercise',exercise_review:{difficulty:2},exercise_review_gpt:{...sample,weakness:null}}]}}};
 ctx.modalClose=()=>closed++;
 assert.equal(await ctx.saveExerciseReview(),true);
 assert.equal(closed,1);
 assert.equal(body.self.difficulty,2);
 assert.equal(body.gpt.help_chatgpt,2);
});
test('unconfirmed GPT save keeps dialog open and displays an explicit error',async()=>{
 const {ctx,elements}=context(null);let closed=0;
 elements['#review-json'].value=JSON.stringify(sample);
 ctx.mutate=async()=>({state:{tasks:[{id:'exercise',exercise_review_gpt:null}]}});
 ctx.modalClose=()=>closed++;
 assert.equal(await ctx.saveExerciseReview(),false);
 assert.equal(closed,0);
 assert.match(elements['#review-gpt-status'].textContent,/not confirmed/);
});
test('GPT help calibration is non-inflated, bilingual, and numerically valid',()=>{
 for(const lang of ['en','de']){
  const prompt=review.buildReviewPrompt({title:'Sample exercise',description:'Show the working'},lang);
  const scores=[0,1,2,3,4,5];
  for(const score of scores)assert.match(prompt,new RegExp('(?:^|\\n)'+score+' ='),lang+' missing anchored '+score);
  assert.match(prompt,/5\/5/);
  assert.match(prompt,/4\/5/);
  assert.match(prompt,lang==='de'?/NICHT automatisch|NICHT kopieren/:/do NOT by themselves|DO NOT copy/);
  const fenced=[...prompt.matchAll(/NaNjson\n([\s\S]*?)\nNaN/g)];
  assert.equal(fenced.length,1);
  const data=JSON.parse(fenced[0][1]);
  assert.equal(data.help_total,2);
  assert.equal(data.help_chatgpt,2);
  assert.equal(data.difficulty,3);
 }
});
test('saved-check helper handles derived issue lists and optional empty arrays without claiming missing ratings are stored',()=>{
 assert.equal(review.matchesPersistedFeedback(sample,{...sample,weakness:null}),true);
 assert.equal(review.matchesPersistedFeedback({...sample,help_total:4},sample),false);
 assert.equal(review.matchesPersistedFeedback(null,null),true);
 assert.equal(review.matchesPersistedFeedback(null,sample),false);
 assert.equal(review.matchesPersistedFeedback({issues:[]},{issues:null}),true);
});
