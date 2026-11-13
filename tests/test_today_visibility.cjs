'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
const html=fs.readFileSync(require.resolve('../static/index.html'),'utf8');
const NOW=Date.parse('2026-11-13T20:00:00Z');
class FixedDate extends Date { constructor(...args){super(...(args.length?args:[NOW]))} static now(){return NOW} }
const iso=hours=>new Date(NOW-hours*3600000).toISOString();
function fixture(){return [
 {id:'open-old',title:'Old unfinished exercise',status:'todo',planned_for:'2026-10-01',subject_id:'num'},
 {id:'parent',title:'Selected parent',status:'doing',planned_for:'2026-11-12',subject_id:'num'},
 {id:'child-open',title:'Inherited unfinished child',status:'todo',parent_id:'parent',planned_for:null,subject_id:'num'},
 {id:'done-new',title:'Recently finished task',status:'done',planned_for:'2026-11-12',completed_at:iso(23),subject_id:'num'},
 {id:'done-old',title:'Long-finished task',status:'done',planned_for:'2026-11-12',completed_at:iso(25),subject_id:'num'},
 {id:'done-edge',title:'Exactly 24 hours old',status:'done',planned_for:'2026-11-12',completed_at:iso(24),subject_id:'num'},
 {id:'child-new',title:'Inherited recent child',status:'done',parent_id:'parent',completed_at:iso(23),subject_id:'num'},
 {id:'child-old',title:'Inherited old child',status:'done',parent_id:'parent',completed_at:iso(25),subject_id:'num'},
 {id:'future',title:'Tomorrow',status:'todo',planned_for:'2026-11-14',subject_id:'num'},
 {id:'unknown',title:'Legacy done',status:'done',planned_for:'2026-11-12',completed_at:null,subject_id:'num'}
]}
const helper=app.slice(app.indexOf('function isTodayPinned(t)'),app.indexOf('function todayButton(t)'));
function contextFor(tasks){const byId=new Map(tasks.map(t=>[t.id,t]));const c={Date:FixedDate,dateKey:()=> '2026-11-13',taskById:id=>byId.get(id)};vm.runInNewContext(helper,c);return c;}
test('pins survive midnight; only completions newer than 24h remain visible',()=>{
 const tasks=fixture(),c=contextFor(tasks),groups=c.todayTaskGroups(tasks,NOW);
 assert.deepEqual(Array.from(groups.pending,t=>t.id),['open-old','parent','child-open']);
 assert.deepEqual(Array.from(groups.recentDone,t=>t.id),['done-new','child-new']);
 assert.equal(tasks.length,10,'filter must not delete anything');
 assert.equal(c.isTodayPinned(tasks[4]),true,'preserve pin even when hidden');
 tasks[4].status='todo';
 assert.ok(c.todayTaskGroups(tasks,NOW).pending.some(t=>t.id==='done-old'),'reopening reactivates task');
});
test('Today renders an active list and a separate collapsed, muted completed section',()=>{
 const tasks=fixture(),c=contextFor(tasks),els=new Map();
 const select=id=>{if(!els.has(id))els.set(id,{textContent:'',innerHTML:'',hidden:false});return els.get(id)};
 Object.assign(c,{state:{tasks},StudyI18n:{language:'en'},$:select,renderTodayTotals(){},fmt:s=>s/60+' min',taskEstimate:()=>0,
  taskEstimateText:()=>'',subject:()=>({name:'NumCSE',color:'#123456'}),COLORS:['#123456'],escapeHtml:x=>String(x??''),
  taskParentText:()=>'',reviewSummary:()=>'',todayButton:()=>'',secondsByTask:()=>0,taskSeconds:()=>0,icon:()=>''});
 vm.runInNewContext(app.slice(app.indexOf('function renderToday(){'),app.indexOf('function taskCard(t){')),c);
 c.renderToday();
 const active=select('#today-task-list').innerHTML,done=select('#today-completed-list').innerHTML;
 assert.match(active,/Old unfinished exercise|Inherited unfinished child/);
 assert.doesNotMatch(active,/Recently finished task|Long-finished task/);
 assert.match(done,/Recently finished task/);
 assert.match(done,/Inherited recent child/);
 assert.doesNotMatch(done,/Long-finished task|Inherited old child|Exactly 24 hours old/);
 assert.match(done,/is-recently-completed/);
 assert.equal(select('#today-completed-section').hidden,false);
 assert.match(html,/id="today-completed-section"[^>]*hidden/);
 assert.match(html,/<summary>.*Kürzlich erledigt/);
});
test('week is default subject-chart range, and break seconds are never added to focus',()=>{
 assert.match(html,/<option value="week" selected>Diese Woche<\/option>/);
 const week=[{subject_id:'num',duration_seconds:3600,break_seconds:1800}],old=[{subject_id:'num',duration_seconds:7200,break_seconds:0}];
 const els=new Map(),select=id=>{if(!els.has(id))els.set(id,{value:'week',textContent:'',innerHTML:'',style:{}});return els.get(id)};
 const c={state:{subjects:[{id:'num',name:'NumCSE',color:'#123456'}]},$:select,
  sessionForWeek:()=>week,recentSessions:()=>week.concat(old),todaySessions:()=>[],fmt:s=>s/3600+' h',niceTooltip:x=>x,escapeHtml:x=>String(x)};
 vm.runInNewContext(app.slice(app.indexOf('function periodSessions(period,'),app.indexOf('function totalSeconds(')),c);
 vm.runInNewContext(app.slice(app.indexOf('function renderDistribution(){'),app.indexOf('function renderTodayTotals(){')),c);
 c.renderDistribution();
 assert.equal(select('#donut-total').textContent,'1 h');
 select('#overview-subject-range').value='30';c.renderDistribution();
 assert.equal(select('#donut-total').textContent,'3 h');
});