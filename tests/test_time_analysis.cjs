'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {focusSpans, accumulate} = require('../static/time_analysis.js');
const iso = s => new Date(s).toISOString();
function session(start, hours, other={}) { return {started_at:iso(start), ended_at:iso(new Date(new Date(start).getTime()+hours*3600000)),duration_seconds:hours*3600,breaks:[],...other}; }

test('recent 24 and 48 hours clip intervals and count the same total accurately',()=>{
 const now=new Date('2026-11-09T15:00:00+01:00').getTime();
 const entries=[session('2026-11-08T15:00:00+01:00',2), session('2026-11-09T10:00:00+01:00',1)];
 const a=accumulate(entries,'24',now),b=accumulate(entries,'48',now);
 assert.equal(a.totalSeconds,3600*3); // Both hours yesterday and one hour today.
 assert.equal(b.totalSeconds,3600*3);
});
test('cross midnight has correct local weekday / hour',()=>{
 const now=new Date('2026-11-10T14:00:00+01:00').getTime();
 const result=accumulate([session('2026-11-06T23:30:00+01:00',2)],'week-total',now);
 assert.equal(result.values[4*24+23],1800);
 assert.equal(result.values[5*24+0],3600);
 assert.equal(result.values[5*24+1],1800);
 assert.equal(result.totalSeconds,7200);
});
test('recurring Friday 08-10 is two hours in a typical week',()=>{
 const now=new Date('2026-11-09T16:00:00+01:00').getTime();
 const sessions=[session('2026-10-30T08:00:00+01:00',2),session('2026-11-06T08:00:00+01:00',2)];
 const result=accumulate(sessions,'week-average',now);
 assert.equal(result.weekCount,2);
 assert.equal(result.values[4*24+8],3600);
 assert.equal(result.values[4*24+9],3600);
});
test('four hours logged between 1 and 2am across four weeks sums to 4h',()=>{
 const now=new Date('2026-11-09T16:00:00+01:00').getTime();
 const starts=['2026-10-14T01:00:00+02:00','2026-10-21T01:00:00+02:00','2026-10-28T01:00:00+01:00','2026-11-04T01:00:00+01:00'];
 const result=accumulate(starts.map(x=>session(x,1)),'week-total',now);
 assert.equal(result.values[2*24+1],4*3600);
 assert.equal(result.totalSeconds,4*3600);
});
test('focus intervals exclude paused periods and breaks',()=>{
 const s={started_at:iso('2026-11-06T08:00:00+01:00'),duration_seconds:3600,
  focus_intervals:[{started_at:iso('2026-11-06T08:00:00+01:00'),ended_at:iso('2026-11-06T08:30:00+01:00')},
    {started_at:iso('2026-11-06T10:00:00+01:00'),ended_at:iso('2026-11-06T10:30:00+01:00')}],
  breaks:[{started_at:iso('2026-11-06T08:30:00+01:00'),ended_at:iso('2026-11-06T09:00:00+01:00')} ]};
 const r=accumulate([s],'week-total',new Date('2026-11-09T16:00:00+01:00').getTime());
 assert.equal(r.values[4*24+8],1800);assert.equal(r.values[4*24+9],0);assert.equal(r.values[4*24+10],1800);
});
test('historical breaks are removed and flagged as estimates',()=>{
 const start='2026-11-06T08:00:00+01:00';const s=session(start,1,{ended_at:iso('2026-11-06T10:00:00+01:00'),breaks:[{started_at:iso('2026-11-06T08:30:00+01:00'),ended_at:iso('2026-11-06T09:30:00+01:00')}]});
 const r=accumulate([s],'week-total',new Date('2026-11-09T16:00:00+01:00').getTime());
 assert.equal(r.totalSeconds,3600);assert.equal(r.estimated,true);assert.equal(r.values[4*24+9],1800);
});
test('today excludes yesterday and includes a cross-midnight focus segment',()=>{
 const now=new Date('2026-11-09T01:30:00+01:00').getTime();
 const result=accumulate([session('2026-11-08T23:30:00+01:00',2)],'today',now);
 assert.equal(result.totalSeconds,5400);
 assert.equal(result.values[0],3600);assert.equal(result.values[1],1800);
});
test('active timer counts only current focus, not time paused',()=>{
 const now=new Date('2026-11-09T15:00:00+01:00').getTime();
 const active={first_started_at:iso('2026-11-09T08:00:00+01:00'),mode:'focus',mode_since:iso('2026-11-09T14:45:00+01:00'),focus_intervals:[{started_at:iso('2026-11-09T08:00:00+01:00'),ended_at:iso('2026-11-09T08:30:00+01:00')}]};
 const result=accumulate([active],'24',now);
 assert.equal(result.totalSeconds,2700);
});
