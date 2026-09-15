(function(){
  const API_BASE = 'https://iakids-ai-tutor-he.onrender.com';
  let history = [];
  let imageDataUrl = '';

  function getClient(){
    try{ if(typeof sb !== 'undefined' && sb) return sb; }catch(_e){}
    return window.sb || null;
  }

  async function getToken(){
    const client = getClient();
    if(!client) return '';
    const {data} = await client.auth.getSession();
    return data?.session?.access_token || '';
  }

  function ensureStyles(){
    if(document.getElementById('openaiCleanChatStyles')) return;
    const style=document.createElement('style');
    style.id='openaiCleanChatStyles';
    style.textContent=`
      #openaiCleanChatView{position:absolute;inset:0;z-index:9998;background:#020b1b;display:flex;flex-direction:column;color:#fff;direction:rtl}
      .occ-head{height:72px;display:flex;align-items:center;justify-content:space-between;padding:0 22px;border-bottom:1px solid rgba(87,153,255,.25);background:linear-gradient(180deg,#0b1931,#071326)}
      .occ-title{font-size:22px;font-weight:900}.occ-sub{font-size:12px;color:#9fb7dc;margin-top:3px}
      .occ-head button{border:1px solid #2b4f7e;background:#10213e;color:#dceaff;border-radius:12px;padding:9px 14px;font-weight:800;cursor:pointer}
      .occ-body{flex:1;min-height:0;display:grid;grid-template-columns:38% 62%;direction:ltr}
      .occ-image{padding:18px;border-right:1px solid rgba(87,153,255,.18);display:flex;flex-direction:column;gap:12px;direction:rtl;overflow:auto}
      .occ-image-card{flex:1;min-height:280px;border:1px dashed #315a8e;border-radius:20px;background:#071428;display:flex;align-items:center;justify-content:center;overflow:hidden;text-align:center;color:#87a4cd}
      .occ-image-card img{width:100%;height:100%;object-fit:contain;background:#031022}
      .occ-upload{border:1px solid #3d66a3;background:#10264a;color:#fff;border-radius:14px;padding:12px 16px;font-weight:900;cursor:pointer;text-align:center}
      .occ-chat{display:flex;flex-direction:column;min-width:0;direction:rtl}
      .occ-messages{flex:1;min-height:0;overflow:auto;padding:22px;display:flex;flex-direction:column;gap:13px}
      .occ-msg{max-width:78%;padding:14px 17px;border-radius:18px;line-height:1.55;white-space:pre-wrap;font-size:16px}
      .occ-msg.user{align-self:flex-end;background:linear-gradient(135deg,#5b35df,#744cff)}
      .occ-msg.assistant{align-self:flex-start;background:#122846;border:1px solid #255184}
      .occ-composer{padding:14px;border-top:1px solid rgba(87,153,255,.18);display:flex;gap:9px;background:#081426}
      .occ-composer textarea{flex:1;resize:none;min-height:56px;max-height:130px;border:1px solid #284a76;border-radius:14px;background:#0b1b33;color:#fff;padding:12px 14px;outline:none;font:inherit}
      .occ-send{width:58px;border:0;border-radius:14px;background:linear-gradient(135deg,#6b44ff,#3d8dff);color:#fff;font-size:22px;cursor:pointer}
      .occ-status{font-size:12px;color:#82a6d6;padding:0 22px 8px}
      @media(max-width:900px){.occ-body{grid-template-columns:1fr}.occ-image{display:none}}
    `;
    document.head.appendChild(style);
  }

  function addMessage(role,text){
    const box=document.querySelector('#openaiCleanChatView .occ-messages');
    if(!box) return;
    const el=document.createElement('div');
    el.className='occ-msg '+role;
    el.textContent=text;
    box.appendChild(el);
    box.scrollTop=box.scrollHeight;
  }

  function setStatus(text){
    const el=document.querySelector('#openaiCleanChatView .occ-status');
    if(el) el.textContent=text||'';
  }

  async function sendMessage(){
    const view=document.getElementById('openaiCleanChatView');
    if(!view) return;
    const input=view.querySelector('textarea');
    const text=String(input?.value||'').trim();
    if(!text && !imageDataUrl) return;
    if(text){ addMessage('user',text); input.value=''; }
    setStatus('GPT-5.6 Sol חושב...');
    try{
      const token=await getToken();
      if(!token) throw new Error('אין התחברות פעילה');
      const response=await fetch(`${API_BASE}/api/tutor/openai-clean-chat`,{
        method:'POST',
        headers:{'Content-Type':'application/json','Authorization':`Bearer ${token}`},
        body:JSON.stringify({message:text,history,image_url:imageDataUrl})
      });
      if(!response.ok) throw new Error(`HTTP ${response.status}`);
      const data=await response.json();
      const reply=String(data?.reply||'').trim();
      if(reply){
        addMessage('assistant',reply);
        if(text) history.push({role:'user',content:text});
        history.push({role:'assistant',content:reply});
        if(history.length>16) history=history.slice(-16);
      }
      setStatus('OpenAI בלבד • ללא Gemini • ללא Homework Coach');
    }catch(err){
      console.error('OPENAI CLEAN CHAT ERROR',err);
      addMessage('assistant','לא הצלחתי להתחבר כרגע. נסה שוב בעוד רגע.');
      setStatus(String(err?.message||err));
    }
  }

  function readFile(file){
    return new Promise((resolve,reject)=>{
      const reader=new FileReader();
      reader.onload=()=>resolve(String(reader.result||''));
      reader.onerror=reject;
      reader.readAsDataURL(file);
    });
  }

  function close(){
    document.getElementById('openaiCleanChatView')?.remove();
    document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));
  }

  window.openOpenAICleanChat=function(button){
    ensureStyles();
    document.getElementById('openaiCleanChatView')?.remove();
    document.querySelectorAll('.side-item').forEach(x=>x.classList.remove('active'));
    button?.classList.add('active');
    history=[]; imageDataUrl='';
    const main=document.querySelector('.main');
    if(!main) return;
    main.style.position='relative';
    const view=document.createElement('section');
    view.id='openaiCleanChatView';
    view.innerHTML=`
      <div class="occ-head"><div><div class="occ-title">OpenAI נקי</div><div class="occ-sub">GPT-5.6 Sol • בלי Gemini • בלי OCR • בלי מנגנון שיעורי הבית הישן</div></div><button type="button" class="occ-close">חזרה</button></div>
      <div class="occ-body">
        <div class="occ-image"><div class="occ-image-card"><span>העלה צילום של דף העבודה</span></div><label class="occ-upload">📎 העלה תמונה<input type="file" accept="image/*" hidden></label></div>
        <div class="occ-chat"><div class="occ-messages"><div class="occ-msg assistant">העלה את דף העבודה וכתוב לי במה לעזור. אני עובד כאן ישירות מול OpenAI בלבד.</div></div><div class="occ-status">OpenAI בלבד • ללא Gemini • ללא Homework Coach</div><div class="occ-composer"><textarea placeholder="כתוב הודעה..."></textarea><button class="occ-send" type="button">➤</button></div></div>
      </div>`;
    main.appendChild(view);
    view.querySelector('.occ-close')?.addEventListener('click',close);
    view.querySelector('.occ-send')?.addEventListener('click',sendMessage);
    view.querySelector('textarea')?.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}});
    view.querySelector('input[type=file]')?.addEventListener('change',async e=>{
      const file=e.target.files?.[0]; if(!file) return;
      imageDataUrl=await readFile(file);
      const card=view.querySelector('.occ-image-card');
      card.innerHTML=`<img alt="דף העבודה">`;
      card.querySelector('img').src=imageDataUrl;
      const input=view.querySelector('textarea');
      if(input && !String(input.value||'').trim()){
        input.value='תסתכל על דף העבודה ותלמד אותי איך לפתור אותו שלב אחרי שלב. אל תיתן לי את התשובה מיד.';
      }
      setStatus('שולח את התמונה ל-OpenAI...');
      await sendMessage();
    });
  };
})();
