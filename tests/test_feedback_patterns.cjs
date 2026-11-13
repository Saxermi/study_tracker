'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {summarize}=require('../static/feedback_insights.js');
const now='2026-11-13T12:00:00Z';
const tasks=[
 {title:'Exercise A',subject_id:'math',completed_at:'2026-11-12T08:00:00Z',exercise_review:{issues:['concept','approach'],issue:'concept',skill_gap:'Pivot selection',next_action:'Try an unseen problem.'},exercise_review_gpt:{issues:['verification'],skill_gap:'Check pivots'}},
 {title:'Exercise B',subject_id:'math',completed_at:'2026-11-10T12:00:00Z',exercise_review:{issues:['concept'],issue:'concept',skill_gap:'pivot selection',next_action:'Redo without hints.'}},
 {title:'Exercise C',subject_id:'physics',completed_at:'2026-11-12T12:00:00Z',exercise_review:{issue:'calculation'}},
 {title:'Old problem',subject_id:'math',completed_at:'2026-10-01T10:00:00Z',exercise_review:{issues:['time']}}
];
test('multiple issues counted at most once per exercise, by subject and date',()=>{
 const s=summarize(tasks,{source:'self',subject:'math',range:'7',now});
 assert.equal(s.reviewed,2);assert.deepEqual(s.issues,[{name:'concept',count:2},{name:'approach',count:1}]);
 assert.equal(s.skillGaps[0].count,2);assert.equal(s.nextActions.length,2);
});
test('GPT and self reviews are not double-counted',()=>{
 const s=summarize(tasks,{source:'gpt',subject:'all',range:'all',now});
 assert.equal(s.reviewed,1);assert.deepEqual(s.issues,[{name:'verification',count:1}]);
});
test('time range filters and missing review records',()=>{
 assert.equal(summarize(tasks,{range:'7',now}).reviewed,3);
 assert.equal(summarize(tasks,{range:'today',now}).reviewed,0);
 assert.equal(summarize(tasks,{range:'all',now}).reviewed,4);
});
