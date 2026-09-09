from pathlib import Path
import re

js=Path('he/workspace/lesson-completion.js')
index=Path('he/workspace/index.html')
s=js.read_text(encoding='utf-8')
MARK='IAKIDS_HOMEWORK_DASHBOARD_RETURN_0760'
if MARK in s:
    print('already applied'); raise SystemExit(0)

# Add a final override that mounts the existing return button inside the homework
# steps sidebar, directly above the "דף הבית" row, instead of floating over the title.
block=r'''

/* IAKIDS_HOMEWORK_DASHBOARD_RETURN_0760 */
(function(){
  if(window.__IAKIDS_HOMEWORK_DASHBOARD_RETURN_0760) return;
  window.__IAKIDS_HOMEWORK_DASHBOARD_RETURN_0760=true;

  function findHomeworkHomeButton(){
    const nodes=[...document.querySelectorAll('button,a,[role="button"]')];
    return nodes.find(el=>{
      const text=(el.textContent||'').replace(/\s+/g,' ').trim();
      if(text!=='דף הבית') return false;
      let p=el.parentElement;
      for(let i=0;i<5 && p;i++,p=p.parentElement){
        const t=(p.textContent||'');
        if(t.includes('העלאת שיעורי הבית') && t.includes('הבנת השאלה')) return true;
      }
      return false;
    })||null;
  }

  function mount(){
    if(!document.body.classList.contains('homework-lesson-mode')) return;
    const btn=document.getElementById('iakidsHomeworkDashboardReturn');
    if(!btn) return;
    const home=findHomeworkHomeButton();
    if(!home || !home.parentElement) return;

    const parent=home.parentElement;
    if(btn.parentElement!==parent || btn.nextElementSibling!==home){
      parent.insertBefore(btn,home);
    }
    btn.classList.add('iakids-homework-dashboard-return-inline');
  }

  const style=document.createElement('style');
  style.id='iakidsHomeworkDashboardReturnInlineStyles0760';
  style.textContent=`
    body.homework-lesson-mode .iakids-homework-dashboard-return.iakids-homework-dashboard-return-inline{
      position:static!important;
      inset:auto!important;
      width:100%!important;
      height:34px!important;
      min-height:34px!important;
      margin:0 0 10px 0!important;
      padding:0 10px!important;
      justify-content:center!important;
      border-radius:10px!important;
      font-size:11px!important;
      box-shadow:none!important;
      transform:none!important;
      background:rgba(13,40,74,.92)!important;
      border:1px solid rgba(84,154,236,.28)!important;
      color:#dcecff!important;
      z-index:auto!important;
    }
    body.homework-lesson-mode .iakids-homework-dashboard-return.iakids-homework-dashboard-return-inline:hover{
      background:rgba(20,55,99,.96)!important;
      border-color:rgba(92,205,255,.55)!important;
      transform:none!important;
    }
  `;
  document.head.appendChild(style);

  document.addEventListener('DOMContentLoaded',()=>setTimeout(mount,250),{once:true});
  if(document.readyState!=='loading') setTimeout(mount,250);
  setTimeout(mount,700);
  setTimeout(mount,1400);
  document.addEventListener('click',()=>setTimeout(mount,80),false);
  window.mountHomeworkDashboardReturn=mount;
})();
'''

s += block
s=re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "[0-9.]+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.60";', s, count=1)
js.write_text(s,encoding='utf-8')

h=index.read_text(encoding='utf-8')
h=re.sub(r'/he/workspace/lesson-completion\.js\?v=\d+', '/he/workspace/lesson-completion.js?v=0760', h, count=1)
h=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.60',h,count=1)
h=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.60";',h,count=1)
index.write_text(h,encoding='utf-8')
print('homework dashboard return moved into sidebar above home; build 0.7.60')
