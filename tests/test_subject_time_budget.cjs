'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const u=require('../static/weekly_planner.js');

test('four focused hours count even if a difficult task remains unfinished',()=>{
  const sessions=[
    {subject_id:'mathe',task_id:'long',started_at:'2026-11-16T09:00:00+01:00',duration_seconds:4*3600,break_seconds:900},
    {subject_id:'info',task_id:'other',started_at:'2026-11-16T13:00:00+01:00',duration_seconds:1800},
    {subject_id:'mathe',started_at:'2026-11-09T10:00:00+01:00',duration_seconds:5400}
  ];
  const seconds=u.subjectFocusSeconds(sessions,'mathe','2026-11-16');
  assert.equal(seconds,4*3600);
  const stats=u.subjectWeekStats([{id:'mathe'},{id:'info'}],sessions,'2026-11-16',{mathe:240,info:120});
  assert.equal(stats.plannedMinutes,360);
  assert.equal(stats.seconds,4*3600+1800);
  assert.equal(stats.rows[0].target,240);
  assert.equal(u.fmtFocus(seconds),'4 h');
});

test('live focus is included once, paused time and breaks are excluded',()=>{
  const sessions=[{subject_id:'mathe',started_at:'2026-11-17T09:00:00+01:00',duration_seconds:1800}];
  const now=new Date('2026-11-18T12:01:00+01:00');
  const active={subject_id:'mathe',first_started_at:'2026-11-18T12:00:00+01:00',focus_seconds:90,mode:'focus',mode_since:'2026-11-18T12:00:00+01:00',break_seconds:700};
  assert.equal(u.subjectFocusSeconds(sessions,'mathe','2026-11-16',active,now),1800+90+60);
  assert.equal(u.subjectFocusSeconds(sessions,'mathe','2026-11-16',{...active,mode:'paused'},now),1800+90);
  assert.equal(u.subjectFocusSeconds(sessions,'mathe','2026-11-23',active,now),0);
});

test('time-budget UI is integrated into weekly planner, Today and Accomplishments',()=>{
  const js=fs.readFileSync(require.resolve('../static/weekly_planner.js'),'utf8');
  const py=fs.readFileSync(require.resolve('../server.py'),'utf8');
  assert.match(js,/weekly-subject-budget-form/);
  assert.match(js,/subject_minutes/);
  assert.match(js,/today-subject-study-time/);
  assert.match(js,/accomplishments-effort/);
  assert.match(py,/subject_minutes/);
  assert.doesNotMatch(js,/Notification\.requestPermission|navigator\.permissions|chrome\.tabs/);
});
