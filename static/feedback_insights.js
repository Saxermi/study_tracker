/* StudyTracker: lightweight recurring issue/skill summaries (no additional stored data). */
'use strict';
(function(root,factory){
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.StudyFeedbackPatterns=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const allowed=['concept','approach','calculation','implementation','instructions','careless','time','verification'];
 function summarize(tasks,opts={}){
  const source=opts.source==='gpt'?'exercise_review_gpt':'exercise_review';
  const subject=opts.subject||'all',range=opts.range||'all';
  const now=opts.now?new Date(opts.now):new Date(),start=new Date(now);
  if(range==='today')start.setHours(0,0,0,0);
  else if(range!=='all'){const days=Number(range);if(Number.isFinite(days)&&days>=0)start.setTime(now.getTime()-days*86400000)}
  const matches=[],issues=new Map(),gaps=new Map(),actions=[];
  for(const task of tasks||[]){
   if(subject!=='all'&&task.subject_id!==subject)continue;
   if(range!=='all'){const stamp=Date.parse(task.completed_at||task.updated_at||task.created_at||'');if(!Number.isFinite(stamp)||stamp<start.getTime()||stamp>now.getTime())continue}
   const feedback=task[source];
   if(!feedback||typeof feedback!=='object')continue;
   matches.push(task);
   const list=Array.isArray(feedback.issues)&&feedback.issues.length?feedback.issues:(feedback.issue?[feedback.issue]:[]);
   for(const issue of new Set(list)){if(allowed.includes(issue))issues.set(issue,(issues.get(issue)||0)+1)}
   const gap=String(feedback.skill_gap||'').trim().slice(0,100);
   if(gap){const key=gap.toLocaleLowerCase();const found=gaps.get(key);if(found)found.count++;else gaps.set(key,{label:gap,count:1})}
   const action=String(feedback.next_action||'').trim().slice(0,160);
   if(action)actions.push({task:task.title||'',action,date:task.completed_at||task.updated_at||''});
  }
  const top=(m,n)=>[...m].sort((a,b)=>b[1]-a[1]||String(a[0]).localeCompare(String(b[0]))).slice(0,n);
  return {reviewed:matches.length,issues:top(issues,8).map(([name,count])=>({name,count})),skillGaps:[...gaps.values()].sort((a,b)=>b.count-a.count).slice(0,4),nextActions:actions.sort((a,b)=>b.date.localeCompare(a.date)).slice(0,3)};
 }
 return {summarize};
});
(function(){
 if(typeof document==='undefined')return;
 const section=document.querySelector('#page-insights'),table=section?.querySelector('.insights-table-panel');
 if(!section||!table)return;
 const panel=document.createElement('article');
 panel.className='panel feedback-patterns-panel';
 panel.innerHTML='<div class="panel-head"><div><span class="eyebrow" id="feedback-patterns-eyebrow">EXERCISE FEEDBACK</span><h3 id="feedback-patterns-title">Recurring challenges</h3><p class="inside-hint" id="feedback-patterns-desc"></p></div><select class="select-slim" id="feedback-pattern-source"><option value="self">My rating</option><option value="gpt">ChatGPT</option></select></div><div id="feedback-pattern-output"></div>';
 table.before(panel);
 const label={en:{heading:'Recurring exercise challenges',eyebrow:'LEARNING FEEDBACK',description:'Uses the subject and date filters above. Issues are counted once per reviewed exercise.',none:'No assessed exercises match these filters.',issues:'Most frequent issues',gaps:'Specific skill gaps',actions:'Suggested next actions',reviewed:'assessed exercises',self:'My rating',gpt:'ChatGPT'},de:{heading:'Wiederkehrende Schwierigkeiten',eyebrow:'LERNFEEDBACK',description:'Verwendet die Fach- und Zeitfilter oben. Jedes Problem zählt höchstens einmal je bewerteter Übung.',none:'Keine bewerteten Übungen für diese Filter.',issues:'Häufigste Probleme',gaps:'Konkrete Kompetenzlücken',actions:'Vorgeschlagene nächste Schritte',reviewed:'bewertete Übungen',self:'Meine Bewertung',gpt:'ChatGPT'}};
 const issueLabels={en:{concept:'Concept',approach:'Approach',calculation:'Calculation',implementation:'Implementation',instructions:'Instructions',careless:'Careless mistake',time:'Time management',verification:'Verification'},de:{concept:'Konzept',approach:'Lösungsansatz',calculation:'Rechnung',implementation:'Implementierung',instructions:'Aufgabenstellung',careless:'Flüchtigkeitsfehler',time:'Zeitmanagement',verification:'Überprüfung'}};
 function draw(){
  if(!state)return;
  const lg=StudyI18n.language==='en'?'en':'de',l=label[lg];
  document.querySelector('#feedback-patterns-title').textContent=l.heading;
  document.querySelector('#feedback-patterns-eyebrow').textContent=l.eyebrow;
  document.querySelector('#feedback-patterns-desc').textContent=l.description;
  const selector=document.querySelector('#feedback-pattern-source');
  selector.options[0].textContent=l.self;selector.options[1].textContent=l.gpt;
  const subject=document.querySelector('#insights-subject')?.value||'all';
  const range=document.querySelector('#insights-range')?.value||'all';
  const sum=StudyFeedbackPatterns.summarize(state.tasks,{source:selector.value,subject,range});
  const target=document.querySelector('#feedback-pattern-output');
  if(!sum.reviewed){target.innerHTML='<div class="empty">'+escapeHtml(l.none)+'</div>';return}
  const names=issueLabels[lg];
  const issues=sum.issues.map(x=>'<div class="feedback-pattern-row"><span>'+escapeHtml(names[x.name]||x.name)+'</span><div class="feedback-pattern-track"><div style="width:'+(x.count/sum.reviewed*100)+'%"></div></div><strong>'+x.count+'/'+sum.reviewed+'</strong></div>').join('');
  const gaps=sum.skillGaps.map(x=>'<li>'+escapeHtml(x.label)+(x.count>1?' <small>×'+x.count+'</small>':'')+'</li>').join('');
  const actions=sum.nextActions.map(x=>'<li><strong>'+escapeHtml(x.task)+'</strong>: '+escapeHtml(x.action)+'</li>').join('');
  target.innerHTML='<p class="inside-hint">'+sum.reviewed+' '+escapeHtml(l.reviewed)+'</p><div class="feedback-pattern-grid"><div><h4>'+escapeHtml(l.issues)+'</h4>'+(issues||'—')+'</div><div><h4>'+escapeHtml(l.gaps)+'</h4>'+(gaps?'<ul>'+gaps+'</ul>':'—')+'<h4>'+escapeHtml(l.actions)+'</h4>'+(actions?'<ul>'+actions+'</ul>':'—')+'</div></div>';
 }
 const previous=renderInsights;
 renderInsights=function(){previous();draw()};
 document.querySelector('#feedback-pattern-source').addEventListener('change',draw);
 if(typeof state!=='undefined'&&state)draw();
})();
