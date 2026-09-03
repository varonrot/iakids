from pathlib import Path

completion = Path('he/workspace/lesson-completion.js')
s = completion.read_text(encoding='utf-8')
marker = 'IAKIDS_AI_WAITING_PANEL_V051'

if marker not in s:
    anchor = 'async function showLessonCompletionScreen(){'
    if anchor not in s:
        raise SystemExit('completion function anchor not found')

    helper = r'''
/* IAKIDS_AI_WAITING_PANEL_V051 */
function ensureAiTeacherWaitingPanelStyles(){
  if(document.getElementById('iakidsAiWaitingPanelStyles')) return;
  const style = document.createElement('style');
  style.id = 'iakidsAiWaitingPanelStyles';
  style.textContent = `
    .lesson-chat-workspace{position:relative!important;overflow:hidden!important;}
    .lesson-ai-waiting-panel{position:absolute;inset:0;z-index:9999;display:flex;align-items:stretch;justify-content:center;padding:14px;background:radial-gradient(circle at 50% 34%,rgba(74,68,255,.18),transparent 36%),linear-gradient(180deg,#041127 0%,#020b1d 100%);direction:rtl;color:#fff;}
    .lesson-ai-waiting-card{position:relative;width:100%;height:100%;overflow:hidden;border:1px solid rgba(90,159,255,.55);border-radius:24px;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:30px 20px 24px;background:radial-gradient(circle at 50% 12%,rgba(112,64,255,.24),transparent 34%),linear-gradient(180deg,rgba(8,22,52,.98),rgba(2,10,27,.99));box-shadow:inset 0 0 0 1px rgba(137,74,255,.13),inset 0 0 38px rgba(60,72,255,.12),0 0 22px rgba(43,120,255,.26),0 0 34px rgba(125,56,255,.18);}
    .lesson-ai-waiting-kicker{position:relative;z-index:5;font-size:17px;font-weight:850;color:#dceaff;margin-bottom:2px;}
    .lesson-ai-waiting-title{position:relative;z-index:5;font-size:34px;line-height:1.05;font-weight:950;margin:0;color:#63d8ff;text-shadow:0 0 18px rgba(70,180,255,.40);}
    .lesson-ai-waiting-subtitle{position:relative;z-index:5;margin-top:10px;color:rgba(223,232,250,.82);font-size:14px;font-weight:650;}
    .lesson-ai-waiting-orbit{position:relative;z-index:4;width:205px;height:205px;flex:0 0 205px;margin:26px 0 22px;display:grid;place-items:center;border-radius:50%;background:radial-gradient(circle,rgba(24,53,117,.70),rgba(8,19,54,.95) 67%);border:3px solid #38c9ff;box-shadow:0 0 0 5px rgba(126,67,255,.26),0 0 26px rgba(51,202,255,.75),0 0 52px rgba(116,56,255,.48),inset 0 0 30px rgba(61,135,255,.24);}
    .lesson-ai-waiting-orbit img{width:184px;height:184px;border-radius:50%;object-fit:cover;object-position:center 18%;position:relative;z-index:3;}
    .lesson-ai-waiting-wave{position:absolute;z-index:2;left:-26%;right:-26%;top:48%;height:165px;pointer-events:none;opacity:.92;background:repeating-radial-gradient(ellipse at center,transparent 0 23px,rgba(50,207,255,.50) 24px 26px,transparent 27px 36px,rgba(157,70,255,.58) 37px 40px,transparent 41px 52px);filter:drop-shadow(0 0 6px rgba(47,201,255,.72)) drop-shadow(0 0 10px rgba(142,57,255,.62));transform:translateY(-50%) scaleY(.38);animation:iakidsWaitingWave 6s ease-in-out infinite alternate;-webkit-mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent);mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent);}
    .lesson-ai-waiting-wave.wave-b{top:51%;opacity:.58;transform:translateY(-50%) scaleY(.28) scaleX(1.14);animation-duration:7.5s;animation-direction:alternate-reverse;}
    .lesson-ai-waiting-status{position:relative;z-index:5;display:flex;align-items:center;gap:9px;margin-top:4px;padding:10px 18px;border-radius:999px;border:1px solid rgba(74,157,255,.28);background:rgba(7,27,58,.72);color:#cfe5ff;font-size:13px;font-weight:750;}
    .lesson-ai-waiting-dot{width:9px;height:9px;border-radius:50%;background:#42e8a1;box-shadow:0 0 12px #42e8a1;animation:iakidsWaitingPulse 1.8s ease-in-out infinite;}
    @keyframes iakidsWaitingWave{0%{transform:translate(-3%,-50%) scaleY(.32) scaleX(1.02)}50%{transform:translate(2%,-50%) scaleY(.46) scaleX(1.12)}100%{transform:translate(4%,-50%) scaleY(.34) scaleX(1.05)}}
    @keyframes iakidsWaitingPulse{0%,100%{opacity:.55;transform:scale(.8)}50%{opacity:1;transform:scale(1.18)}}
  `;
  document.head.appendChild(style);
}

function showAiTeacherWaitingPanel(){
  const chat = document.querySelector('.lesson-chat-workspace');
  if(!chat) return false;
  ensureAiTeacherWaitingPanelStyles();
  chat.querySelector('.lesson-ai-waiting-panel')?.remove();
  const panel = document.createElement('section');
  panel.className = 'lesson-ai-waiting-panel';
  panel.innerHTML = `
    <div class="lesson-ai-waiting-card">
      <div class="lesson-ai-waiting-kicker">✦ מורה AI ✦</div>
      <h2 class="lesson-ai-waiting-title">בהמתנה ✨</h2>
      <div class="lesson-ai-waiting-subtitle">אני כאן כשתרצו להמשיך ללמוד</div>
      <div class="lesson-ai-waiting-wave"></div>
      <div class="lesson-ai-waiting-wave wave-b"></div>
      <div class="lesson-ai-waiting-orbit"><img src="/assets/lesson/lesson-teacher.webp" alt="המורה AI"></div>
      <div class="lesson-ai-waiting-status"><span class="lesson-ai-waiting-dot"></span><span>מוכנה כשתרצו להמשיך</span></div>
    </div>`;
  chat.appendChild(panel);
  return true;
}

function hideAiTeacherWaitingPanel(){
  document.querySelectorAll('.lesson-ai-waiting-panel').forEach(el => el.remove());
}

window.showAiTeacherWaitingPanel = showAiTeacherWaitingPanel;
window.hideAiTeacherWaitingPanel = hideAiTeacherWaitingPanel;

'''
    s = s.replace(anchor, helper + anchor, 1)

    call_anchor = '  console.log(\n    "LESSON COMPLETION SCREEN SHOWN",'
    if call_anchor not in s:
        raise SystemExit('completion call anchor not found')
    s = s.replace(call_anchor, '  showAiTeacherWaitingPanel();\n\n' + call_anchor, 1)
    completion.write_text(s, encoding='utf-8')

index = Path('he/workspace/index.html')
h = index.read_text(encoding='utf-8')
start_anchor = 'async function startSelectedUnitLesson(\n  lesson\n){'
if start_anchor not in h:
    raise SystemExit('startSelectedUnitLesson anchor not found')

if "window.hideAiTeacherWaitingPanel();" not in h:
    h = h.replace(
        start_anchor,
        start_anchor + "\n  if(typeof window.hideAiTeacherWaitingPanel === 'function'){\n    window.hideAiTeacherWaitingPanel();\n  }",
        1
    )

h = h.replace('IAKIDS • build 0.5.0', 'IAKIDS • build 0.5.1')
h = h.replace('window.IAKIDS_BUILD_VERSION = "0.5.0"', 'window.IAKIDS_BUILD_VERSION = "0.5.1"')
index.write_text(h, encoding='utf-8')
