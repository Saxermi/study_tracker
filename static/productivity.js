/* Optional execution workflow: daily top three, capacity, focus and weekly review.
   Local-first, no telemetry, and independent from legacy planned_for pins. */
'use strict';
(function () {
  const $p = selector => document.querySelector(selector);
  const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const localDay = value => {
    const d = new Date(value);
    return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  };
  const weekMonday = value => {
    const d = new Date(value);
    d.setHours(12,0,0,0);
    d.setDate(d.getDate()-(d.getDay()+6)%7);
    return localDay(d);
  };
  function plannedMinutes(tasks, ids) {
    const byId = new Map(tasks.map(t=>[t.id,t]));
    const selected = ids.map(id=>byId.get(id)).filter(Boolean);
    // A selected parent already includes its children's estimated effort.
    const unique = selected.filter(t=>!t.parent_id||!ids.includes(t.parent_id));
    let known = 0, unknown = 0;
    for(const t of unique) {
      const n = taskEstimate(t);
      if(n == null) unknown++; else known += n;
    }
    return {known, unknown};
  }
  let draftTask = null, draftNote = '';
  let shellReady = false;
  let displayedDay = null;
  const openTasks = () => (state?.tasks || []).filter(t=>t.status!=='done');
  function ensureShell() {
    if(shellReady) return;
    const today = $p('#page-today');
    if(!today) return;
    const panel = document.createElement('article');
    panel.className = 'panel productivity-plan';
    panel.id = 'productivity-plan';
    panel.innerHTML = `
      <div class="productivity-plan-heading">
        <div><span class="eyebrow">BEWUSST PLANEN</span><h3>Deine drei Tagesprioritäten</h3>
        <p class="inside-hint">Optional, getrennt von den bisherigen „Für heute“-Markierungen. Keine automatische Übernahme am nächsten Tag.</p></div>
        <button type="button" class="btn outline" id="productivity-review-open">Wochenreview</button>
      </div>
      <form id="productivity-plan-form">
        <div id="productivity-priorities" class="productivity-priorities"></div>
        <div class="productivity-budget">
          <label>Heute verfügbare Minuten (optional)
            <input id="productivity-capacity" type="number" min="1" max="1440" step="1" placeholder="z. B. 150">
          </label>
          <div id="productivity-budget-summary" role="status" aria-live="polite"></div>
        </div>
        <div class="productivity-plan-actions">
          <button type="submit" class="btn primary">Tagesplan speichern</button>
          <span id="productivity-plan-progress" class="inside-hint"></span>
        </div>
      </form><div id="productivity-plan-entries" class="productivity-plan-entries"></div>`;
    const anchor = today.querySelector('.today-summary');
    today.insertBefore(panel,anchor);
    const focus = document.createElement('div');
    focus.id = 'productivity-focus-overlay';
    focus.className = 'productivity-focus-overlay';
    focus.hidden = true;
    focus.innerHTML = `<div class="productivity-focus-panel" role="dialog" aria-modal="true" aria-label="Fokusmodus">
      <div class="productivity-focus-header"><span class="eyebrow">FOKUSMODUS</span>
        <button type="button" class="btn outline" id="productivity-focus-exit">Ansicht verlassen</button></div>
      <h2 id="productivity-focus-title">Fokus</h2>
      <p id="productivity-focus-next" class="productivity-focus-next"></p>
      <div id="productivity-focus-clock" class="productivity-focus-clock" aria-label="Fokuszeit">00:00:00</div>
      <p id="productivity-focus-status" class="inside-hint"></p>
      <div id="productivity-focus-actions" class="productivity-focus-actions"></div>
      <label class="productivity-resume-label">Wo weitermachen? (optional)
        <textarea id="productivity-resume-note" maxlength="400" rows="3" placeholder="z. B. Bei Aufgabe B, Randbedingungen überprüfen"></textarea>
      </label><button type="button" class="btn outline" id="productivity-resume-save">Notiz speichern</button>
      <small class="inside-hint">Die Notiz erscheint beim nächsten Start dieser Aufgabe. Die Ansicht kannst du ohne Timer-Stopp verlassen.</small>
    </div>`;
    document.body.appendChild(focus);
    const reopen=document.createElement('button');
    reopen.type='button';
    reopen.id='productivity-focus-reopen';
    reopen.className='btn white';
    reopen.textContent='Fokusansicht';
    reopen.hidden=true;
    $p('.timer-buttons')?.appendChild(reopen);
    reopen.addEventListener('click',openFocus);
    const review = document.createElement('dialog');
    review.id = 'productivity-review-dialog';
    review.className = 'productivity-review-dialog';
    review.innerHTML = `<form id="productivity-review-form" class="productivity-review-form">
       <div class="productivity-plan-heading"><div><span class="eyebrow">WOCHENREVIEW</span><h3>Planung verbessern</h3></div>
       <button type="button" class="btn outline" id="productivity-review-close">Schließen</button></div>
       <p class="inside-hint">Nur bei Bedarf. Keine Pflichtreflexion nach jeder Session.</p>
       <label>Was hat diese Woche funktioniert?<textarea id="productivity-worked" maxlength="1000" rows="2"></textarea></label>
       <label>Welches Hindernis ist aufgetreten?<textarea id="productivity-obstacle" maxlength="1000" rows="2"></textarea></label>
       <label>Was planst du nächste Woche anders?<textarea id="productivity-adjustment" maxlength="1000" rows="2"></textarea></label>
       <label>Wenn-dann-Plan (optional)<textarea id="productivity-if-then" maxlength="400" rows="2" placeholder="Wenn ich feststecke, dann ..."></textarea></label>
       <div class="productivity-plan-actions"><button class="btn primary" type="submit">Review speichern</button></div>
      </form>`;
    document.body.appendChild(review);
    const settings = $p('#page-settings');
    if(settings){
      const option=document.createElement('article');
      option.className='panel productivity-setting';
      option.innerHTML='<label><input id="productivity-focus-enabled" type="checkbox" checked> Fokusmodus beim Timerstart automatisch öffnen</label>';
      settings.appendChild(option);
      option.addEventListener('change',async e=>{
        if(e.target.id!=='productivity-focus-enabled')return;
        const wanted=e.target.checked;
        const r=await mutate('/api/settings','PATCH',{focus_mode_enabled:wanted});
        if(!r)e.target.checked=!wanted;
      });
    }
    $p('#productivity-plan-form').addEventListener('submit', savePlan);
    $p('#productivity-plan-form').addEventListener('input', updateBudget);
    $p('#productivity-review-open').addEventListener('click', openWeeklyReview);
    $p('#productivity-review-close').addEventListener('click', ()=>$p('#productivity-review-dialog').close());
    $p('#productivity-review-form').addEventListener('submit', saveWeeklyReview);
    $p('#productivity-focus-exit').addEventListener('click', closeFocus);
    $p('#productivity-resume-save').addEventListener('click', saveResume);
    $p('#productivity-resume-note').addEventListener('input',e=>{draftNote=e.target.value;});
    $p('#productivity-focus-actions').addEventListener('click',async e=>{
      const button=e.target.closest('[data-productivity-timer-action]');
      if(!button)return;
      const action=button.dataset.productivityTimerAction;
      if(action==='stop' && !(await saveResume(true)))return;
      await timerAction(action);
      renderFocus();
    });
    document.addEventListener('keydown',e=>{
      if(e.key==='Escape' && !$p('#productivity-focus-overlay').hidden)closeFocus();
    });
    shellReady=true;
  }
  function renderProductivity() {
    if(!state)return;
    ensureShell();
    if(!shellReady)return;
    const day = localDay(new Date());
    displayedDay = day;
    const plan = state.productivity?.daily_plans?.[day] || {priority_ids:[],capacity_minutes:null};
    const candidates = openTasks();
    const selected = (plan.priority_ids || []).filter(id=>state.tasks.some(t=>t.id===id));
    const target = $p('#productivity-priorities');
    target.innerHTML = [0,1,2].map((idx)=>{
      const id = selected[idx] || '';
      const options = candidates.concat((id&&!candidates.some(t=>t.id===id))?[state.tasks.find(t=>t.id===id)]:[]).filter(Boolean);
      return '<label>Priorität '+(idx+1)+'<select class="productivity-choice" aria-label="Priorität '+(idx+1)+'"><option value="">Keine Auswahl</option>'+
        options.map(t=>'<option value="'+safe(t.id)+'" '+(id===t.id?'selected':'')+'>'+safe(t.title)+(t.status==='done'?' (erledigt)':'')+'</option>').join('')+
        '</select></label>';
    }).join('');
    $p('#productivity-capacity').value=plan.capacity_minutes??'';
    const finished = selected.filter(id=>state.tasks.find(t=>t.id===id)?.status==='done').length;
    $p('#productivity-plan-progress').textContent=selected.length?finished+' von '+selected.length+' Prioritäten erledigt':'Noch keine Prioritäten ausgewählt';
    $p('#productivity-plan-entries').innerHTML=selected.map(id=>{
      const task=state.tasks.find(t=>t.id===id);
      if(!task)return '';
      return '<div class="productivity-priority-row"><div><strong>'+safe(task.title)+'</strong>'+
        (task.next_action?'<small>→ '+safe(task.next_action)+'</small>':'')+'</div>'+
        (task.status==='done'?'<span class="productivity-done">Erledigt ✓</span>':
          '<button type="button" class="btn outline" data-task-start="'+safe(task.id)+'" '+(state.active_timer?'disabled':'')+'>Start</button>')+'</div>';
    }).join('');
    const opener=$p('#productivity-focus-reopen');
    if(opener)opener.hidden=!state.active_timer;
    const setting=$p('#productivity-focus-enabled');
    if(setting)setting.checked=state.settings?.focus_mode_enabled!==false;
    updateBudget();
    renderFocus();
  }
  function selectedIds() {
    return [...$p('#productivity-priorities').querySelectorAll('select')].map(s=>s.value).filter(Boolean);
  }
  function updateBudget() {
    if(!shellReady||!state)return;
    const ids=selectedIds(),estimate=plannedMinutes(state.tasks,ids),value=$p('#productivity-capacity').value;
    const capacity=value===''?null:Number(value);
    const msg=estimate.known+' Min. geschätzt'+(estimate.unknown?' · '+estimate.unknown+' ohne Schätzung':'');
    const target=$p('#productivity-budget-summary');
    target.textContent=msg+(capacity!=null && Number.isFinite(capacity)?' · Kapazität '+capacity+' Min.':'');
    target.classList.toggle('productivity-overbooked',capacity!=null&&Number.isFinite(capacity)&&estimate.known>capacity);
    if(capacity!=null&&Number.isFinite(capacity)&&estimate.known>capacity)target.textContent+=' · Überplant: '+(estimate.known-capacity)+' Min.';
  }
  async function savePlan(e) {
    e.preventDefault();
    const ids=selectedIds();
    if(new Set(ids).size!==ids.length){toast('Bitte eine Aufgabe nicht mehrfach auswählen.',true);return}
    const raw=$p('#productivity-capacity').value;
    const capacity=raw===''?null:Number(raw);
    const result=await mutate('/api/productivity/daily-plan','PATCH',{
      date:localDay(new Date()),priority_ids:ids,capacity_minutes:capacity});
    if(result)toast('Tagesprioritäten gespeichert.');
  }
  function openWeeklyReview(){
    const monday=weekMonday(new Date());
    const review=state.productivity?.weekly_reviews?.[monday]||{};
    $p('#productivity-review-dialog').dataset.week=monday;
    for(const key of ['worked','obstacle','adjustment','if_then']){
      $p('#productivity-'+(key==='if_then'?'if-then':key)).value=review[key]||'';
    }
    $p('#productivity-review-dialog').showModal();
  }
  async function saveWeeklyReview(e){
    e.preventDefault();
    const body={week_start:$p('#productivity-review-dialog').dataset.week};
    for(const key of ['worked','obstacle','adjustment','if_then'])
      body[key]=$p('#productivity-'+(key==='if_then'?'if-then':key)).value;
    const result=await mutate('/api/productivity/weekly-review','PATCH',body);
    if(result){$p('#productivity-review-dialog').close();toast('Wochenreview gespeichert.');}
  }
  function renderFocus(){
    const overlay=$p('#productivity-focus-overlay');
    if(!overlay||overlay.hidden)return;
    const a=state?.active_timer;
    if(!a){closeFocus();return}
    const task=a.task_id?state.tasks.find(t=>t.id===a.task_id):null;
    if(draftTask!==a.task_id){draftTask=a.task_id;draftNote=task?.resume_note||''}
    $p('#productivity-focus-title').textContent=task?.title||a.title||'Freie Lerneinheit';
    $p('#productivity-focus-next').textContent=task?.next_action?'Nächster Schritt: '+task.next_action:'';
    $p('#productivity-resume-note').value=draftNote;
    $p('#productivity-resume-note').disabled=!task;
    $p('#productivity-resume-save').disabled=!task;
    const actions = a.mode==='focus'?[['pause','Unterbrechen'],['break-start','Pause'],['stop','Session speichern']]:
      a.mode==='break'?[['break-end','Pause beenden'],['stop','Session speichern']]:
      [['resume','Fortsetzen'],['stop','Session speichern']];
    $p('#productivity-focus-actions').innerHTML=actions.map(([action,label])=>
      '<button class="btn '+(action==='stop'?'outline':'primary')+'" type="button" data-productivity-timer-action="'+action+'">'+label+'</button>').join('');
    $p('#productivity-focus-status').textContent={focus:'Fokus läuft',break:'Pause läuft',paused:'Unterbrochen'}[a.mode]||'';
    updateProductivityClock();
  }
  function updateProductivityClock(){
    if(shellReady && state && displayedDay!==localDay(new Date()))renderProductivity();
    const el=$p('#productivity-focus-clock');
    if(!el||$p('#productivity-focus-overlay')?.hidden||!state?.active_timer)return;
    const seconds=timerTime('focus');
    const pad=n=>String(n).padStart(2,'0');
    el.textContent=pad(Math.floor(seconds/3600))+':'+pad(Math.floor(seconds/60)%60)+':'+pad(seconds%60);
  }
  function openFocus(){
    if(!state?.active_timer)return;
    ensureShell();
    $p('#productivity-focus-overlay').hidden=false;
    $p('#productivity-focus-exit').focus();
    renderFocus();
  }
  function closeFocus(){
    const el=$p('#productivity-focus-overlay');
    if(el)el.hidden=true;
    draftTask=null;draftNote='';
  }
  async function saveResume(silent=false){
    const taskId=state?.active_timer?.task_id;
    if(!taskId)return true;
    const existing=state.tasks.find(t=>t.id===taskId);
    if(!existing||existing.resume_note===draftNote)return true;
    const r=await mutate('/api/tasks/'+taskId,'PATCH',{resume_note:draftNote});
    if(r&&!silent)toast('Wiederaufnahme-Notiz gespeichert.');
    return !!r;
  }
  if(typeof window!=='undefined'){
    window.renderProductivity = renderProductivity;
    window.updateProductivityClock = updateProductivityClock;
    window.openProductivityFocus = openFocus;
    window.closeProductivityFocus = closeFocus;
  }
  if(typeof module==='object'&&module.exports)module.exports={localDay,weekMonday,plannedMinutes};
})();