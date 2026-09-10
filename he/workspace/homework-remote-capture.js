/* IAKIDS desktop remote homework capture 0.7.71 */
(function(){
  if(window.__IAKIDS_REMOTE_HOMEWORK_0771) return;
  window.__IAKIDS_REMOTE_HOMEWORK_0771=true;
  let pollTimer=null,currentSession=null;
  const isDesktop=()=>window.matchMedia('(min-width:901px)').matches;

  function getWorkspaceClient(){
    try{ if(typeof sb!=='undefined' && sb) return sb; }catch(_e){}
    return window.sb || null;
  }

  function getActiveKid(){
    try{ if(typeof CURRENT_KID!=='undefined' && CURRENT_KID) return CURRENT_KID; }catch(_e){}
    return window.CURRENT_KID || null;
  }

  function styleButton(btn){
    if(!btn) return;
    const span=btn.querySelector('span');
    const icon=btn.querySelector('i');
    const wantedText=isDesktop()?'סרוק עם הטלפון':'צלם שיעורי בית';
    const wantedIcon=isDesktop()?'fa-solid fa-qrcode':'fa-solid fa-camera';
    if(span && span.textContent!==wantedText) span.textContent=wantedText;
    if(icon && icon.className!==wantedIcon) icon.className=wantedIcon;
  }

  function styleButtons(root=document){
    root.querySelectorAll('[data-homework-camera],[data-homework-camera-retry]').forEach(styleButton);
  }

  const obs=new MutationObserver(mutations=>{
    for(const mutation of mutations){
      for(const node of mutation.addedNodes){
        if(!(node instanceof Element)) continue;
        if(node.matches?.('[data-homework-camera],[data-homework-camera-retry]')) styleButton(node);
        node.querySelectorAll?.('[data-homework-camera],[data-homework-camera-retry]').forEach(styleButton);
      }
    }
  });

  function startObserver(){
    styleButtons();
    if(document.body) obs.observe(document.body,{subtree:true,childList:true});
  }
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',startObserver,{once:true});
  else startObserver();
  setTimeout(()=>styleButtons(),500);
  setTimeout(()=>styleButtons(),1500);

  function ensureStyles(){if(document.getElementById('remoteHomeworkStyles'))return;const s=document.createElement('style');s.id='remoteHomeworkStyles';s.textContent=`
  .remote-homework-modal{position:fixed;inset:0;z-index:100000;background:rgba(0,6,18,.76);display:none;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(10px)}
  .remote-homework-modal.open{display:flex}.remote-homework-card{width:min(560px,96vw);padding:28px;border:1px solid rgba(81,164,255,.42);border-radius:28px;background:linear-gradient(180deg,#091f3e,#041225);box-shadow:0 28px 80px rgba(0,0,0,.5);color:#eef6ff;text-align:center;direction:rtl}.remote-homework-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.remote-homework-head b{font-size:20px}.remote-homework-x{width:38px;height:38px;border:1px solid rgba(94,159,235,.3);border-radius:12px;background:#0c2547;color:#fff;font-size:18px}.remote-homework-qr{width:250px;height:250px;margin:18px auto;padding:14px;border-radius:22px;background:#fff;display:grid;place-items:center}.remote-homework-qr img,.remote-homework-qr canvas{max-width:100%!important;max-height:100%!important}.remote-homework-card p{color:#a8bdd9;line-height:1.65}.remote-homework-status{margin-top:13px;color:#69dcff;font-weight:800;min-height:24px}.remote-homework-link{font-size:12px;color:#7f97b8;word-break:break-all;margin-top:10px}
  `;document.head.appendChild(s)}
  function getModal(){ensureStyles();let m=document.getElementById('remoteHomeworkModal');if(m)return m;m=document.createElement('div');m.id='remoteHomeworkModal';m.className='remote-homework-modal';m.innerHTML=`<section class="remote-homework-card"><div class="remote-homework-head"><b>📱 סרקו עם הטלפון</b><button class="remote-homework-x" type="button">×</button></div><p>סרקו את הקוד, צלמו את שיעורי הבית בטלפון ולחצו „שלח למחשב”. התמונה תופיע כאן אוטומטית.</p><div id="remoteHomeworkQr" class="remote-homework-qr"></div><div id="remoteHomeworkStatus" class="remote-homework-status">יוצר קוד מאובטח...</div><div id="remoteHomeworkLink" class="remote-homework-link"></div></section>`;document.body.appendChild(m);m.querySelector('.remote-homework-x').onclick=closeModal;m.addEventListener('click',e=>{if(e.target===m)closeModal()});return m}
  function closeModal(){const m=document.getElementById('remoteHomeworkModal');m?.classList.remove('open');if(pollTimer){clearInterval(pollTimer);pollTimer=null}}
  async function loadQrLib(){if(window.QRCode)return;await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://cdn.jsdelivr.net/npm/qrcodejs@1.0.0/qrcode.min.js';s.onload=resolve;s.onerror=reject;document.head.appendChild(s)})}
  async function startRemoteCapture(){
    const client=getWorkspaceClient();if(!client){alert('לא ניתן להתחבר כרגע');return}
    const kid=getActiveKid(); if(!kid?.id){alert('לא נמצא ילד פעיל');return}
    const {data:{user}}=await client.auth.getUser();if(!user){alert('יש להתחבר מחדש');return}
    const m=getModal();m.classList.add('open');const status=m.querySelector('#remoteHomeworkStatus');const qr=m.querySelector('#remoteHomeworkQr');const linkEl=m.querySelector('#remoteHomeworkLink');qr.innerHTML='';status.textContent='יוצר קוד מאובטח...';linkEl.textContent='';
    const {data,error}=await client.from('homework_capture_sessions').insert({user_id:user.id,kid_id:kid.id}).select('id,token,expires_at').single();
    if(error||!data){console.error('REMOTE CAPTURE SESSION CREATE',error);status.textContent='לא הצלחנו ליצור קוד. נסו שוב.';return}
    currentSession=data;const url=`${location.origin}/he/capture/?token=${encodeURIComponent(data.token)}`;linkEl.textContent=url;
    try{await loadQrLib();new QRCode(qr,{text:url,width:220,height:220,correctLevel:QRCode.CorrectLevel.M})}catch(e){console.error(e);status.textContent='לא הצלחנו להציג QR';return}
    status.textContent='מחכה לתמונה מהטלפון...';
    if(pollTimer)clearInterval(pollTimer);pollTimer=setInterval(async()=>{
      const {data:sess,error:e}=await client.from('homework_capture_sessions').select('status,signed_url,original_file_name,mime_type').eq('id',data.id).single();
      if(e||!sess)return;
      if(sess.status==='uploaded'&&sess.signed_url){clearInterval(pollTimer);pollTimer=null;status.textContent='התמונה התקבלה — מעביר לשיעורי הבית...';try{const r=await fetch(sess.signed_url);const blob=await r.blob();const file=new File([blob],sess.original_file_name||'homework.jpg',{type:sess.mime_type||blob.type||'image/jpeg'});const input=document.getElementById('homeworkCameraInput')||document.getElementById('homeworkFileInput');if(!input)throw new Error('input_not_found');const dt=new DataTransfer();dt.items.add(file);input.files=dt.files;input.dispatchEvent(new Event('change',{bubbles:true}));await client.from('homework_capture_sessions').update({status:'consumed',consumed_at:new Date().toISOString()}).eq('id',data.id);setTimeout(closeModal,600)}catch(err){console.error(err);status.textContent='התמונה התקבלה אבל לא הצלחנו לפתוח אותה. נסו שוב.'}}
    },1300)
  }
  document.addEventListener('click',e=>{if(!isDesktop())return;const btn=e.target?.closest?.('[data-homework-camera],[data-homework-camera-retry]');if(!btn)return;e.preventDefault();e.stopPropagation();e.stopImmediatePropagation();startRemoteCapture()},true)
})();
