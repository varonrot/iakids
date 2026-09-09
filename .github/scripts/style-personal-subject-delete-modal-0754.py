from pathlib import Path
import re
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_PERSONAL_SUBJECT_DELETE_MODAL_0754'
if MARK in s:
    print('already applied'); raise SystemExit(0)

style=r'''
<style id="IAKIDS_PERSONAL_SUBJECT_DELETE_MODAL_0754">
  .iakids-delete-modal-overlay{position:fixed;inset:0;z-index:99999;display:none;align-items:center;justify-content:center;padding:20px;background:rgba(1,8,20,.72);backdrop-filter:blur(8px);direction:rtl;font-family:"Heebo",Arial,sans-serif}
  .iakids-delete-modal-overlay.show{display:flex}
  .iakids-delete-modal{width:min(440px,calc(100vw - 32px));border-radius:24px;border:1px solid rgba(92,154,235,.26);background:linear-gradient(180deg,#0b213f,#07162d);box-shadow:0 30px 90px rgba(0,0,0,.58),inset 0 0 0 1px rgba(255,255,255,.025);padding:26px;color:#eef6ff;text-align:center}
  .iakids-delete-modal-icon{width:66px;height:66px;margin:0 auto 15px;border-radius:20px;display:grid;place-items:center;background:rgba(207,55,68,.14);border:1px solid rgba(255,91,104,.26);color:#ff7f8b;font-size:26px;box-shadow:0 10px 28px rgba(177,36,49,.18)}
  .iakids-delete-modal h3{margin:0 0 8px;font-size:22px;font-weight:950;color:#fff}
  .iakids-delete-modal p{margin:0;color:#9cb1cd;font-size:14px;line-height:1.7}
  .iakids-delete-modal-name{display:inline-block;margin:12px 0 2px;padding:7px 12px;border-radius:10px;background:rgba(44,102,176,.16);border:1px solid rgba(82,143,220,.22);color:#dbeaff;font-weight:900}
  .iakids-delete-modal-note{margin-top:10px!important;color:#7892b3!important;font-size:12px!important}
  .iakids-delete-modal-actions{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:22px}
  .iakids-delete-modal-actions button{height:44px;border-radius:13px;font-weight:900;cursor:pointer;font-family:inherit}
  .iakids-delete-cancel{border:1px solid rgba(100,150,213,.25);background:#102b50;color:#dcecff}
  .iakids-delete-confirm{border:1px solid rgba(255,97,108,.36);background:linear-gradient(135deg,#c73d4b,#ef5965);color:#fff;box-shadow:0 9px 24px rgba(197,61,75,.22)}
  .iakids-delete-cancel:hover{background:#15355f}.iakids-delete-confirm:hover{filter:brightness(1.06)}
</style>
'''

script=r'''
<script id="IAKIDS_PERSONAL_SUBJECT_DELETE_MODAL_0754_SCRIPT">
(function(){
  if(window.__IAKIDS_PERSONAL_DELETE_MODAL_0754)return;window.__IAKIDS_PERSONAL_DELETE_MODAL_0754=true;
  let resolver=null;
  function ensure(){
    let overlay=document.getElementById('iakidsPersonalDeleteModal');
    if(overlay)return overlay;
    overlay=document.createElement('div');
    overlay.id='iakidsPersonalDeleteModal';
    overlay.className='iakids-delete-modal-overlay';
    overlay.innerHTML=`<div class="iakids-delete-modal" role="dialog" aria-modal="true" aria-labelledby="iakidsDeleteTitle">
      <div class="iakids-delete-modal-icon"><i class="fa-solid fa-trash-can"></i></div>
      <h3 id="iakidsDeleteTitle">להסיר את המקצוע?</h3>
      <p>המקצוע יוסר מהמערכת האישית שלך.</p>
      <div class="iakids-delete-modal-name" id="iakidsDeleteSubjectName"></div>
      <p class="iakids-delete-modal-note">אפשר יהיה להוסיף אותו שוב בעתיד.</p>
      <div class="iakids-delete-modal-actions"><button type="button" class="iakids-delete-cancel">ביטול</button><button type="button" class="iakids-delete-confirm">כן, להסיר</button></div>
    </div>`;
    document.body.appendChild(overlay);
    const finish=(value)=>{overlay.classList.remove('show');const r=resolver;resolver=null;r?.(value)};
    overlay.querySelector('.iakids-delete-cancel')?.addEventListener('click',()=>finish(false));
    overlay.querySelector('.iakids-delete-confirm')?.addEventListener('click',()=>finish(true));
    overlay.addEventListener('click',e=>{if(e.target===overlay)finish(false)});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&overlay.classList.contains('show'))finish(false)});
    return overlay;
  }
  window.confirmPersonalSubjectRemoval=function(subjectName){
    const overlay=ensure();
    const name=overlay.querySelector('#iakidsDeleteSubjectName');
    if(name)name.textContent=subjectName||'המקצוע';
    overlay.classList.add('show');
    return new Promise(resolve=>{resolver=resolve});
  };
})();
</script>
'''

if '</body>' not in s: raise SystemExit('body end not found')
s=s.replace('</body>',style+script+'\n</body>',1)
old="const ok=window.confirm(`להסיר את ${subject.subject_name} מהמערכת האישית שלך?\\n\\nאפשר יהיה להוסיף את המקצוע שוב בעתיד.`);\n        if(!ok) return;"
new="const ok=await window.confirmPersonalSubjectRemoval?.(subject.subject_name);\n        if(!ok) return;"
if old not in s:
    raise SystemExit('browser confirm block not found')
s=s.replace(old,new,1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.54',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = \"[0-9.]+\";','window.IAKIDS_BUILD_VERSION = \"0.7.54\";',s,count=1)
p.write_text(s,encoding='utf-8')
print('styled delete confirmation modal added; build 0.7.54')
