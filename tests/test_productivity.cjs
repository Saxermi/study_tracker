'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const helpers=require('../static/productivity.js');

test('local day and week use local calendar instead of UTC',()=>{
  assert.equal(helpers.localDay(new Date(2026,10,18,23,59)), '2026-11-18');
  assert.equal(helpers.weekMonday(new Date(2026,10,18)), '2026-11-16');
  assert.equal(helpers.weekMonday(new Date(2026,10,22)), '2026-11-16');
  assert.equal(helpers.weekMonday(new Date(2026,10,23)), '2026-11-23');
});
test('capacity excludes duplicate child estimate when parent is selected',()=>{
  global.taskEstimate=t=>t.planned_minutes;
  const tasks=[{id:'p',planned_minutes:90},{id:'c',parent_id:'p',planned_minutes:30},
               {id:'other',planned_minutes:null}];
  assert.deepEqual(helpers.plannedMinutes(tasks,['p','c','other']),{known:90,unknown:1});
  assert.deepEqual(helpers.plannedMinutes(tasks,['c','other']),{known:30,unknown:1});
  delete global.taskEstimate;
});
test('productivity integration preserves the previous Today and supports start button',()=>{
  const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
  const html=fs.readFileSync(require.resolve('../static/index.html'),'utf8');
  const server=fs.readFileSync(require.resolve('../server.py'),'utf8');
  assert.match(app,/function isTodayPinned\(t\)/,'old Today pins remain supported');
  assert.match(app,/window\.renderProductivity/,'state changes refresh productivity');
  assert.match(app,/next_action:\$\('#f-next-action'\)\.value/,'task editor saves next action');
  assert.match(app,/window\.openProductivityFocus/,'timer opens optional Focus Mode');
  assert.match(html,/\/productivity\.js/);
  assert.match(html,/\/productivity\.css/);
  assert.match(server,/\/productivity\.js/);
  assert.match(server,/\/productivity\.css/);
  const frontend=fs.readFileSync(require.resolve('../static/productivity.js'),'utf8');
  assert.match(frontend,/data-task-start/,'daily priorities have actionable start buttons');
  assert.match(frontend,/data-productivity-timer-action/,'focus overlay has timer controls');
});
test('new script compiles independently in a browser-like context',()=>{
  const code=fs.readFileSync(require.resolve('../static/productivity.js'),'utf8');
  const sandbox={window:{},document:{},module:undefined};
  vm.runInNewContext(code,sandbox);
  for(const name of ['renderProductivity','updateProductivityClock','openProductivityFocus','closeProductivityFocus']){
    assert.equal(typeof sandbox.window[name],'function');
  }
});
