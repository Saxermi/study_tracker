'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {applySuggestion} = require('../static/exercise_review_import.js');

test('pasted ChatGPT response applies a difficulty even if Apply was skipped',()=>{
 assert.deepEqual(applySuggestion('{"difficulty": 4, "outcome":"partial"}',
  {difficulty:null,outcome:null}),{difficulty:4,outcome:'partial'});
});
test('empty or null AI fields cannot erase saved or manually entered ratings',()=>{
 const old={difficulty:2,outcome:'correct',help_total:3,help_chatgpt:0};
 assert.deepEqual(applySuggestion('{"difficulty": null, "outcome":null, "help_total":null}',old),old);
});
test('manual override takes precedence over an AI suggestion',()=>{
 assert.deepEqual(applySuggestion('{"difficulty": 5, "help_total":4}',
  {difficulty:2,help_total:null},new Set(['difficulty'])),{difficulty:2,help_total:4});
});
test('fenced JSON accepted; zero aid remains a real value distinct from null',()=>{
 assert.deepEqual(applySuggestion('```json\n{"difficulty":3, "help_chatgpt":0}\n```',
  {difficulty:null,help_chatgpt:null}),{difficulty:3,help_chatgpt:0});
});
test('invalid or impossible feedback is rejected, not silently saved',()=>{
 for(const raw of ['not JSON','[]','{"difficulty":6}',
  '{"help_total":1,"help_chatgpt":4}','{"outcome":"flawless"}']){
  assert.throws(()=>applySuggestion(raw,{}),undefined,raw);
 }
});
test('unknown AI fields are ignored without overwriting manual values',()=>{
 const old={difficulty:3,issue:null};
 assert.deepEqual(applySuggestion('{"unknown":5}',old),old);
});
