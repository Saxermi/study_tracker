#!/usr/bin/env node
'use strict';
// Actual old/new app functions in an isolated DOM-like context (NOT a browser).
// Usage: TZ=Europe/Zurich node scripts/benchmark_frontend.cjs /path/to/baseline [seconds]
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const {performance}=require('node:perf_hooks');
const baseline=process.argv[2];
if(!baseline){console.error('Usage: node scripts/benchmark_frontend.cjs BASELINE_DIRECTORY [simulated_seconds]');process.exit(2)}
const root=path.resolve(__dirname,'..'),ticks=Number(process.argv[3]||60);
if(!Number.isInteger(ticks)||ticks<1||ticks>3600)throw Error('seconds must be 1–3600');
const now=Date.parse('2026-11-20T13:00:00+01:00');
const fmt=s=>Math.round(s/60)+' min',pad=n=>String(n).padStart(2,'0');
function fixture(tasks,sessions,mode){
 const end=now-60000;
 const entries=Array.from({length:sessions},(_,i)=>{
  const b=end-i*2*3600000-1800000,e=b+1800000;
  return {id:'s'+i,subject_id:'num',task_id:'t'+(i%tasks),started_at:new Date(b).toISOString(),
   ended_at:new Date(e).toISOString(),duration_seconds:1800,break_seconds:0,breaks:[],
   focus_intervals:[{started_at:new Date(b).toISOString(),ended_at:new Date(e).toISOString()}]};
 });
 return {tasks:Array.from({length:tasks},(_,i)=>({id:'t'+i,title:'Task '+i,status:'todo',subject_id:'num'})),
  sessions:entries,subjects:[{id:'num',name:'NumCSE',color:'#123456'}],
  active_timer:mode?{mode:'focus',mode_since:new Date(now-120000).toISOString(),focus_seconds:0,break_seconds:0,subject_id:'num',focus_intervals:[],breaks:[]}:null};
}
function measure(dir,label,scenario,tasks,count){
 const app=fs.readFileSync(path.join(dir,'static/app.js'),'utf8');
 const StudyTime=require(path.join(dir,'static/time_analysis.js'));
 const optimized=fs.existsSync(path.join(dir,'static/performance.js'));
 const active=scenario==='active-visible'||scenario==='active-hidden',hidden=scenario==='active-hidden';
 const state=fixture(tasks,count,active);
 const els=new Map();let writes=0,statsCalls=0,clockCalls=0,time=now,clockRunning=false;
 class FixedDate extends Date{constructor(...args){super(...(args.length?args:[time]))}static now(){return time}}
 const $=id=>{
  if(!els.has(id)){let text='',html='';els.set(id,{value:'week',hidden:true,style:{},
   get textContent(){return text},set textContent(v){text=String(v);writes++},
   get innerHTML(){return html},set innerHTML(v){html=String(v);writes++}})}
  return els.get(id)
 };
 const sources=new Map();
 const ctx={state,StudyTime,Date:FixedDate,$,pad,fmt,escapeHtml:x=>String(x),document:{hidden},currentPage:'overview',
  window:{},lastOverviewMinute:Math.floor(now/60000),lastUiMinute:Math.floor(now/60000),lastCalendarDay:'2026-11-20',
  lastTodayVisibilityRefresh:now,lastTimingRefresh:now,renderWeekTotals(){},renderDistribution(){},renderActivity(){},
  setText(id,value){const e=$(id);if(e.textContent!==String(value))e.textContent=value},
  setHTML(id,value){if(sources.get(id)!==value){$(id).innerHTML=value;sources.set(id,value)}}
 };
 ctx.dateKey=d=>d.getFullYear()+'-'+pad(d.getMonth()+1)+'-'+pad(d.getDate());
 const slice=(start,end)=>{const i=app.indexOf(start),j=app.indexOf(end,i);if(i<0||j<0)throw Error('Missing app function '+start);return app.slice(i,j)};
 vm.runInNewContext(slice('function sessionsInWindow(','function sessionCategory('),ctx);
 vm.runInNewContext(slice('function renderTodayTotals(){','function isTodayPinned('),ctx);
 vm.runInNewContext(slice('function timerTime(','async function timerAction('),ctx);
 const totals=ctx.renderTodayTotals;ctx.renderTodayTotals=()=>{statsCalls++;return totals()};
 // Initial page rendering is measured separately. Cache is warmed only here,
 // matching an already-open page; the idle benchmark starts after first load.
 const initialStart=performance.now();ctx.renderTodayTotals();const initialMs=performance.now()-initialStart;
 const initialWrites=writes;writes=0;statsCalls=0;
 const cpu=process.cpuUsage(),heapBefore=process.memoryUsage().heapUsed,start=performance.now();
 for(let i=0;i<ticks;i++){
  time=now+i*1000;
  if(!optimized||(!hidden&&active)){clockCalls++;ctx.updateClock()}
  if(optimized&&!hidden&&active&&i%60===0)ctx.renderTodayTotals();
 }
 const elapsed=performance.now()-start,used=process.cpuUsage(cpu);
 return {version:label,scenario,tasks,sessions:count,simulated_seconds:ticks,initial_ms:+initialMs.toFixed(2),initial_dom_assignments:initialWrites,
  clock_callbacks:clockCalls,statistics_calls:statsCalls,dom_assignments:writes,elapsed_js_ms:+elapsed.toFixed(2),
  cpu_ms:+((used.user+used.system)/1000).toFixed(2),heap_delta_kib:Math.round((process.memoryUsage().heapUsed-heapBefore)/1024)};
}
console.log('FRONTEND_BENCHMARK: actual app callbacks in Node VM, simulated DOM assignments; not browser CPU, not a battery measurement.');
for(const [tasks,sessions] of [[1000,5000],[5000,20000]]){
 for(const scenario of ['idle-visible','active-visible','active-hidden']){
  for(const [dir,label] of [[path.resolve(baseline),'before'],[root,'after']])
   console.log(JSON.stringify(measure(dir,label,scenario,tasks,sessions)));
 }
}
console.log('SCHEDULED_RATES: ideal unchanged-profile steady state; excludes visibility transitions, activity, browser throttling and request runtime');
console.log(JSON.stringify({before:{visible_clock_per_h:3600,hidden_clock_per_h:3600,visible_poll_per_h:720,hidden_poll_per_h:720,one_visible_two_hidden_tabs_poll_per_h:2160},after:{idle_clock_per_h:0,active_visible_clock_per_h:3600,hidden_clock_per_h:0,visible_poll_per_h:240,hidden_poll_per_h:60,one_visible_two_hidden_tabs_poll_per_h:360}}));
