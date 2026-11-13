'use strict';
const assert=require('node:assert/strict');
const test=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
const W=require('../static/import_wizard.js');
const target={id:'subject-numcse-123',name:'NumCSE',semester_id:'sem-26'};
const parent={id:'task-sheet-42',title:'Exercise Sheet 1',subject_id:target.id,parent_id:null};
function sampleFrom(text){const json=text.match(/## (?:Example|Beispiel)[^\n]*\n```json\n([\s\S]*?)\n```/);assert.ok(json,'must have a complete JSON example');return JSON.parse(json[1]);}

test('seven sources offer separate German and English labels and markdown files',()=>{
 assert.equal(W.sourceKeys.length,7);
 for(const lang of ['en','de']){
  const opts=W.sourceOptions(lang);assert.equal(opts.length,7);assert.equal(new Set(opts.map(o=>o.label)).size,7);
  for(const {id,label} of opts){assert.ok(label.length>3);assert.ok(fs.existsSync(path.join(__dirname,'..','prompts','import',id+(lang==='de'?'.de':'')+'.md')));}
 }
});
test('all source prompts pin the selected existing ID in every task',()=>{
 for(const source of W.sourceKeys)for(const lang of ['de','en']){
  const output=W.build({source,lang,subject:target,semester:{name:'Fall 2026'}});
  const doc=sampleFrom(output);
  assert.equal(doc.format,'studytracker.tasks.v1');
  assert.equal(doc.tasks.length,3);
  assert.ok(doc.tasks.every(t=>t.subject_id===target.id));
  assert.equal(doc.tasks[1].parent_external_id,doc.tasks[0].external_id);
  assert.equal(doc.tasks[2].parent_external_id,doc.tasks[0].external_id);
  assert.ok(output.includes('subject-numcse-123'));
  assert.ok(output.includes('Fall 2026'));
  assert.ok(!doc.tasks.some(t=>Object.hasOwn(t,'parent_id')));
 }
});
test('selected existing task uses parent_id and no new parent',()=>{
 for(const lang of ['en','de']){
  const prompt=W.build({source:'chatgpt',lang,subject:target,parent,semester:{name:'Fall 2026'}});
  const doc=sampleFrom(prompt);
  assert.equal(doc.tasks.length,2);
  assert.ok(doc.tasks.every(t=>t.parent_id===parent.id));
  assert.ok(doc.tasks.every(t=>!('parent_external_id' in t)));
  assert.ok(prompt.includes(parent.title));
 }
});
test('invalid targets are rejected',()=>{
 assert.throws(()=>W.build({source:'email',subject:null}));
 assert.throws(()=>W.build({source:'unknown',subject:target}));
 assert.throws(()=>W.build({source:'email',subject:target,parent:{...parent,subject_id:'other'}}));
 assert.throws(()=>W.build({source:'email',subject:target,parent:{...parent,parent_id:'abc'}}));
});
test('date and estimate invention prohibited, copy-friendly output in both languages',()=>{
 for(const lang of ['de','en']){
  const text=W.build({source:'sheet',lang,subject:target});
  assert.match(text,/batch_id/);assert.match(text,/external_id/);assert.match(text,/parent_external_id/);
  assert.match(text,/null/);assert.ok(text.length>1000);
 }
});
