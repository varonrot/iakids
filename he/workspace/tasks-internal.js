/* IAKIDS internal tasks view 0.7.65 */
(function(){
  if(window.__IAKIDS_INTERNAL_TASKS_0765) return;
  window.__IAKIDS_INTERNAL_TASKS_0765 = true;

  function ensureStyles(){
    if(document.getElementById('iakidsInternalTasksStyles')) return;
    const style=document.createElement('style');
    style.id='iakidsInternalTasksStyles';
    style.textContent=`
      .main{position:relative!important;}
      #iakidsInternalTasksView{
        position:absolute;inset:0;z-index:1200;
        display:none;flex-direction:column;
        background:#f4f7ff;
        border-radius:24px;overflow:hidden;
        box-shadow:0 20px 60px rgba(4,14,35,.24);
        direction:rtl;
      }
      #iakidsInternalTasksView.open{display:flex;}
      .iit-toolbar{
        height:52px;min-height:52px;
        display:flex;align-items:center;justify-content:space-between;gap:12px;
        padding:0 14px;
        background:linear-gradient(180deg,#ffffff,#f8f9ff);
        border-bottom:1px solid #e5e8f2;
        color:#172052;
      }
      .iit-toolbar strong{font:900 17px "Heebo",Arial,sans-serif;}
      .iit-close{
        height:36px;padding:0 13px;border:1px solid #dfe3ef;border-radius:11px;
        background:#fff;color:#4f5c83;font:800 13px "Heebo",Arial,sans-serif;cursor:pointer;
      }
      .iit-close:hover{background:#f1edff;color:#603ce8;border-color:#d8cdfd;}
      .iit-frame{width:100%;height:100%;min-height:0;border:0;background:#f5f7ff;}
      @media(max-width:900px){
        #iakidsInternalTasksView{border-radius:0;}
        .iit-toolbar{height:48px;min-height:48px;}
      }
    `;
    document.head.appendChild(style);
  }

  function getView(){
    let view=document.getElementById('iakidsInternalTasksView');
    if(view) return view;
    ensureStyles();
    const main=document.querySelector('.main');
    if(!main) return null;
    view=document.createElement('section');
    view.id='iakidsInternalTasksView';
    view.setAttribute('aria-label','המשימות שלי');
    view.innerHTML=`
      <div class="iit-toolbar">
        <strong><i class="fa-regular fa-calendar-check"></i> המשימות שלי</strong>
        <button type="button" class="iit-close"><i class="fa-solid fa-arrow-right"></i> חזרה לעולם הלמידה</button>
      </div>
      <iframe class="iit-frame" title="המשימות שלי" src="/he/tasks/?embed=1"></iframe>
    `;
    main.appendChild(view);
    view.querySelector('.iit-close')?.addEventListener('click',closeTasks);
    const frame=view.querySelector('.iit-frame');
    frame?.addEventListener('load',()=>{
      try{
        const doc=frame.contentDocument;
        if(!doc) return;
        const topbar=doc.querySelector('.topbar');
        if(topbar) topbar.style.display='none';
        const app=doc.querySelector('.app');
        if(app){app.style.gridTemplateRows='minmax(0,1fr)';app.style.minHeight='100vh';}
        const mainInner=doc.querySelector('.main');
        if(mainInner){mainInner.style.paddingTop='16px';mainInner.style.paddingBottom='24px';}
        doc.documentElement.style.background='#f5f7ff';
        doc.body.style.background='#f5f7ff';
      }catch(error){
        console.warn('INTERNAL TASKS EMBED STYLE',error);
      }
    });
    return view;
  }

  function markSidebarActive(clicked){
    document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));
    if(clicked) clicked.classList.add('active');
  }

  function openTasks(clicked){
    try{window.closeWorkspaceAchievements?.()}catch(_e){}
    try{window.closeLearningProgress?.()}catch(_e){}
    try{window.closeMyLessonsInternal?.()}catch(_e){}
    try{window.closeMyFilesInternal?.()}catch(_e){}
    const dash=document.getElementById('iakidsLearningDashboard');
    if(dash) dash.hidden=true;
    const view=getView();
    if(!view) return;
    markSidebarActive(clicked);
    view.classList.add('open');
  }

  function closeTasks(){
    const view=document.getElementById('iakidsInternalTasksView');
    if(view) view.classList.remove('open');
    const home=document.getElementById('homeSidebarBtn');
    if(home){
      document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));
      home.classList.add('active');
    }
  }

  window.openWorkspaceTasks=openTasks;
  window.closeWorkspaceTasks=closeTasks;

  document.addEventListener('click',function(event){
    const item=event.target?.closest?.('button.side-item,a.side-item');
    if(!item) return;
    const text=(item.textContent||'').replace(/\s+/g,' ').trim();
    if(text.includes('משימות')){
      event.preventDefault();
      event.stopPropagation();
      event.stopImmediatePropagation();
      openTasks(item);
      return;
    }
    if(document.getElementById('iakidsInternalTasksView')?.classList.contains('open')){
      closeTasks();
    }
  },true);
})();
