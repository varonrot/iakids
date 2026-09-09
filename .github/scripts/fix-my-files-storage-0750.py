from pathlib import Path
import re
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
MARK='IAKIDS_MY_FILES_STORAGE_FIX_0750'
if MARK in s:
    print('already applied'); raise SystemExit(0)

# Fix the wrong homework_sessions column name in the existing My Files block.
s=s.replace("source_file_name,source_file_url,source_file_type,status,started_at,created_at","source_file_name,source_file_url,source_type,status,started_at,created_at")
s=s.replace("fileIcon(r.source_file_type,r.source_file_name)","fileIcon(r.source_type,r.source_file_name)")

# Add a storage fallback layer. If homework_sessions has no file metadata, read the actual
# homework-uploads bucket using the authenticated user's id + selected kid id.
block=r'''
<script id="IAKIDS_MY_FILES_STORAGE_FIX_0750">
(function(){
  if(window.__IAKIDS_MY_FILES_STORAGE_FIX_0750)return;
  window.__IAKIDS_MY_FILES_STORAGE_FIX_0750=true;

  const originalOpen=window.openMyFilesInternal;
  if(typeof originalOpen!=='function') return;

  function getClient(){
    try{if(typeof sb!=='undefined'&&sb?.storage)return sb}catch(_e){}
    return window.sb?.storage?window.sb:(window.supabaseClient?.storage?window.supabaseClient:null);
  }
  function getKid(){
    try{if(typeof CURRENT_KID!=='undefined'&&CURRENT_KID?.id)return CURRENT_KID}catch(_e){}
    return window.CURRENT_KID||window.SELECTED_KID||window.currentKid||window.selectedKid||null;
  }
  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
  function sizeLabel(n){n=Number(n||0);if(n>=1048576)return (n/1048576).toFixed(1)+' MB';if(n>=1024)return Math.round(n/1024)+' KB';return n+' B'}
  function icon(name,mime){const x=(String(name||'')+' '+String(mime||'')).toLowerCase();if(x.includes('pdf'))return'file-pdf';if(x.match(/png|jpg|jpeg|webp|image/))return'file-image';return'file-lines'}

  async function loadFromStorage(){
    const client=getClient(),kid=getKid(),view=document.getElementById('iakidsMyFilesInternalView');
    if(!client||!kid?.id||!view) return;
    const currentText=(view.textContent||'');
    // Only replace the error/empty state. If session-backed rows already rendered, keep them.
    if(!currentText.includes('לא הצלחתי לטעון את הקבצים כרגע') && !currentText.includes('עדיין אין קבצים שמורים')) return;
    try{
      const {data:userData,error:userErr}=await client.auth.getUser();
      if(userErr) throw userErr;
      const uid=userData?.user?.id;
      if(!uid) throw new Error('missing auth user');
      const prefix=`${uid}/${kid.id}`;
      const {data:files,error}=await client.storage.from('homework-uploads').list(prefix,{limit:100,sortBy:{column:'created_at',order:'desc'}});
      if(error) throw error;
      const rows=(files||[]).filter(f=>f?.name && !f.name.endsWith('/'));
      const withUrls=[];
      for(const f of rows){
        const full=`${prefix}/${f.name}`;
        let signed='';
        try{const r=await client.storage.from('homework-uploads').createSignedUrl(full,3600);signed=r?.data?.signedUrl||''}catch(_e){}
        withUrls.push({...f,full,signed});
      }
      const cards=withUrls.length?withUrls.map(f=>{
        const mime=f.metadata?.mimetype||f.metadata?.contentType||'';
        const d=new Date(f.created_at||f.updated_at||Date.now());
        const pretty=(f.name||'קובץ שיעורי בית').replace(/^\d+-/,'');
        return `<div class="imf-file"><div class="imf-icon"><i class="fa-solid fa-${icon(f.name,mime)}"></i></div><div class="imf-name"><b>${esc(pretty)}</b><span>${esc(mime||'קובץ שיעורי בית')}</span></div><div class="imf-cell"><small>גודל</small>${esc(sizeLabel(f.metadata?.size||f.metadata?.contentLength||0))}</div><div class="imf-cell"><small>תאריך</small>${d.toLocaleDateString('he-IL')}</div><span class="imf-status">שמור</span>${f.signed?`<button type="button" class="imf-open" data-url="${esc(f.signed)}">פתיחה</button>`:'<button type="button" class="imf-open" disabled>פתיחה</button>'}</div>`
      }).join(''):'<div class="imf-empty">עדיין אין קבצים שמורים.</div>';
      view.innerHTML=`<div class="imf-shell"><div class="imf-head"><div class="imf-title"><h1>הקבצים שלי</h1><p>קבצים שהועלו בעזרה בשיעורי בית</p></div><button type="button" class="imf-close"><i class="fa-solid fa-arrow-right"></i> חזרה</button></div><div class="imf-stats"><div class="imf-stat"><span>קבצים שמורים</span><strong>${withUrls.length}</strong></div><div class="imf-stat"><span>תמונות</span><strong>${withUrls.filter(f=>String(f.metadata?.mimetype||'').startsWith('image/')).length}</strong></div><div class="imf-stat"><span>PDF</span><strong>${withUrls.filter(f=>String(f.metadata?.mimetype||'').includes('pdf')).length}</strong></div></div><div class="imf-list">${cards}</div></div>`;
      view.querySelector('.imf-close')?.addEventListener('click',()=>window.closeMyFilesInternal?.());
      view.querySelectorAll('.imf-open[data-url]').forEach(b=>b.addEventListener('click',()=>window.open(b.dataset.url,'_blank','noopener')));
    }catch(e){
      console.error('MY FILES STORAGE FALLBACK ERROR',e);
    }
  }

  window.openMyFilesInternal=function(item){
    originalOpen(item);
    setTimeout(loadFromStorage,250);
    setTimeout(loadFromStorage,900);
  };
})();
</script>
'''
if '</body>' not in s: raise SystemExit('body end not found')
s=s.replace('</body>',block+'\n</body>',1)
s=re.sub(r'IAKIDS • build [0-9.]+','IAKIDS • build 0.7.50',s,count=1)
s=re.sub(r'window\.IAKIDS_BUILD_VERSION = "[0-9.]+";','window.IAKIDS_BUILD_VERSION = "0.7.50";',s,count=1)
p.write_text(s,encoding='utf-8')
print('fixed My Files query column and added storage bucket fallback')
