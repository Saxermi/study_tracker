/* Structured, optional feedback, layered on the existing v4.3 review dialog. */
(function(){
'use strict';
const issues=['concept','approach','calculation','implementation','instructions','careless','time','verification'];
const help=['verification','hint','guiding_questions','concept_explanation','approach_selection','step_by_step','debugging','calculation','code_generation','full_solution','error_identification'];
const titles={en:{issues:'Issues (up to 3)',strength:'My strength',weakness:'My weakness',gptHelp:'How ChatGPT helped (up to 3)',skill_gap:'Skill gap',next_action:'Next action',interventions:'ChatGPT help types'},de:{issues:'Probleme (bis zu 3)',strength:'Meine Stärke',weakness:'Meine Schwäche',gptHelp:'ChatGPT-Hilfearten (bis zu 3)',skill_gap:'Kompetenzlücke',next_action:'Nächster Schritt',interventions:'ChatGPT-Hilfearten'}};
const helpTitles={en:['Checked my answer','Small hint','Guiding questions','Explained concept','Suggested approach','Step-by-step guidance','Debugged code','Calculation help','Generated code','Full solution','Identified error'],de:['Antwort geprüft','Kleiner Hinweis','Leitfragen','Konzept erklärt','Ansatz vorgeschlagen','Schrittweise Anleitung','Code debuggt','Rechnung unterstützt','Code erzeugt','Vollständige Lösung','Fehler gefunden']};
const lang=()=>StudyI18n.language==='en'?'en':'de';
const originalOpen=openTaskReview,originalCompare=renderReviewComparison;
function chips(field,codes,labels,values,owner){const chosen=new Set(values||[]);return '<div class="review-multi">'+codes.map((x,i)=>'<button type="button" class="review-multi-chip '+(chosen.has(x)?'selected':'')+'" data-rich-field="'+field+'" data-rich-owner="'+owner+'" data-rich-code="'+x+'" aria-pressed="'+chosen.has(x)+'">'+escapeHtml(labels[i])+'</button>').join('')+'</div>'}
function pretty(v){return v==null?'—':Array.isArray(v)?v.join(', '):String(v)}
reviewPromptFor=function(task){const en=lang()==='en',fence=String.fromCharCode(96).repeat(3),example={difficulty:null,outcome:null,issue:null,issues:[],help_total:null,help_chatgpt:null,chatgpt_interventions:[],strength:null,weakness:null,skill_gap:null,next_action:null};return (en?'Evaluate ONLY facts supported by the task, solution and conversation. Never invent information; unknown fields must be null.':'Bewerte nur belegte Fakten aus Aufgabe, Lösung und Chat. Nichts erfinden; unbekannte Werte müssen null sein.')+'\n'+(en?'Return exactly one copyable fenced JSON code block, with no extra prose.':'Gib genau einen kopierbaren JSON-Codeblock ohne weiteren Text zurück.')+'\n'+(en?'Choose 0–3 observed issues and 0–3 ChatGPT intervention types. Give one specific sentence each for strength and weakness (max 200 characters), a skill gap (max 100) and one next action (max 160).':'Wähle 0–3 beobachtete Probleme und 0–3 ChatGPT-Hilfearten. Stärke und Schwäche je ein konkreter Satz (max. 200 Zeichen); Kompetenzlücke max. 100, nächste Aktion max. 160 Zeichen.')+'\nAllowed issues: '+issues.join(', ')+'\nAllowed assistance types: '+help.join(', ')+'\n'+fence+'json\n'+JSON.stringify(example,null,2)+'\n'+fence+'\n\nExercise: '+task.title+'\nDetails: '+(task.description||'-')+'\n\nTask, solution and conversation:\n[ ... ]'};
function myFields(){const root=document.querySelector('#review-fields');if(!root)return;const n=titles[lang()],extra=document.createElement('section');extra.id='rich-self-fields';extra.className='review-additions';extra.innerHTML='<label>'+n.issues+'</label>'+chips('issues',issues,reviewLang().issues,reviewDraft.issues||[],'self')+'<label>'+n.strength+' (max 200)<textarea id="rich-strength" maxlength="200" rows="2"></textarea></label><label>'+n.weakness+' (max 200)<textarea id="rich-weakness" maxlength="200" rows="2"></textarea></label>';root.after(extra);document.querySelector('#rich-strength').value=reviewDraft.strength||'';document.querySelector('#rich-weakness').value=reviewDraft.weakness||'';const paste=document.querySelector('#review-json');if(paste){const g=document.createElement('div');g.id='rich-gpt-help';g.className='review-additions';paste.closest('label').after(g)}}
function redrawMine(){const div=document.querySelector('#rich-self-fields .review-multi');if(div)div.outerHTML=chips('issues',issues,reviewLang().issues,reviewDraft.issues||[],'self')}
openTaskReview=function(id){originalOpen(id);const task=taskById(id);if(!task)return;for(const field of ['issues','strength','weakness','skill_gap','next_action','chatgpt_interventions'])reviewDraft[field]=task.exercise_review?.[field]??null;reviewDraft.issues=[...(reviewDraft.issues||(reviewDraft.issue?[reviewDraft.issue]:[]))];myFields();renderReviewComparison()};
renderReviewComparison=function(){originalCompare();const where=document.querySelector('#review-source-comparison');if(!where)return;const n=titles[lang()],g=gptAssessmentFromDialog(),data=g.data||{};const gHelp=document.querySelector('#rich-gpt-help');if(gHelp)gHelp.innerHTML='<label>'+n.gptHelp+'</label>'+chips('chatgpt_interventions',help,helpTitles[lang()],data.chatgpt_interventions||[],'gpt');let out=document.querySelector('#rich-comparison');if(!out){out=document.createElement('div');out.id='rich-comparison';out.className='review-source-comparison';where.after(out)}const fields=[['issues',n.issues],['strength',n.strength],['weakness',n.weakness],['skill_gap',n.skill_gap],['next_action',n.next_action],['chatgpt_interventions',n.interventions]];out.innerHTML=fields.map(([key,label])=>'<div class="review-compare-row"><span>'+escapeHtml(label)+'</span><strong>'+escapeHtml(pretty(reviewDraft[key]))+'</strong><strong>'+escapeHtml(pretty(data[key]))+'</strong><span>'+(data[key]!=null&&JSON.stringify(reviewDraft[key])!==JSON.stringify(data[key])?'<button type="button" class="review-use" data-rich-use="'+key+'">'+(lang()==='en'?'Use GPT':'Übernehmen')+'</button>':'')+'</span></div>').join('')};
document.addEventListener('input',e=>{if(e.target.id==='rich-strength'){reviewDraft.strength=e.target.value||null;renderReviewComparison()}if(e.target.id==='rich-weakness'){reviewDraft.weakness=e.target.value||null;renderReviewComparison()}});
document.addEventListener('change',e=>{if(e.target.id==='review-issue'&&reviewDraft){const item=reviewDraft.issue,old=reviewDraft.issues||[];if(item&&!old.includes(item)){reviewDraft.issues=[item,...old].slice(0,3);redrawMine()}else if(!item&&old.length)reviewDraft.issue=old[0];renderReviewComparison()}});
document.addEventListener('click',e=>{const chip=e.target.closest('[data-rich-field]');if(chip){const owner=chip.dataset.richOwner,key=chip.dataset.richField,code=chip.dataset.richCode;const state=owner==='gpt'?gptAssessmentFromDialog():{data:reviewDraft,error:null};if(state.error)return;const obj=state.data||{},old=obj[key]||[],next=old.includes(code)?old.filter(x=>x!==code):[...old,code];if(next.length>3)return;obj[key]=next;if(owner==='gpt'){document.querySelector('#review-json').value=JSON.stringify(obj,null,2)}else{reviewDraft.issues=next;reviewDraft.issue=next.includes(reviewDraft.issue)?reviewDraft.issue:next[0]||null;redrawMine()}renderReviewComparison();return}const b=e.target.closest('[data-rich-use]');if(b){const g=gptAssessmentFromDialog(),key=b.dataset.richUse;if(!g.error&&g.data?.[key]!=null){reviewDraft[key]=Array.isArray(g.data[key])?[...g.data[key]]:g.data[key];if(key==='issues'){reviewDraft.issue=reviewDraft.issues?.[0]||null;redrawMine()}if(key==='strength'){const el=document.querySelector('#rich-strength');if(el)el.value=reviewDraft.strength||''}if(key==='weakness'){const el=document.querySelector('#rich-weakness');if(el)el.value=reviewDraft.weakness||''}renderReviewComparison()}}});
/* Reuse the existing import assistant DOM (and its bound events) inside a modal. */
let importHome=null,importNext=null,importPanel=null;
const closeBeforeImport=typeof modalClose==='function'?modalClose:null;
function restoreImportPanel(){
 if(!importPanel||!importHome)return;
 importPanel.classList.remove('agent-in-modal');
 if(importNext&&importNext.parentElement===importHome)importHome.insertBefore(importPanel,importNext);
 else importHome.appendChild(importPanel);
 importHome=null;importNext=null;importPanel=null;
}
if(closeBeforeImport)modalClose=function(){restoreImportPanel();closeBeforeImport()};
// The main app bound its close button directly before this extension loaded.
// Restore the reused panel in capture phase before that original click handler clears modal content.
document.querySelector('#modal-close')?.addEventListener('click',restoreImportPanel,true);
const button=document.querySelector('#board-import');
if(button)button.addEventListener('click',()=>{
 const panel=document.querySelector('#agent-import-panel');
 if(!panel)return;
 if(modalKind)modalClose();
 importHome=panel.parentElement;importNext=panel.nextSibling;importPanel=panel;
 const en=lang()==='en';
 modalOpen('agent-import',en?'Import tasks':'Aufgaben importieren','AI · IMPORT',
   '<div id="agent-import-modal-slot"></div><div class="modal-actions"><button type="button" class="btn outline" data-modal-cancel>'+(en?'Close':'Schließen')+'</button><button type="button" class="btn primary" id="agent-import-json-upload">'+(en?'Upload task JSON':'Aufgaben-JSON importieren')+'</button></div>');
 document.querySelector('#agent-import-modal-slot').appendChild(panel);
 panel.classList.add('agent-in-modal');
 renderAgentBuilder();
 document.querySelector('#agent-subject')?.focus();
});
document.addEventListener('click',e=>{if(e.target.closest('#agent-import-json-upload'))document.querySelector('#import-task-file')?.click()});

})();