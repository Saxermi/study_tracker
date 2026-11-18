/* Optional weekly scheduling, recurring lectures and meaningful accomplishments.
   Runs entirely in the browser; no OS integration, notifications or background work. */
'use strict';
(function () {
  const $w=s=>document.querySelector(s);
  const h=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const localDate=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  const midday=key=>{const [y,m,d]=key.split('-').map(Number);return new Date(y,m-1,d,12)};
  const offsetDay=(key,n)=>{const d=midday(key);d.setDate(d.getDate()+n);return localDate(d)};
  const monday=day=>{const d=midday(day);d.setDate(d.getDate()-(d.getDay()+6)%7);return localDate(d)};
  const datesInWeek=week=>Array.from({length:7},(_,i)=>offsetDay(week,i));
  const fmtFocus=seconds=>{const m=Math.round(Math.max(0,seconds)/60);return m>=60?Math.floor(m/60)+' h'+(m%60?' '+m%60+' min':''):m+' min'};
  // Same start-week attribution as existing StudyTracker summaries. Pauses excluded.
  function subjectFocusSeconds(sessions,id,week,active=null,now=new Date()){
    const end=offsetDay(week,7);
    const inWeek=start=>{const day=localDate(new Date(start));return day>=week&&day<end};
    let sec=(sessions||[]).reduce((n,s)=>n+(s.subject_id===id&&inWeek(s.started_at)?Math.max(0,Number(s.duration_seconds)||0):0),0);
    if(active?.subject_id===id&&active.first_started_at&&inWeek(active.first_started_at)){
      sec+=Math.max(0,Number(active.focus_seconds)||0);
      if(active.mode==='focus'&&active.mode_since)sec+=Math.max(0,Math.floor((now-new Date(active.mode_since))/1000));
    }
    return sec;
  }
  function subjectWeekStats(subjects,sessions,week,targets={},active=null,now=new Date()){
    const rows=subjects.map(subject=>({subject,target:targets[subject.id]??null,seconds:subjectFocusSeconds(sessions,subject.id,week,active,now)}));
    return {rows,plannedMinutes:rows.reduce((n,r)=>n+(r.target||0),0),seconds:rows.reduce((n,r)=>n+r.seconds,0)};
  }
  const dayLabels=['Mo','Di','Mi','Do','Fr','Sa','So'];
  const dateLabel=day=>midday(day).toLocaleDateString(StudyI18n?.language==='en'?'en-GB':'de-CH',{day:'2-digit',month:'short'});
  function currentAtZone(zone,when=new Date()){
    const parts=new Intl.DateTimeFormat('en-GB',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(when);
    const d=Object.fromEntries(parts.map(p=>[p.type,p.value]));
    return {day:d.year+'-'+d.month+'-'+d.day,clock:d.hour+':'+d.minute};
  }
  function lectureOccurs(lecture,day){
    return day>=lecture.first_date&&(!lecture.last_date||day<=lecture.last_date)&&midday(day).getDay()===(lecture.weekday+1)%7;
  }
  function lecturePassed(lecture,day,when=new Date()){
    if(!lectureOccurs(lecture,day))return false;
    const z=currentAtZone(lecture.timezone,when);
    return z.day>day||(z.day===day&&z.clock>=lecture.end_time);
  }
  function outstandingLectures(productivity,when=new Date(),maxDays=14){
    const pending=[];
    for(const lecture of productivity?.lectures||[]){
      const today=currentAtZone(lecture.timezone,when).day;
      const oldest=offsetDay(today,-maxDays);
      for(let day=oldest;day<=today;day=offsetDay(day,1)){
        if(lecturePassed(lecture,day,when)&&!lecture.attendance?.[day])pending.push({lecture,day});
      }
    }
    pending.sort((a,b)=>b.day.localeCompare(a.day)||a.lecture.start_time.localeCompare(b.lecture.start_time));
    return pending;
  }
  const stateForWeek=(week)=>state?.productivity?.weekly_plans?.[week]||{outcome_ids:[],days:{},subject_minutes:{}};
  let chosenWeek=monday(localDate(new Date()));
  let doneRange='week';
  let lastAttendanceCheck=0;
  const deferredAttendance=new Set();
  function renderWeeklyPlanner(){
    const root=$w('#weekly-planner-root');
    if(!root||!state)return;
    const plan=stateForWeek(chosenWeek);
    const days=datesInWeek(chosenWeek);
    const openTasks=state.tasks.filter(t=>t.status!=='done');
    const taskOptions=openTasks.map(t=>'<option value="'+h(t.id)+'">'+h(t.title)+'</option>').join('');
    const outcomes=(plan.outcome_ids||[]).map(id=>state.tasks.find(t=>t.id===id)).filter(Boolean);
    const lectureOptions=state.subjects.filter(s=>!s.archived).map(x=>'<option value="'+h(x.id)+'">'+h(x.name)+'</option>').join('');
    const lectures=state.productivity?.lectures||[];
    const budget=subjectWeekStats(state.subjects,state.sessions,chosenWeek,plan.subject_minutes||{},state.active_timer);
    const budgetRows=budget.rows.filter(r=>!r.subject.archived||r.target!=null||r.seconds>0);
    const defaultGoals=state.subjects.filter(s=>!s.archived&&s.weekly_goal_minutes);
    root.innerHTML='<section class="panel weekly-header"><div><strong>'+h(dateLabel(days[0]))+' – '+h(dateLabel(days[6]))+'</strong><p class="inside-hint">Du kannst die Wochenplanung jederzeit ignorieren. Vorhandene Heute-Markierungen bleiben unabhängig.</p></div>'+
      '<div class="weekly-nav"><button type="button" class="btn outline" data-week-shift="-7" aria-label="Vorherige Woche">‹</button><button type="button" class="btn outline" data-week-current>Heute</button><button type="button" class="btn outline" data-week-shift="7" aria-label="Nächste Woche">›</button></div></section>'+
      '<div id="weekly-attendance" class="weekly-attendance"></div>'+
      '<section class="panel weekly-subject-budget"><div class="weekly-budget-heading"><div><span class="eyebrow">ZEIT ZUERST PLANEN</span><h3>Lernzeit pro Fach</h3><p class="inside-hint">Plane verfügbare Fokuszeit, nicht zwangsläufig die Zahl erledigter Aufgaben. Auch lange schwierige Aufgaben zählen. Die Planung bleibt optional.</p></div>'+
      '<div class="weekly-budget-total"><strong>'+fmtFocus(budget.seconds)+'</strong><small>investiert · '+fmtFocus(budget.plannedMinutes*60)+' geplant</small></div></div>'+
      '<form id="weekly-subject-budget-form"><div class="weekly-subject-budget-rows">'+budgetRows.map(r=>{
        const target=r.target||0,pct=target?Math.min(100,Math.round(r.seconds/(target*60)*100)):0;
        return '<div class="weekly-subject-budget-row"><div class="weekly-budget-name"><span class="weekly-color-dot" style="background:'+h(r.subject.color)+'"></span><strong>'+h(r.subject.name)+'</strong></div>'+
        '<label>Stunden pro Woche <input type="number" data-subject-budget="'+h(r.subject.id)+'" min="0" max="168" step="0.25" value="'+(target?target/60:'')+'" placeholder="z. B. 4" aria-label="Geplante Stunden für '+h(r.subject.name)+'"></label>'+
        '<div class="weekly-budget-result"><strong>'+fmtFocus(r.seconds)+' investiert</strong><small>'+(target?'von '+fmtFocus(target*60)+' geplant':'Ohne Zeitvorgabe')+'</small>'+
        '<div class="weekly-budget-progress" role="progressbar" aria-label="Zeitbudget '+h(r.subject.name)+'" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+pct+'"><div style="width:'+pct+'%;background:'+h(r.subject.color)+'"></div></div></div></div>';
      }).join('')+'</div><div class="weekly-plan-actions"><button class="btn primary" type="submit">Fachzeitbudget speichern</button>'+
      (defaultGoals.length?'<button class="btn outline" type="button" id="weekly-use-default-goals">Fach-Standardziele übernehmen</button>':'')+
      '<small class="inside-hint">Nur Timer- und Session-Fokuszeit, ohne Pausen. Vorlesungsanwesenheit wird nicht automatisch als Lernzeit gezählt.</small></div></form></section>'+
      '<section class="panel weekly-goals"><h3>Wichtige Wochenziele <small>(max. 3, optional)</small></h3><div class="weekly-goal-items">'+
      (outcomes.map(t=>'<div class="weekly-goal-item"><span class="'+(t.status==='done'?'weekly-finished':'')+'">'+h(t.title)+(t.status==='done'?' ✓':'')+'</span><button class="btn outline" type="button" data-week-goal-remove="'+h(t.id)+'">Entfernen</button></div>').join('')||'<p class="inside-hint">Keine Wochenziele ausgewählt.</p>')+
      '</div><form id="weekly-goal-form" class="weekly-inline"><label>Wochenziel hinzufügen<select id="weekly-goal-task" required><option value="">Aufgabe wählen</option>'+taskOptions+'</select></label><button class="btn primary" type="submit" '+(outcomes.length>=3?'disabled':'')+'>Hinzufügen</button></form></section>'+
      '<div class="weekly-days">'+days.map((day,i)=>{
        const planned=(plan.days?.[day]||[]).map(id=>state.tasks.find(t=>t.id===id)).filter(Boolean);
        const events=lectures.filter(l=>lectureOccurs(l,day)).sort((a,b)=>a.start_time.localeCompare(b.start_time));
        return '<section class="panel weekly-day"><div class="weekly-day-head"><h3>'+dayLabels[i]+' <small>'+h(dateLabel(day))+'</small></h3><span class="inside-hint">'+planned.length+' Aufgaben</span></div>'+
          '<div class="weekly-day-events">'+events.map(l=>'<div class="weekly-lecture"><strong>'+h(l.start_time)+'–'+h(l.end_time)+' · '+h(l.title)+'</strong><small>'+h(state.subjects.find(x=>x.id===l.subject_id)?.name||'')+'</small>'+
          (l.attendance?.[day]?'<span class="weekly-status">'+h(({attended:'Besucht',missed:'Nicht besucht',excused:'Entschuldigt'})[l.attendance[day]])+'</span>':'')+
          (lecturePassed(l,day)?'<details class="weekly-lecture-confirm"><summary>Anwesenheit '+(l.attendance?.[day]?'ändern':'bestätigen')+'</summary><div class="weekly-attendance-actions">'+
          [['attended','Ja'],['missed','Nein'],['excused','Entschuldigt']].map(([status,label])=>'<button type="button" class="btn outline" data-attendance-id="'+h(l.id)+'" data-attendance-day="'+h(day)+'" data-attendance-status="'+status+'">'+label+'</button>').join('')+'</div></details>':'')+'</div>').join('')+
          planned.map(t=>'<div class="weekly-task"><span class="'+(t.status==='done'?'weekly-finished':'')+'">'+h(t.title)+(t.status==='done'?' ✓':'')+'</span><button class="weekly-remove" type="button" data-week-remove="'+h(day)+'" data-week-task="'+h(t.id)+'" title="Aus diesem Tag entfernen">×</button></div>').join('')+'</div>'+
          '<form class="weekly-inline weekly-add-form" data-week-day="'+h(day)+'"><label>Aufgabe planen<select name="task" required><option value="">Aufgabe wählen</option>'+taskOptions+'</select></label><button type="submit" class="btn outline">+</button></form></section>';
      }).join('')+'</div>'+
      '<section class="panel weekly-lecture-settings"><h3>Wiederkehrende Vorlesungen</h3><p class="inside-hint">Einmal eintragen: Die Vorlesung erscheint an jedem passenden Wochentag ab Startdatum. Keine Kalenderberechtigung erforderlich.</p>'+
      '<form id="weekly-lecture-form" class="weekly-lecture-form"><label>Titel<input name="title" maxlength="140" placeholder="Analysis II" required></label>'+
      '<label>Fach<select name="subject_id" required>'+lectureOptions+'</select></label>'+
      '<label>Wochentag<select name="weekday">'+dayLabels.map((d,i)=>'<option value="'+i+'">'+d+'</option>').join('')+'</select></label>'+
      '<label>Beginn<input name="start_time" type="time" value="10:00" required></label><label>Ende<input name="end_time" type="time" value="11:30" required></label>'+
      '<label>Ab<input name="first_date" type="date" value="'+h(chosenWeek)+'" required></label>'+
      '<label>Bis (optional)<input name="last_date" type="date"></label>'+
      '<button type="submit" class="btn primary">Vorlesung speichern</button></form>'+
      '<div class="weekly-lecture-list">'+lectures.map(l=>'<div class="weekly-lecture-row"><div><strong>'+h(l.title)+'</strong><small>'+dayLabels[l.weekday]+' · '+h(l.start_time)+'–'+h(l.end_time)+' · '+h(l.first_date)+(l.last_date?' bis '+h(l.last_date):'')+'</small></div><button class="btn outline" type="button" data-lecture-delete="'+h(l.id)+'">Löschen</button></div>').join('')+'</div></section>';
    renderAttendance();
  }
  function renderAttendance(){
    const pending=outstandingLectures(state?.productivity||{}).filter(p=>!deferredAttendance.has(p.lecture.id+':'+p.day));
    for(const selector of ['#weekly-attendance','#today-lecture-attendance']){
      const el=$w(selector);
      if(!el)continue;
      if(!pending.length){el.innerHTML='';el.hidden=true;continue}
      el.hidden=false;
      const shown=pending.slice(0,3);
      el.innerHTML='<section class="panel weekly-attendance-box"><div><strong>Warst du bei dieser Vorlesung?</strong><p class="inside-hint">Nur im StudyTracker gefragt, wenn du die App öffnest. Nicht automatisch als besucht markieren.</p></div>'+
        shown.map(p=>'<div class="weekly-attendance-row"><div><strong>'+h(p.lecture.title)+'</strong><small>'+h(p.day)+' · '+h(p.lecture.start_time)+'–'+h(p.lecture.end_time)+'</small></div>'+
          '<div class="weekly-attendance-actions">'+[['attended','Ja'],['missed','Nein'],['excused','Entschuldigt']].map(([status,label])=>'<button type="button" class="btn outline" data-attendance-id="'+h(p.lecture.id)+'" data-attendance-day="'+h(p.day)+'" data-attendance-status="'+status+'">'+label+'</button>').join('')+'</div></div>').join('')+
        (pending.length>shown.length?'<small class="inside-hint">'+(pending.length-shown.length)+' weitere unbeantwortete Vorlesungen</small>':'')+
        '<button type="button" class="btn outline" data-attendance-later>Später erinnern</button></section>';
    }
  }
  async function patchWeek(plan){
    const r=await mutate('/api/productivity/weekly-plan','PATCH',{week_start:chosenWeek,...plan});
    if(r)renderWeeklyPlanner();
  }
  function bindWeeklyPlanner(){
    const root=$w('#weekly-planner-root');
    if(!root)return;
    root.addEventListener('click',async e=>{
      const el=e.target.closest('button');if(!el)return;
      if(el.hasAttribute('data-week-shift')){chosenWeek=offsetDay(chosenWeek,Number(el.dataset.weekShift));renderWeeklyPlanner();return}
      if(el.hasAttribute('data-week-current')){chosenWeek=monday(localDate(new Date()));renderWeeklyPlanner();return}
      if(el.hasAttribute('data-week-goal-remove')){
        const plan=structuredClone(stateForWeek(chosenWeek));
        plan.outcome_ids=plan.outcome_ids.filter(id=>id!==el.dataset.weekGoalRemove);
        await patchWeek(plan);return;
      }
      if(el.hasAttribute('data-week-remove')){
        const plan=structuredClone(stateForWeek(chosenWeek)),day=el.dataset.weekRemove;
        plan.days[day]=(plan.days[day]||[]).filter(id=>id!==el.dataset.weekTask);
        await patchWeek(plan);return;
      }
      if(el.hasAttribute('data-lecture-delete')){
        if(!confirm('Diese wiederkehrende Vorlesung und ihre Anwesenheitseinträge löschen?'))return;
        await mutate('/api/productivity/lectures/'+el.dataset.lectureDelete,'DELETE',{});return;
      }
    });
    root.addEventListener('submit',async e=>{
      e.preventDefault();
      const form=e.target;
      if(form.id==='weekly-goal-form'){
        const id=$w('#weekly-goal-task').value;if(!id)return;
        const plan=structuredClone(stateForWeek(chosenWeek));
        if(!plan.outcome_ids.includes(id))plan.outcome_ids.push(id);
        await patchWeek(plan);return;
      }
      if(form.classList.contains('weekly-add-form')){
        const day=form.dataset.weekDay,id=form.elements.task.value;if(!id)return;
        const plan=structuredClone(stateForWeek(chosenWeek));
        plan.days[day]??=[];
        if(!plan.days[day].includes(id))plan.days[day].push(id);
        await patchWeek(plan);return;
      }
      if(form.id==='weekly-lecture-form'){
        const body=Object.fromEntries(new FormData(form).entries());
        body.weekday=Number(body.weekday);
        body.last_date=body.last_date||null;
        body.timezone=Intl.DateTimeFormat().resolvedOptions().timeZone||'UTC';
        const r=await mutate('/api/productivity/lectures','POST',body);
        if(r)toast('Vorlesung wurde als wöchentlicher Termin gespeichert.');
      }
    });
    document.addEventListener('click',async e=>{
      if(e.target.closest('[data-attendance-later]')){
        for(const entry of outstandingLectures(state?.productivity||{}).filter(p=>!deferredAttendance.has(p.lecture.id+':'+p.day)).slice(0,3))
          deferredAttendance.add(entry.lecture.id+':'+entry.day);
        renderAttendance();return;
      }
      const b=e.target.closest('[data-attendance-id]');if(!b)return;
      const result=await mutate('/api/productivity/lectures/'+b.dataset.attendanceId+'/attendance','PATCH',{
        date:b.dataset.attendanceDay,status:b.dataset.attendanceStatus});
      if(result)toast('Vorlesungsanwesenheit gespeichert.');
    });
  }
  function renderAccomplishments(){
    const root=$w('#accomplishments-root');
    if(!root||!state)return;
    const today=localDate(new Date()),week=monday(today);
    const end=doneRange==='week'?week:doneRange==='month'?offsetDay(today,-29):'0000-01-01';
    const completed=state.tasks.filter(t=>t.status==='done'&&t.completed_at&&localDate(new Date(t.completed_at))>=end);
    // Avoid counting a parent and its completed children as separate final outcomes.
    const visible=completed.filter(t=>!t.parent_id||!completed.some(parent=>parent.id===t.parent_id));
    const goals=new Set(state.productivity?.weekly_plans?.[week]?.outcome_ids||[]);
    visible.sort((a,b)=>Number(goals.has(b.id))-Number(goals.has(a.id))||new Date(b.completed_at)-new Date(a.completed_at));
    const subjects=state.subjects;
    const cards=visible.slice(0,80).map(t=>{
      const sub=subjects.find(s=>s.id===t.subject_id);
      const used=secondsByTask(t.id);
      return '<article class="panel accomplishment-card"><div class="accomplishment-check">✓</div><div><strong>'+h(t.title)+'</strong><div class="accomplishment-meta">'+h(sub?.name||'')+' · '+h(localDate(new Date(t.completed_at)))+
        (goals.has(t.id)?' · Wochenziel erreicht':'')+(used>0?' · '+Math.round(used/60)+' min Fokus':'')+'</div></div></article>';
    }).join('');
    root.innerHTML='<section class="panel accomplishments-intro"><div><span class="eyebrow">DEINE ERGEBNISSE</span><h3>'+visible.length+' abgeschlossene Ergebnisse</h3>'+
      '<p class="inside-hint">Abschlüsse werden aus deinen existierenden Aufgaben automatisch übernommen. Erledigte Unteraufgaben zählen nicht zusätzlich, wenn ihre Hauptaufgabe ebenfalls abgeschlossen ist.</p></div>'+
      '<div class="accomplishment-filters">'+[['week','Diese Woche'],['month','30 Tage'],['all','Alle']].map(([key,label])=>'<button type="button" class="btn '+(doneRange===key?'primary':'outline')+'" data-done-range="'+key+'">'+label+'</button>').join('')+'</div></section>'+
      '<div class="accomplishment-list">'+(cards||'<div class="panel today-empty">Noch keine abgeschlossenen Ergebnisse im ausgewählten Zeitraum.</div>')+'</div>';
  }
  function bindAccomplishments(){
    $w('#accomplishments-root')?.addEventListener('click',e=>{
      const el=e.target.closest('[data-done-range]');
      if(!el)return;
      doneRange=el.dataset.doneRange;renderAccomplishments();
    });
  }
  function init(){
    const today=$w('#page-today');
    if(today){
      const node=document.createElement('div');
      node.id='today-lecture-attendance';node.hidden=true;
      today.insertBefore(node,today.querySelector('.today-summary'));
    }
    if(typeof state!=='undefined'&&state)renderAttendance();
    bindWeeklyPlanner();
    bindAccomplishments();
  }
  if(typeof window!=='undefined'){
    window.renderWeeklyPlanner=()=>{if(state&&$w('#weekly-planner-root'))renderWeeklyPlanner();};
    window.renderAccomplishments=()=>{if(state&&$w('#accomplishments-root'))renderAccomplishments();};
    window.renderLectureAttendance=()=>{
      if(!state)return;
      const now=Date.now();
      if(now-lastAttendanceCheck>=60000){lastAttendanceCheck=now;renderAttendance();}
    };
  }
  if(typeof module==='object'&&module.exports)module.exports={localDate,monday,offsetDay,datesInWeek,lectureOccurs,lecturePassed,outstandingLectures};
  if(typeof document!=='undefined')document.addEventListener('DOMContentLoaded',init);
})();