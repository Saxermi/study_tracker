'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const StudyTime=require('../static/time_analysis.js'),StudyImportWizard=require('../static/import_wizard.js');
const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
const html=fs.readFileSync(require.resolve('../static/index.html'),'utf8');
const iso=x=>new Date(x).toISOString(),ms=x=>Date.parse(x);
const NOW=ms('2026-11-16T00:40:00+01:00'), m=(day,time)=>iso('2026-11-'+day+'T'+time+':00+01:00');
const session={
 id:'cross',subject_id:'num',started_at:m('15','23:30'),ended_at:m('16','00:20'),
 duration_seconds:2400,break_seconds:600,
 focus_intervals:[{started_at:m('15','23:30'),ended_at:m('15','23:50')},{started_at:m('16','00:00'),ended_at:m('16','00:20')}],
 breaks:[{started_at:m('15','23:50'),ended_at:m('16','00:00')}]
};
const active={
 subject_id:'num',mode:'focus',first_started_at:m('16','00:20'),mode_since:m('16','00:30'),focus_seconds:0,break_seconds:600,
 focus_intervals:[],breaks:[{started_at:m('16','00:20'),ended_at:m('16','00:30')}]
};
const old={...session,id:'old',started_at:m('15','21:00'),ended_at:m('15','21:30'),focus_intervals:[{started_at:m('15','21:00'),ended_at:m('15','21:30')}],breaks:[],break_seconds:0,duration_seconds:1800};
function context(now=NOW, state={sessions:[session,old],active_timer:active,subjects:[{id:'num',name:'NumCSE',color:'#123456'}],settings:{weekly_goal_minutes:60},tasks:[]}){
 class FixedDate extends Date {constructor(...a){super(...(a.length?a:[now]))}static now(){return now}}
 const els=new Map();const $=id=>{if(!els.has(id))els.set(id,{value:'week',style:{},textContent:'',innerHTML:''});return els.get(id)};
 const c={Date:FixedDate,StudyTime,state,$,fmt:s=>s/60+' min',niceTooltip:x=>x,escapeHtml:x=>String(x),lastOverviewMinute:null};
 // Exercise the real dashboard selectors and renderers, not a reimplementation.
 vm.runInNewContext(app.slice(app.indexOf('function sessionsInWindow('),app.indexOf('function sessionCategory(')),c);
 vm.runInNewContext(app.slice(app.indexOf('function weekStart('),app.indexOf('function localTimestamp(')),c);
 vm.runInNewContext(app.slice(app.indexOf('function renderWeekTotals('),app.indexOf('function renderOverview(')),c);
 vm.runInNewContext(app.slice(app.indexOf('function renderDistribution('),app.indexOf('function renderTodayTotals(')),c);
 return c;
}
test('Monday 00:40: Today and This Week include Sunday-crossing focus and a running timer, not breaks',()=>{
 const c=context(),today=c.periodSessions('today'),week=c.periodSessions('week');
 assert.equal(c.totalSeconds(today),1800);
 assert.equal(c.totalSeconds(week),1800);
 assert.equal(c.totalSeconds(week,'break_seconds'),600);
 assert.equal(c.totalSeconds(c.periodSessions('week',false)),1200);
 assert.equal(c.totalSeconds(c.periodSessions('today',false)),1200);
 assert.equal(c.weekStart().toISOString(),'2026-11-15T23:00:00.000Z');
 c.renderWeekTotals();
 assert.equal(c.$('#goal-value').textContent,'30 min');
 assert.equal(c.$('#kpi-week').textContent,'30 min');
 assert.equal(c.$('#kpi-break').textContent,'10 min');
 assert.equal(c.$('#days-week').textContent,'1 Tage');
 const sel=c.$('#overview-subject-range');
 sel.value='today';c.renderDistribution();assert.equal(c.$('#donut-total').textContent,'30 min');
 sel.value='week';c.renderDistribution();assert.equal(c.$('#donut-total').textContent,'30 min');
});
test('stopping a cross-week active timer does not change the focus allocated to this week',()=>{
 const crossing={subject_id:'num',first_started_at:m('15','23:45'),mode:'focus',mode_since:m('15','23:45'),focus_intervals:[],breaks:[]};
 const before=context(NOW,{sessions:[],active_timer:crossing}).sessionForWeek();
 assert.equal(before[0].duration_seconds,2400);
 const after={subject_id:'num',started_at:m('15','23:45'),ended_at:new Date(NOW).toISOString(),duration_seconds:3300,focus_intervals:[{started_at:m('15','23:45'),ended_at:new Date(NOW).toISOString()}],breaks:[]};
 const saved=context(NOW,{sessions:[after],active_timer:null}).sessionForWeek();
 assert.equal(saved[0].duration_seconds,before[0].duration_seconds);
 assert.equal(after.duration_seconds,3300,'stored duration is unchanged');
});
test('local week boundary uses local Monday midnight across DST, and old weeks do not count',()=>{
 const c=context(ms('2026-03-30T00:10:00+02:00'),{sessions:[],active_timer:null});
 assert.equal(c.weekStart().toISOString(),'2026-03-29T22:00:00.000Z');
 const from=ms('2026-11-16T00:00:00+01:00');
 assert.equal(StudyTime.clipSession(old,from,NOW),null);
 const legacy={started_at:m('15','23:30'),ended_at:m('16','00:30'),duration_seconds:2700,break_seconds:900,breaks:[{started_at:m('16','00:00'),ended_at:m('16','00:15')}]};
 const row=StudyTime.clipSession(legacy,from,NOW);
 assert.equal(row.duration_seconds,900);assert.equal(row.break_seconds,900);
 const scalar={started_at:m('16','00:00'),ended_at:m('16','00:30'),duration_seconds:1200,break_seconds:600};
 assert.equal(StudyTime.clipSession(scalar,from,NOW).break_seconds,600);
});
test('paused and active break timers never add elapsed pause to focus',()=>{
 const from=ms('2026-11-16T00:00:00+01:00');
 const base={first_started_at:m('15','23:50'),mode_since:m('16','00:20'),focus_intervals:[{started_at:m('15','23:50'),ended_at:m('16','00:20')}],breaks:[]};
 assert.equal(StudyTime.clipSession({...base,mode:'paused'},from,NOW).duration_seconds,1200);
 const br=StudyTime.clipSession({...base,mode:'break'},from,NOW);
 assert.equal(br.duration_seconds,1200);assert.equal(br.break_seconds,1200);
});
const sample={format:'studytracker.tasks.v1',batch_id:'source-1',tasks:[
 {external_id:'source-1:a',subject_id:'num',parent_id:'existing',title:'Aufgabe A'}]};
