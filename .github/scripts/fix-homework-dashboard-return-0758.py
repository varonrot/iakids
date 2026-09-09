from pathlib import Path
import re

js=Path('he/workspace/lesson-completion.js')
index=Path('he/workspace/index.html')
s=js.read_text(encoding='utf-8')
MARK='IAKIDS_HOMEWORK_DASHBOARD_RETURN_0758'
if MARK not in s:
    block=r'''

/* IAKIDS_HOMEWORK_DASHBOARD_RETURN_0758 */
(function(){
  if(window.__IAKIDS_HOMEWORK_DASHBOARD_RETURN_0758) return;
  window.__IAKIDS_HOMEWORK_DASHBOARD_RETURN_0758=true;

  function goDashboard(){
    try{ window.HOMEWORK_STRUCTURED_ACTIVE=false; }catch(_e){}
    try{ document.body.classList.remove('homework-lesson-mode'); }catch(_e){}
    // Full reload is intentional here: it guarantees lesson/fullscreen state is cleared
    // and returns to the normal workspace dashboard without stale lesson DOM.
    window.location.href='/he/workspace/';
  }

  function ensureButton(){
    let btn=document.getElementById('iakidsHomeworkDashboardReturn');
    if(btn) return btn;
    const style=document.createElement('style');
    style.id='iakidsHomeworkDashboardReturnStyles';
    style.textContent=`
      .iakids-homework-dashboard-return{display:none;position:fixed;top:104px;left:24px;z-index:10050;height:42px;padding:0 15px;border-radius:12px;border:1px solid rgba(86,157,238,.35);background:linear-gradient(180deg,#12345f,#0b2548);color:#eef7ff;align-items:center;gap:8px;font:900 12px "Heebo",Arial,sans-serif;cursor:pointer;box-shadow:0 10px 28px rgba(0,0,0,.28)}
      .iakids-homework-dashboard-return:hover{border-color:rgba(92,205,255,.7);transform:translateY(-1px)}
      body.homework-lesson-mode .iakids-homework-dashboard-return{display:flex!important}
      @media(max-width:900px){.iakids-homework-dashboard-return{top:78px;left:12px;height:38px;padding:0 11px;font-size:11px}}
    `;
    document.head.appendChild(style);
    btn=document.createElement('button');
    btn.type='button';
    btn.id='iakidsHomeworkDashboardReturn';
    btn.className='iakids-homework-dashboard-return';
    btn.innerHTML='<i class="fa-solid fa-arrow-left"></i><span>חזרה לדשבורד</span>';
    btn.addEventListener('click',function(event){event.preventDefault();event.stopPropagation();goDashboard();});
    document.body.appendChild(btn);
    return btn;
  }

  document.addEventListener('DOMContentLoaded',ensureButton,{once:true});
  if(document.readyState!=='loading') ensureButton();

  // If a visible navigation control is clicked while Homework is fullscreen,
  // always return cleanly to the dashboard instead of leaving stale lesson layout.
  document.addEventListener('click',function(event){
    if(!document.body.classList.contains('homework-lesson-mode')) return;
    const el=event.target?.closest?.('button,a,.side-item');
    if(!el) return;
    const text=(el.textContent||'').replace(/\s+/g,' ').trim();
    if(el.id==='homeSidebarBtn' || text==='דף הבית' || text.includes('דשבורד')){
      event.preventDefault();event.stopPropagation();event.stopImmediatePropagation();goDashboard();
    }
  },true);

  window.exitHomeworkToDashboard=goDashboard;
})();
'''
    s += block
    s=re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "[0-9.]+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.58";', s, count=1)
    js.write_text(s,encoding='utf-8')

h=index.read_text(encoding='utf-8')
h=re.sub(r'/he/workspace/lesson-completion\.js\?v=\d+', '/he/workspace/lesson-completion.js?v=0758', h, count=1)
h=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.58',h,count=1)
h=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.58";',h,count=1)
index.write_text(h,encoding='utf-8')
print('homework dashboard return fixed; build 0.7.58')
