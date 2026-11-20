'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const P=require('../static/performance.js'),T=require('../static/time_analysis.js');
const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
const html=fs.readFileSync(require.resolve('../static/index.html'),'utf8');
function fakeTimers(){
 let next=0;const jobs=new Map();
 return {jobs,setTimer(fn,delay){const id=++next;jobs.set(id,{fn,delay});return id},clearTimer:id=>jobs.delete(id),
 delay:()=>[...jobs.values()][0]?.delay,
 async fire(){const [id,job]=jobs.entries().next().value;jobs.delete(id);job.fn();await new Promise(setImmediate)}};
}
test('clock schedules no work while idle, paused, invisible or not displayed',async()=>{
 const f=fakeTimers();let allowed=false,ticks=0;
 const c=P.createClock({shouldRun:()=>allowed,tick:()=>ticks++,setTimer:f.setTimer,clearTimer:f.clearTimer});
 c.sync();assert.equal(f.jobs.size,0);
 allowed=true;c.sync();c.sync();assert.equal(f.jobs.size,1);assert.equal(f.delay(),1000);
 await f.fire();assert.equal(ticks,1);assert.equal(f.jobs.size,1);
 allowed=false;c.sync();assert.equal(f.jobs.size,0);
 allowed=true;c.sync();await f.fire();assert.equal(ticks,2);c.stop();assert.equal(f.jobs.size,0);
});
test('adaptive polling is serialized, pauses when disabled, and refreshes on visibility',async()=>{
 const f=fakeTimers();let visible=true,enabled=true,runs=0,resolve;
 const p=P.createPoller({run:()=>{runs++;return new Promise(r=>{resolve=r})},visible:()=>visible,enabled:()=>enabled,setTimer:f.setTimer,clearTimer:f.clearTimer});
 p.start();assert.equal(f.delay(),15000);await f.fire();assert.equal(runs,1);assert.equal(f.jobs.size,0);
 visible=false;p.visibilityChanged();visible=true;p.visibilityChanged();assert.equal(f.jobs.size,0);
 resolve();await new Promise(setImmediate);assert.equal(f.delay(),0);
 await f.fire();assert.equal(runs,2);visible=false;p.visibilityChanged();resolve();await new Promise(setImmediate);assert.equal(f.delay(),60000);
 visible=true;p.visibilityChanged();assert.equal(f.delay(),0);p.stop();assert.equal(f.jobs.size,0);
 enabled=false;p.start();assert.equal(f.jobs.size,0);
});
test('network error backoff caps at five minutes and resets after success',async()=>{
 const f=fakeTimers();let fail=true;
 const p=P.createPoller({run:async()=>{if(fail)throw Error('offline')},visible:()=>true,setTimer:f.setTimer,clearTimer:f.clearTimer});
 p.start();
 for(const delay of [30000,60000,120000,240000,300000,300000]){await f.fire();assert.equal(f.delay(),delay)}
 fail=false;await f.fire();assert.equal(f.delay(),15000);p.stop();
});
test('completed-window cache reuses immutable profile snapshots, refreshes date and handles future sessions',()=>{
 const now=Date.parse('2026-11-20T13:00:00+01:00'),from=Date.parse('2026-11-20T00:00:00+01:00');
 let reads=0;const saved={get started_at(){reads++;return '2026-11-20T10:00:00+01:00'},duration_seconds:600,breaks:[]};
 const future={started_at:'2026-11-20T14:00:00+01:00',duration_seconds:3600,breaks:[]};
 const rows=[saved,future],sum=xs=>xs.reduce((n,s)=>n+s.duration_seconds,0);
 assert.equal(sum(T.completedInWindow(rows,from,now)),600);const initial=reads;
 assert.equal(sum(T.completedInWindow(rows,from,now+60000)),600);assert.equal(reads,initial);
 assert.equal(sum(T.completedInWindow(rows,from,now+90*60000)),2400);assert.equal(reads,initial);
 assert.equal(T.completedCandidates(rows,from,now).length,2);
 assert.equal(sum(T.completedInWindow([...rows],from,now)),600);assert.ok(reads>initial);
 assert.equal(sum(T.completedInWindow(rows,from+86400000,now+86400000)),0);
 // Clock corrections may move the right boundary backwards.
 assert.equal(sum(T.completedInWindow(rows,from,now-4*3600000)),0);
});
test('per-second clock touches only changed clock labels and never calculates statistics',()=>{
 const els=new Map();let writes=0;
 const $=id=>{if(!els.has(id)){let value='';els.set(id,{hidden:true,get textContent(){return value},set textContent(v){value=v;writes++}})}return els.get(id)};
 const c={state:{active_timer:{mode:'focus'}},document:{hidden:false},currentPage:'overview',$,window:{},pad:x=>String(x).padStart(2,'0'),fmt:s=>Math.round(s/60)+' min',timerTime:mode=>mode==='focus'?62:0, setText:(id,v)=>{const el=$(id);if(el.textContent!==v)el.textContent=v}};
 vm.runInNewContext(app.slice(app.indexOf('function focusOverlayVisible('),app.indexOf('function syncClock(')),c);
 c.updateClock();assert.equal(writes,3);c.updateClock();assert.equal(writes,3);
 c.document.hidden=true;c.timerTime=()=>90;c.updateClock();assert.equal(writes,3);
 c.document.hidden=false;c.currentPage='board';c.updateClock();assert.equal(writes,3);
});
test('hidden state updates defer every renderer; opening the tab draws current snapshot',()=>{
 let renders=0,indexes=0;
 const c={state:{},document:{hidden:true},indexedState:null,renderIndex:null,renderPending:false,lastCalendarDay:null,lastUiMinute:null,Date,
 dateKey:()=> '2026-11-20',setText(){},StudyI18n:{locale:()=> 'en-GB'},syncClock(){},buildRenderIndex(){indexes++;return {}},
 renderSide(){},renderSelects(){},renderVisiblePage(){renders++},hydrateIcons(){}};
 vm.runInNewContext(app.slice(app.indexOf('function renderAll(){'),app.indexOf('function renderSide(){')),c);
 c.renderAll();assert.equal(renders,0);assert.equal(indexes,0);assert.equal(c.renderPending,true);
 c.document.hidden=false;c.renderAll();assert.equal(renders,1);assert.equal(indexes,1);assert.equal(c.renderPending,false);
 c.renderAll();assert.equal(indexes,1);
});
test('revision poll skips full fetch when unchanged and discards a stale response after a mutation',async()=>{
 let reqs=[],fullResolve;
 const c={refreshVisibleTime(){},user:{id:'u'},state:{imports:[]},pendingMutations:0,profileEpoch:0,accountEpoch:0,profileRevision:'same',
 AbortController,setTimeout,clearTimeout,document:{hidden:false},renderAll(){},toast(){},api:async(path)=>{reqs.push(path);return {revision:'same'}}};
 vm.runInNewContext(app.slice(app.indexOf('async function pollProfile(){'),app.indexOf('const uiClock=')),c);
 await c.pollProfile();assert.deepEqual(reqs,['/api/profile/revision']);
 c.api=path=>{reqs.push(path);return path.endsWith('/revision')?Promise.resolve({revision:'changed'}):new Promise(r=>{fullResolve=r})};
 const pending=c.pollProfile();await new Promise(setImmediate);c.profileEpoch++;const original=c.state;fullResolve({user:{id:'u'},state:{imports:[{}]},revision:'changed'});await pending;
 assert.equal(c.state,original);
});
test('real app uses the visibility scheduler and hides clock translation changes',()=>{
 assert.doesNotMatch(app,/setInterval\(/);
 assert.match(app,/document\.addEventListener\('visibilitychange'/);
 assert.match(app,/StudyPerformance\.createPoller/);
 assert.match(html,/id="focus-clock" data-no-translate/);
 assert.match(html,/src="\/performance\.js"/);
});