const fence=String.fromCharCode(96).repeat(3),raw=JSON.stringify(sample);
test('paste parser accepts raw JSON and exactly one fenced JSON block; preserves IDs and text',()=>{
 for(const str of [raw,'  '+raw+'  ','\uFEFF'+raw,fence+'json\n'+raw+'\n'+fence,fence+'JSON\r\n'+raw+'\r\n'+fence,fence+'\n'+raw+'\n'+fence]){
  assert.deepEqual(StudyImportWizard.parseTaskImport(str),sample);
 }
});
test('paste parser rejects malformed, empty, non-task, multiple-block and oversized input',()=>{
 for(const bad of ['', 'not JSON', '[]', '{}','null',JSON.stringify({...sample,batch_id:''}),JSON.stringify({...sample,tasks:[]}),JSON.stringify({...sample,tasks:Array(151).fill(sample.tasks[0])}),fence+'json\n'+raw+'\n'+fence+'\nextra text',fence+'json\n'+raw+'\n'+fence+'\n'+fence+'json\n'+raw+'\n'+fence,' '.repeat(8*1024*1024)+raw]){
  assert.throws(()=>StudyImportWizard.parseTaskImport(bad));
 }
});
function pasteContext(value,mutate,language='en'){
 const elements={'#agent-paste-json':{value,readOnly:false},'#agent-paste-submit':{disabled:false},'#agent-paste-status':{textContent:'',dataset:{}}};
 const c={$:id=>elements[id],StudyImportWizard,StudyI18n:{language},user:{id:'account'},mutate,toast(){}};
 vm.runInNewContext(app.slice(app.indexOf('async function importPastedTasks('),app.indexOf('async function renderSettings(')),c);
 return {c,elements};
}
test('direct import uses existing task endpoint, clears successful paste and reports duplicate counts',async()=>{
 const {c,elements}=pasteContext(raw,async(path,method,body)=>{
  assert.equal(path,'/api/import/tasks');assert.equal(method,'POST');assert.deepEqual(body,sample);
  return {added:1,skipped:2};
 });
 await c.importPastedTasks();
 assert.equal(elements['#agent-paste-json'].value,'');
 assert.match(elements['#agent-paste-status'].textContent,/1 tasks imported, 2 duplicates skipped/);
 assert.equal(elements['#agent-paste-submit'].disabled,false);
});
test('failed/invalid imports keep the input and do not submit invalid JSON',async()=>{
 let calls=0;
 const {c,elements}=pasteContext(raw,async()=>{calls++;return null},'de');
 await c.importPastedTasks();
 assert.equal(calls,1);assert.equal(elements['#agent-paste-json'].value,raw);
 assert.equal(elements['#agent-paste-status'].dataset.error,'true');
 elements['#agent-paste-json'].value='invalid';
 await c.importPastedTasks();assert.equal(calls,1);assert.equal(elements['#agent-paste-json'].value,'invalid');
});
test('double-click does not submit a second request while importing',async()=>{
 let resolve,calls=0;
 const {c,elements}=pasteContext(raw,()=>{calls++;return new Promise(r=>{resolve=r})});
 const first=c.importPastedTasks();await c.importPastedTasks();
 assert.equal(calls,1);assert.equal(elements['#agent-paste-submit'].disabled,true);
 resolve({added:0,skipped:1});await first;
 assert.equal(elements['#agent-paste-submit'].disabled,false);
 assert.equal(elements['#agent-paste-json'].readOnly,false);
});
test('paste controls are part of the shared import panel and existing upload remains available',()=>{
 assert.match(html,/id="agent-import-panel"[\s\S]*?id="agent-paste-json"/);
 assert.equal((html.match(/id="agent-paste-json"/g)||[]).length,1);
 assert.match(html,/id="import-task-file"/);
 assert.match(app,/\$\('#agent-paste-submit'\)\.addEventListener\('click',importPastedTasks\)/);
 assert.match(app,/renderWeeklyPlanner/);
 assert.match(app,/openProductivityFocus/);
 assert.match(app,/renderAccomplishments/);
});
