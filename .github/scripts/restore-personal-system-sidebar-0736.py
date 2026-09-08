from pathlib import Path
import re

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

MARK = 'IAKIDS_PERSONAL_SYSTEM_SIDEBAR_SAFE_0736'
if MARK not in s:
    block = r'''
<style id="iakidsPersonalSystemSafeStyles">
  .iakids-personal-safe{margin-top:10px;padding-top:10px;border-top:1px solid rgba(95,140,205,.16);direction:rtl}
  .iakids-personal-safe-head{width:100%;min-height:58px;border:1px solid rgba(88,137,207,.22);border-radius:16px;background:linear-gradient(180deg,rgba(16,35,67,.9),rgba(8,23,49,.94));color:#e9f1ff;display:flex;align-items:center;gap:11px;padding:0 12px;font-weight:900}
  .iakids-personal-safe-head .psi{width:38px;height:38px;border-radius:12px;display:grid;place-items:center;background:linear-gradient(135deg,#6750ff,#2d8cff);color:#fff}
  .iakids-personal-safe-head .pst{flex:1;text-align:right;font-size:15px}
  .iakids-personal-safe-head .psc{min-width:28px;height:28px;padding:0 7px;border-radius:999px;display:grid;place-items:center;background:rgba(74,129,215,.18);border:1px solid rgba(95,158,255,.28);color:#9edfff;font-size:12px}
  .iakids-personal-safe-list{display:grid;gap:7px;margin-top:7px}
  .iakids-personal-safe-row{min-height:50px;border:1px solid rgba(74,122,192,.18);border-radius:14px;background:rgba(9,25,52,.68);display:flex;align-items:center;gap:9px;padding:6px 9px;color:#dce9ff;cursor:pointer;font-weight:850}
  .iakids-personal-safe-row:hover{border-color:rgba(91,170,255,.42);background:rgba(13,34,68,.84)}
  .iakids-personal-safe-row .psri{width:32px;height:32px;border-radius:10px;display:grid;place-items:center;background:linear-gradient(135deg,rgba(78,77,216,.95),rgba(31,128,197,.95));color:#fff;flex:0 0 32px}
  .iakids-personal-safe-empty{padding:10px 12px;color:#788eaf;font-size:12px;font-weight:700;text-align:right}
</style>
<script id="IAKIDS_PERSONAL_SYSTEM_SIDEBAR_SAFE_0736">
(function(){
  function getClient(){
    try{ if(typeof sb !== 'undefined' && sb?.from) return sb; }catch(_e){}
    return window.sb?.from ? window.sb : (window.supabaseClient?.from ? window.supabaseClient : null);
  }
  function getKid(){
    try{ if(typeof CURRENT_KID !== 'undefined' && CURRENT_KID?.id) return CURRENT_KID; }catch(_e){}
    return window.CURRENT_KID || window.SELECTED_KID || window.currentKid || null;
  }
  function esc(v){return String(v??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));}
  function ensureHost(){
    const actions=document.querySelector('.kid-actions');
    if(!actions) return null;
    let host=document.getElementById('iakidsPersonalSafe');
    if(host) return host;
    host=document.createElement('section');
    host.id='iakidsPersonalSafe';
    host.className='iakids-personal-safe';
    host.innerHTML=`<div class="iakids-personal-safe-head"><span class="psi"><i class="fa-solid fa-wand-magic-sparkles"></i></span><span class="pst">המערכת האישית שלי</span><span class="psc" id="iakidsPersonalSafeCount">0</span></div><div class="iakids-personal-safe-list" id="iakidsPersonalSafeList"></div>`;
    actions.appendChild(host);
    return host;
  }
  function openSubject(subject){
    try{
      if(typeof openCustomSubject === 'function'){ openCustomSubject(subject.id, subject.subject_name||'מקצוע אישי'); return; }
      if(typeof window.openCustomSubject === 'function'){ window.openCustomSubject(subject.id, subject.subject_name||'מקצוע אישי'); return; }
    }catch(e){ console.warn('PERSONAL SAFE OPEN',e); }
  }
  function render(items){
    ensureHost();
    const list=document.getElementById('iakidsPersonalSafeList');
    const count=document.getElementById('iakidsPersonalSafeCount');
    if(!list||!count) return;
    count.textContent=String(items.length);
    if(!items.length){list.innerHTML='<div class="iakids-personal-safe-empty">עדיין לא נוספו מקצועות אישיים</div>';return;}
    list.innerHTML='';
    items.forEach(subject=>{
      const row=document.createElement('button');
      row.type='button';
      row.className='iakids-personal-safe-row';
      row.innerHTML=`<span class="psri"><i class="fa-solid fa-star"></i></span><span>${esc(subject.subject_name)}</span>`;
      row.addEventListener('click',()=>openSubject(subject));
      list.appendChild(row);
    });
  }
  async function load(){
    ensureHost();
    const kid=getKid();
    const client=getClient();
    if(!kid?.id||!client){render([]);return;}
    try{
      const {data,error}=await client.from('kid_custom_subjects').select('id,subject_name,status,created_at').eq('kid_id',kid.id).eq('status','active').order('created_at',{ascending:true});
      if(error) throw error;
      render(Array.isArray(data)?data:[]);
    }catch(e){console.warn('PERSONAL SAFE LOAD',e);}
  }
  document.addEventListener('DOMContentLoaded',()=>setTimeout(load,900),{once:true});
  if(document.readyState!=='loading') setTimeout(load,900);
  window.refreshPersonalSystemsSidebar=load;
})();
</script>
'''
    s = s.replace('</body>', block + '\n</body>', 1)

# bump visible build only
s = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.36', s, count=1)
s = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.36";', s, count=1)
p.write_text(s,encoding='utf-8')
print('safe personal system sidebar restored; build 0.7.36')
