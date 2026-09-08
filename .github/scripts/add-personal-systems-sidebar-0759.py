from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

MARKER = 'IAKIDS_PERSONAL_SYSTEMS_SIDEBAR_0759'

if MARKER not in index:
    injection = r'''
<style id="iakidsPersonalSystemsSidebarStyles">
  .iakids-personal-systems-wrap{
    margin-top:10px;
    border-top:1px solid rgba(90,129,190,.16);
    padding-top:10px;
  }
  .iakids-personal-systems-head{
    min-height:58px;
    width:100%;
    border:1px solid rgba(77,126,199,.22);
    border-radius:16px;
    background:linear-gradient(180deg,rgba(16,35,67,.88),rgba(9,24,50,.92));
    color:#e8f0ff;
    display:flex;
    align-items:center;
    gap:12px;
    padding:0 13px;
    cursor:pointer;
    font-weight:900;
    direction:rtl;
  }
  .iakids-personal-systems-head:hover{
    border-color:rgba(78,164,255,.45);
  }
  .iakids-personal-systems-head .ps-icon{
    width:40px;height:40px;flex:0 0 40px;
    display:grid;place-items:center;border-radius:13px;
    background:linear-gradient(135deg,#6750ff,#2d8cff);
    color:#fff;font-size:17px;
    box-shadow:0 7px 15px rgba(53,87,196,.24);
  }
  .iakids-personal-systems-head .ps-title{
    flex:1;text-align:right;font-size:16px;
  }
  .iakids-personal-systems-head .ps-count{
    min-width:28px;height:28px;padding:0 8px;border-radius:999px;
    display:grid;place-items:center;
    background:rgba(81,126,210,.18);
    border:1px solid rgba(91,157,255,.28);
    color:#9edfff;font-size:12px;font-weight:900;
  }
  .iakids-personal-systems-list{
    display:grid;gap:7px;margin-top:7px;
  }
  .iakids-personal-systems-wrap.collapsed .iakids-personal-systems-list{display:none;}
  .iakids-personal-system-row{
    display:flex;align-items:center;gap:8px;
    min-height:52px;padding:6px 8px 6px 10px;
    border-radius:14px;
    border:1px solid rgba(72,120,190,.18);
    background:rgba(9,25,52,.66);
  }
  .iakids-personal-system-open{
    flex:1;min-width:0;border:0;background:transparent;color:#dbe8ff;
    display:flex;align-items:center;gap:10px;text-align:right;cursor:pointer;
    padding:3px 4px;font-weight:850;
  }
  .iakids-personal-system-open .ps-subject-icon{
    width:34px;height:34px;display:grid;place-items:center;border-radius:11px;
    background:linear-gradient(135deg,rgba(78,77,216,.92),rgba(31,128,197,.92));
    color:#fff;flex:0 0 34px;
  }
  .iakids-personal-system-open .ps-subject-name{
    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;
  }
  .iakids-personal-system-remove{
    width:36px;height:36px;flex:0 0 36px;border-radius:11px;
    border:1px solid rgba(255,112,128,.22);
    background:rgba(106,27,43,.18);
    color:#ff9aaa;cursor:pointer;
  }
  .iakids-personal-system-remove:hover{
    background:rgba(139,36,55,.34);color:#ffd5dc;
  }
  .iakids-personal-systems-empty{
    padding:10px 12px;color:#788eaf;font-size:12px;font-weight:700;text-align:right;
  }
</style>
<script id="IAKIDS_PERSONAL_SYSTEMS_SIDEBAR_0759">
(function(){
  let lastKidId = null;
  let refreshBusy = false;

  function getClient(){
    try{
      if(typeof sb !== 'undefined' && sb?.from) return sb;
    }catch(_e){}
    if(window.sb?.from) return window.sb;
    if(window.supabaseClient?.from) return window.supabaseClient;
    return null;
  }

  function getKid(){
    try{
      if(typeof CURRENT_KID !== 'undefined' && CURRENT_KID?.id) return CURRENT_KID;
    }catch(_e){}
    return window.CURRENT_KID || window.SELECTED_KID || window.currentKid || window.selectedKid || null;
  }

  function ensureContainer(){
    const actions = document.querySelector('.kid-actions');
    if(!actions) return null;
    let wrap = document.getElementById('iakidsPersonalSystemsWrap');
    if(wrap) return wrap;

    wrap = document.createElement('section');
    wrap.id = 'iakidsPersonalSystemsWrap';
    wrap.className = 'iakids-personal-systems-wrap';
    wrap.innerHTML = `
      <button type="button" class="iakids-personal-systems-head" aria-expanded="true">
        <span class="ps-icon"><i class="fa-solid fa-wand-magic-sparkles"></i></span>
        <span class="ps-title">המערכת האישית שלי</span>
        <span class="ps-count" id="iakidsPersonalSystemsCount">0</span>
      </button>
      <div class="iakids-personal-systems-list" id="iakidsPersonalSystemsList"></div>`;

    actions.appendChild(wrap);
    const head = wrap.querySelector('.iakids-personal-systems-head');
    head?.addEventListener('click', ()=>{
      wrap.classList.toggle('collapsed');
      head.setAttribute('aria-expanded', wrap.classList.contains('collapsed') ? 'false' : 'true');
    });
    return wrap;
  }

  function escapeHtml(value){
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  }

  async function archivePersonalSystem(subject){
    const client = getClient();
    const kid = getKid();
    if(!client || !kid?.id || !subject?.id) return;

    const ok = window.confirm(`להסיר את "${subject.subject_name}" מהמערכת האישית?\nאפשר יהיה להוסיף מקצוע חדש בעתיד.`);
    if(!ok) return;

    try{
      const now = new Date().toISOString();
      const related = [
        ['kid_custom_lessons', {status:'archived', updated_at:now}],
        ['kid_custom_units', {status:'archived', updated_at:now}],
        ['kid_custom_curriculums', {status:'archived', updated_at:now}]
      ];
      for(const [table, values] of related){
        const result = await client.from(table).update(values).eq('custom_subject_id', subject.id).eq('kid_id', kid.id);
        if(result?.error) console.warn('PERSONAL SYSTEM RELATED ARCHIVE WARNING', table, result.error);
      }

      const { error } = await client
        .from('kid_custom_subjects')
        .update({status:'archived', updated_at:now})
        .eq('id', subject.id)
        .eq('kid_id', kid.id);
      if(error) throw error;

      if(Array.isArray(window.CUSTOM_SUBJECTS)){
        window.CUSTOM_SUBJECTS = window.CUSTOM_SUBJECTS.filter(item => item?.id !== subject.id);
      }
      try{
        if(typeof loadCustomSubjectsForDashboard === 'function'){
          await loadCustomSubjectsForDashboard();
        }
      }catch(error){
        console.warn('PERSONAL SYSTEM MAP REFRESH WARNING', error);
      }
      await refreshPersonalSystems(true);
    }catch(error){
      console.error('PERSONAL SYSTEM REMOVE FAILED', error);
      alert('לא הצלחתי להסיר את המקצוע כרגע. אפשר לנסות שוב.');
    }
  }

  async function openPersonalSystem(subject){
    if(!subject?.id) return;
    try{
      if(typeof openCustomSubject === 'function'){
        await openCustomSubject(subject.id, subject.subject_name || 'מקצוע אישי');
        return;
      }
      if(typeof window.openCustomSubject === 'function'){
        await window.openCustomSubject(subject.id, subject.subject_name || 'מקצוע אישי');
        return;
      }
    }catch(error){
      console.error('PERSONAL SYSTEM OPEN FAILED', error);
    }
  }

  function renderSubjects(subjects){
    const wrap = ensureContainer();
    if(!wrap) return;
    const list = document.getElementById('iakidsPersonalSystemsList');
    const count = document.getElementById('iakidsPersonalSystemsCount');
    if(!list || !count) return;

    count.textContent = String(subjects.length);
    list.innerHTML = '';

    if(!subjects.length){
      list.innerHTML = '<div class="iakids-personal-systems-empty">עדיין לא נוספו מקצועות אישיים</div>';
      return;
    }

    subjects.forEach(subject => {
      const row = document.createElement('div');
      row.className = 'iakids-personal-system-row';
      row.innerHTML = `
        <button type="button" class="iakids-personal-system-open" title="פתיחת ${escapeHtml(subject.subject_name)}">
          <span class="ps-subject-icon"><i class="fa-solid fa-star"></i></span>
          <span class="ps-subject-name">${escapeHtml(subject.subject_name)}</span>
        </button>
        <button type="button" class="iakids-personal-system-remove" title="הסרת ${escapeHtml(subject.subject_name)}" aria-label="הסר ${escapeHtml(subject.subject_name)}">
          <i class="fa-solid fa-trash-can"></i>
        </button>`;
      row.querySelector('.iakids-personal-system-open')?.addEventListener('click', ()=>openPersonalSystem(subject));
      row.querySelector('.iakids-personal-system-remove')?.addEventListener('click', event=>{
        event.preventDefault(); event.stopPropagation(); archivePersonalSystem(subject);
      });
      list.appendChild(row);
    });
  }

  async function refreshPersonalSystems(force=false){
    if(refreshBusy) return;
    const client = getClient();
    const kid = getKid();
    ensureContainer();
    if(!client || !kid?.id){
      renderSubjects([]);
      return;
    }
    if(!force && lastKidId === kid.id && document.querySelectorAll('.iakids-personal-system-row').length) return;

    refreshBusy = true;
    try{
      const { data, error } = await client
        .from('kid_custom_subjects')
        .select('id,kid_id,subject_name,subject_key,status,created_at')
        .eq('kid_id', kid.id)
        .eq('status','active')
        .order('created_at',{ascending:true});
      if(error) throw error;
      lastKidId = kid.id;
      renderSubjects(Array.isArray(data) ? data : []);
    }catch(error){
      console.warn('PERSONAL SYSTEMS SIDEBAR LOAD WARNING', error);
    }finally{
      refreshBusy = false;
    }
  }

  document.addEventListener('DOMContentLoaded', ()=>{
    ensureContainer();
    refreshPersonalSystems(true);
  });

  setTimeout(()=>refreshPersonalSystems(true),400);
  setTimeout(()=>refreshPersonalSystems(true),1400);

  setInterval(()=>{
    const kid = getKid();
    const kidId = kid?.id || null;
    if(kidId !== lastKidId){
      refreshPersonalSystems(true);
    }
  },900);

  window.refreshPersonalSystemsSidebar = ()=>refreshPersonalSystems(true);
})();
</script>
'''
    if '</body>' not in index:
        raise RuntimeError('index body end not found')
    index = index.replace('</body>', injection + '\n</body>', 1)

# Visible build bump
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.59', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.59";', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0759', index, count=1)

loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.59";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0759', loader, count=1)

INDEX.write_text(index, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
print('Personal systems sidebar added; build 0.7.59')
