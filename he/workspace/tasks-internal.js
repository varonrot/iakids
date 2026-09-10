/* IAKIDS internal tasks view 0.7.68 */
(function(){
  if(window.__IAKIDS_INTERNAL_TASKS_0768) return;
  window.__IAKIDS_INTERNAL_TASKS_0768 = true;

  function syncActiveKid(){
    try{
      const kid=window.CURRENT_KID;
      if(kid?.id){
        localStorage.setItem('active_kid_id',kid.id);
        return kid.id;
      }
    }catch(_e){}
    try{return localStorage.getItem('active_kid_id')||'';}catch(_e){return '';}
  }

  function ensureStyles(){
    if(document.getElementById('iakidsInternalTasksStyles')) return;
    const style=document.createElement('style');
    style.id='iakidsInternalTasksStyles';
    style.textContent=`
      .main{position:relative!important;}
      #iakidsInternalTasksView{position:absolute;inset:0;z-index:1200;display:none;flex-direction:column;background:#020b18;border-radius:24px;overflow:hidden;box-shadow:0 20px 60px rgba(0,0,0,.34);direction:rtl;}
      #iakidsInternalTasksView.open{display:flex;}
      .iit-toolbar{height:52px;min-height:52px;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:0 14px;background:linear-gradient(180deg,#071425,#04101e);border-bottom:1px solid rgba(92,154,232,.18);color:#eef6ff;}
      .iit-toolbar strong{font:900 17px "Heebo",Arial,sans-serif;}.iit-toolbar strong i{color:#6ddcff;margin-left:7px;}
      .iit-close{height:36px;padding:0 13px;border:1px solid rgba(89,154,235,.28);border-radius:11px;background:#0a1b31;color:#cfe3fb;font:800 13px "Heebo",Arial,sans-serif;cursor:pointer;}
      .iit-close:hover{background:#102946;color:#fff;border-color:#57cfff;}
      .iit-frame{width:100%;height:100%;min-height:0;border:0;background:#020b18;}
      @media(max-width:900px){#iakidsInternalTasksView{border-radius:0;}.iit-toolbar{height:48px;min-height:48px;}}
    `;
    document.head.appendChild(style);
  }

  function applyEmbeddedDarkTheme(doc){
    if(!doc) return;
    const topbar=doc.querySelector('.topbar');if(topbar) topbar.style.display='none';
    const app=doc.querySelector('.app');if(app){app.style.gridTemplateRows='minmax(0,1fr)';app.style.minHeight='100vh';}
    const mainInner=doc.querySelector('.main');if(mainInner){mainInner.style.paddingTop='16px';mainInner.style.paddingBottom='24px';}
    doc.documentElement.style.background='#020b18';doc.body.style.background='#020b18';
    if(doc.getElementById('iakidsEmbeddedTasksDarkTheme')) return;
    const style=doc.createElement('style');style.id='iakidsEmbeddedTasksDarkTheme';
    style.textContent=`
      :root{--purple:#6b4dff!important;--purple2:#8a68ff!important;--ink:#edf5ff!important;--muted:#8fa6c6!important;--line:rgba(83,140,214,.22)!important;--bg:#020b18!important;--card:#07182b!important;--shadow:0 16px 36px rgba(0,0,0,.28)!important;--soft:0 8px 22px rgba(0,0,0,.20)!important;}
      html,body,.app,.main{background:#020b18!important;color:#edf5ff!important}.main{width:100%!important;max-width:none!important;padding-left:22px!important;padding-right:22px!important}
      .hero-copy h1,.calendar-title,.tasks-head h2,.kid-meta strong{color:#eef6ff!important}.hero-copy p,.kid-meta small,.stat small,.task-sub,.empty,.weekday{color:#8fa6c6!important}
      .card,.calendar-card,.kid-card,.stats,.filters,.tasks-card{background:linear-gradient(180deg,rgba(8,25,46,.98),rgba(4,16,31,.98))!important;border:1px solid rgba(86,151,231,.22)!important;box-shadow:0 16px 36px rgba(0,0,0,.24)!important}
      .kid-card{background:linear-gradient(145deg,#0a1e35,#08162a)!important}.stat{background:#0a1c32!important;color:#f2f7ff!important}
      .filter-btn,.icon-btn,.task-action{background:#0a1c32!important;border-color:rgba(85,145,220,.24)!important;color:#adc4df!important}.filter-btn:hover,.icon-btn:hover,.task-action:hover{background:#102845!important;color:#fff!important}
      .filter-btn.active{background:linear-gradient(135deg,#243b84,#5030bc)!important;border-color:#6e7dff!important;color:#fff!important}
      .day{background:#07182b!important;border-color:rgba(82,137,205,.20)!important;color:#dfeeff!important}.day:hover{background:#0b2039!important;border-color:#438fe7!important}.day.today{background:#10254b!important;border-color:#5ed9ff!important}.day.selected{box-shadow:inset 0 0 0 2px rgba(102,128,255,.55)!important}
      .task{background:#081a2f!important;border-color:rgba(82,137,205,.20)!important;color:#edf5ff!important}.task-title{color:#edf5ff!important}
      .add-btn,.save-btn{background:linear-gradient(135deg,#2377e8,#5a38d7)!important;box-shadow:0 10px 24px rgba(22,98,214,.28)!important}
      .modal-backdrop{background:rgba(0,5,14,.72)!important}.modal{background:#07182b!important;border:1px solid rgba(85,145,220,.26)!important;color:#edf5ff!important}.modal-head h2,.field label{color:#edf5ff!important}
      .field input,.field select,.field textarea{background:#0a1c32!important;border-color:rgba(85,145,220,.28)!important;color:#edf5ff!important}.close-btn,.cancel-btn{background:#0a1c32!important;border-color:rgba(85,145,220,.24)!important;color:#c7dbf2!important}
    `;doc.head.appendChild(style);
  }

  function getView(){
    let view=document.getElementById('iakidsInternalTasksView');if(view) return view;
    ensureStyles();const main=document.querySelector('.main');if(!main) return null;
    syncActiveKid();
    view=document.createElement('section');view.id='iakidsInternalTasksView';view.setAttribute('aria-label','המשימות שלי');
    view.innerHTML=`<div class="iit-toolbar"><strong><i class="fa-regular fa-calendar-check"></i> המשימות שלי</strong><button type="button" class="iit-close"><i class="fa-solid fa-arrow-right"></i> חזרה לעולם הלמידה</button></div><iframe class="iit-frame" title="המשימות שלי" src="/he/tasks/?embed=1&v=0768"></iframe>`;
    main.appendChild(view);view.querySelector('.iit-close')?.addEventListener('click',closeTasks);
    const frame=view.querySelector('.iit-frame');frame?.addEventListener('load',()=>{try{applyEmbeddedDarkTheme(frame.contentDocument)}catch(error){console.warn('INTERNAL TASKS EMBED STYLE',error)}});
    return view;
  }

  function markSidebarActive(clicked){document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));if(clicked) clicked.classList.add('active');}
  function openTasks(clicked){
    try{window.closeWorkspaceAchievements?.()}catch(_e){}try{window.closeLearningProgress?.()}catch(_e){}try{window.closeMyLessonsInternal?.()}catch(_e){}try{window.closeMyFilesInternal?.()}catch(_e){}
    const kidId=syncActiveKid();const dash=document.getElementById('iakidsLearningDashboard');if(dash) dash.hidden=true;
    const view=getView();if(!view) return;const frame=view.querySelector('.iit-frame');
    if(frame && kidId){
      const expected=`/he/tasks/?embed=1&v=0768&kid_id=${encodeURIComponent(kidId)}`;
      if(!frame.src.includes(`kid_id=${encodeURIComponent(kidId)}`)) frame.src=expected;
      try{frame.contentWindow?.localStorage?.setItem('active_kid_id',kidId)}catch(_e){}
    }
    markSidebarActive(clicked);view.classList.add('open');
  }
  function closeTasks(){const view=document.getElementById('iakidsInternalTasksView');if(view) view.classList.remove('open');const home=document.getElementById('homeSidebarBtn');if(home){document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));home.classList.add('active')}}
  window.openWorkspaceTasks=openTasks;window.closeWorkspaceTasks=closeTasks;
  document.addEventListener('click',function(event){const item=event.target?.closest?.('button.side-item,a.side-item');if(!item)return;const text=(item.textContent||'').replace(/\s+/g,' ').trim();if(text.includes('משימות')){event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();openTasks(item);return}if(document.getElementById('iakidsInternalTasksView')?.classList.contains('open'))closeTasks();},true);
})();
