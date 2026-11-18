'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs');
const planner=require('../static/weekly_planner.js');

test('Monday and week days remain correct across DST in Europe/Zurich',()=>{
  assert.equal(planner.monday('2026-03-29'),'2026-03-23');
  assert.equal(planner.offsetDay('2026-03-28',1),'2026-03-29');
  assert.equal(planner.offsetDay('2026-03-29',1),'2026-03-30');
  assert.deepEqual(planner.datesInWeek('2026-11-16'),[
    '2026-11-16','2026-11-17','2026-11-18','2026-11-19',
    '2026-11-20','2026-11-21','2026-11-22']);
});

test('weekly lecture recurrence respects weekday and start/end dates',()=>{
  const lecture={id:'a',title:'Analysis',weekday:0,start_time:'09:00',end_time:'10:30',
    timezone:'Europe/Zurich',first_date:'2026-11-02',last_date:'2026-11-30',attendance:{}};
  assert.equal(planner.lectureOccurs(lecture,'2026-11-02'),true);
  assert.equal(planner.lectureOccurs(lecture,'2026-11-16'),true);
  assert.equal(planner.lectureOccurs(lecture,'2026-11-17'),false);
  assert.equal(planner.lectureOccurs(lecture,'2026-12-07'),false);
  assert.equal(planner.lectureOccurs(lecture,'2026-10-26'),false);
});

test('attendance is asked only once the lecture has ended in its timezone',()=>{
  const lecture={id:'a',title:'Analysis',weekday:0,start_time:'09:00',end_time:'10:30',
    timezone:'Europe/Zurich',first_date:'2026-11-02',last_date:'2026-11-30',attendance:{}};
  assert.equal(planner.lecturePassed(lecture,'2026-11-16',new Date('2026-11-16T09:00:00Z')),false);
  assert.equal(planner.lecturePassed(lecture,'2026-11-16',new Date('2026-11-16T09:30:00Z')),true);
  assert.equal(planner.lecturePassed(lecture,'2026-11-23',new Date('2026-11-16T17:00:00Z')),false);
  assert.equal(planner.outstandingLectures({lectures:[lecture]},new Date('2026-11-16T12:00:00Z')).length,3);
  lecture.attendance['2026-11-16']='attended';
  assert.equal(planner.outstandingLectures({lectures:[lecture]},new Date('2026-11-16T12:00:00Z')).some(p=>p.day==='2026-11-16'),false);
});

test('weekly pages and focus completion are wired without OS permissions',()=>{
  const app=fs.readFileSync(require.resolve('../static/app.js'),'utf8');
  const html=fs.readFileSync(require.resolve('../static/index.html'),'utf8');
  const focus=fs.readFileSync(require.resolve('../static/productivity.js'),'utf8');
  const server=fs.readFileSync(require.resolve('../server.py'),'utf8');
  assert.match(html,/id="page-week"/);
  assert.match(html,/id="page-done"/);
  assert.match(html,/weekly_planner\.js/);
  assert.match(app,/renderWeeklyPlanner/);
  assert.match(app,/renderAccomplishments/);
  assert.match(focus,/complete_task:true/);
  assert.match(focus,/showNextSuggestion/);
  assert.match(server,/completed_task_id/);
  assert.doesNotMatch(fs.readFileSync(require.resolve('../static/weekly_planner.js'),'utf8'),
    /Notification\.|navigator\.permissions|chrome\.tabs|browser\.tabs/);
});
