'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const {parseFeedback}=require('../static/exercise_review_import.js');
const sample={difficulty:3,outcome:'partial',issue:'concept',help_total:4,help_chatgpt:4};
test('example GPT feedback is validated and remains separate from self assessment',()=>{
 assert.deepEqual(parseFeedback(JSON.stringify(sample)),sample);
});
test('optional fields and zero aid',()=>{
 assert.deepEqual(parseFeedback('{"help_total":0,"help_chatgpt":0}'),{help_total:0,help_chatgpt:0});
 assert.equal(parseFeedback('{"difficulty":null}'),null);
});
test('no silent acceptance of malformed or unknown ratings',()=>{
 for(const v of ['not json','{}','[]','{"unknown":4}','{"difficulty":7}','{"help_total":1,"help_chatgpt":4}'])assert.throws(()=>parseFeedback(v));
});
