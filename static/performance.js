/* Dependency-free scheduling primitives; injected timers make deterministic tests possible. */
'use strict';
(function(root,factory){
 const api=factory();
 if(typeof module==='object'&&module.exports)module.exports=api;
 root.StudyPerformance=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
 const VISIBLE_MS=15000,HIDDEN_MS=60000,MAX_BACKOFF_MS=300000;
 function createPoller({run,visible,enabled=()=>true,setTimer=setTimeout,clearTimer=clearTimeout}) {
  let timer=null,inFlight=false,again=false,started=false,failures=0;
  const cancel=()=>{if(timer!==null){clearTimer(timer);timer=null}};
  const delay=()=>Math.min(MAX_BACKOFF_MS,(visible()?VISIBLE_MS:HIDDEN_MS)*2**Math.min(failures,8));
  function schedule(ms=delay()){
   cancel();
   if(started&&enabled()&&!inFlight)timer=setTimer(()=>{timer=null;void execute()},ms);
  }
  async function execute(){
   if(!started||!enabled()||inFlight)return;
   inFlight=true;
   try{await run();failures=0}
   catch{failures=Math.min(8,failures+1)}
   finally{
    inFlight=false;
    const immediate=again;again=false;
    schedule(immediate?0:delay());
   }
  }
  return {
   start(){started=true;failures=0;schedule()},
   stop(){started=false;again=false;cancel()},
   visibilityChanged(){
    if(!started)return;
    if(inFlight){again=visible();return}
    schedule(visible()?0:delay());
   },
   get inFlight(){return inFlight},
   get delay(){return delay()}
  };
 }
 function createClock({shouldRun,tick,setTimer=setTimeout,clearTimer=clearTimeout}){
  let timer=null;
  function stop(){if(timer!==null){clearTimer(timer);timer=null}}
  function sync(){
   if(!shouldRun()){stop();return}
   if(timer===null)timer=setTimer(()=>{
    timer=null;
    if(!shouldRun())return;
    try{tick()}finally{sync()}
   },1000);
  }
  return {sync,stop};
 }
 return {VISIBLE_MS,HIDDEN_MS,MAX_BACKOFF_MS,createPoller,createClock};
});
