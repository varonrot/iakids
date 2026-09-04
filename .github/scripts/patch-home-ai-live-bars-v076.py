from pathlib import Path

p = Path('he/workspace/index.html')
s = p.read_text(encoding='utf-8')

marker = 'KINGDOM AI LIVE BARS — build 0.7.6'

if marker not in s:
    style = r'''
<style id="kingdom-ai-live-bars-v076">
/* =====================================================
   KINGDOM AI LIVE BARS — build 0.7.6
===================================================== */
.kingdom-status-bar{
  width:1180px !important;
  max-width:82% !important;
  grid-template-columns:1fr 1.18fr 1fr 1.05fr !important;
}

.kingdom-status-ai-live{
  padding:10px 13px !important;
  display:flex !important;
  flex-direction:column !important;
  justify-content:space-between !important;
  gap:5px !important;
  overflow:hidden !important;
}
.kingdom-ai-live-head{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:8px;
  direction:rtl;
}
.kingdom-ai-live-copy{
  min-width:0;
  display:flex;
  flex-direction:column;
  align-items:flex-start;
  line-height:1.08;
}
.kingdom-ai-live-kicker{
  color:#55c9ff;
  font-size:10px;
  font-weight:900;
  letter-spacing:1.7px;
  direction:ltr;
}
.kingdom-ai-live-title{
  margin-top:3px;
  color:#f4f8ff;
  font-size:13px;
  font-weight:900;
  white-space:nowrap;
}
.kingdom-ai-live-dot{
  width:10px;
  height:10px;
  flex:0 0 10px;
  border-radius:50%;
  background:#48e5b0;
  box-shadow:0 0 0 5px rgba(72,229,176,.10),0 0 13px rgba(72,229,176,.75);
  animation:kingdomAiLivePulse 1.7s ease-in-out infinite;
}
.kingdom-ai-live-sub{
  color:rgba(203,216,240,.58);
  font-size:9px;
  font-weight:750;
  text-align:right;
  padding-top:3px;
  border-top:1px solid rgba(88,139,205,.14);
}
.kingdom-ai-live-bars{
  height:46px;
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:4px;
  padding:2px 2px 0;
  border-bottom:1px solid rgba(62,126,211,.22);
}
.kingdom-ai-live-bar{
  flex:1 1 0;
  min-width:5px;
  height:var(--h);
  transform-origin:bottom;
  border-radius:5px 5px 2px 2px;
  background:linear-gradient(180deg,#52cff4 0%,#338de9 48%,#5744e8 100%);
  box-shadow:0 0 9px rgba(55,166,255,.18),inset 0 1px rgba(255,255,255,.26);
  animation:kingdomAiBarFill var(--d) ease-in-out var(--delay) infinite alternate;
}
@keyframes kingdomAiBarFill{
  0%{transform:scaleY(.28);filter:brightness(.82)}
  55%{transform:scaleY(.72);filter:brightness(1)}
  100%{transform:scaleY(1);filter:brightness(1.12)}
}
@keyframes kingdomAiLivePulse{
  0%,100%{opacity:.62;transform:scale(.82)}
  50%{opacity:1;transform:scale(1.08)}
}
@media(max-width:1500px){
  .kingdom-status-bar{
    width:auto !important;
    max-width:none !important;
    grid-template-columns:1fr 1.18fr 1fr 1.05fr !important;
  }
  .kingdom-ai-live-title{font-size:11px}
  .kingdom-ai-live-bars{height:40px}
}
</style>
'''
    head_end = s.find('</head>')
    if head_end == -1:
        raise SystemExit('head end not found')
    s = s[:head_end] + style + '\n' + s[head_end:]

    section_start = s.find('<section class="kingdom-status-bar">')
    if section_start == -1:
        raise SystemExit('kingdom status bar section not found')
    section_end = s.find('</section>', section_start)
    if section_end == -1:
        raise SystemExit('kingdom status bar closing section not found')

    card = r'''

  <!-- פעילות AI בזמן אמת -->
  <div class="kingdom-status-card kingdom-status-ai-live" aria-label="פעילות AI בזמן אמת">
    <div class="kingdom-ai-live-head">
      <div class="kingdom-ai-live-copy">
        <span class="kingdom-ai-live-kicker">AI LIVE</span>
        <strong class="kingdom-ai-live-title">פעילות AI בזמן אמת</strong>
      </div>
      <span class="kingdom-ai-live-dot" aria-hidden="true"></span>
    </div>

    <div class="kingdom-ai-live-bars" aria-hidden="true">
      <span class="kingdom-ai-live-bar" style="--h:58%;--d:1.7s;--delay:-.2s"></span>
      <span class="kingdom-ai-live-bar" style="--h:76%;--d:1.45s;--delay:-.8s"></span>
      <span class="kingdom-ai-live-bar" style="--h:92%;--d:1.9s;--delay:-1.1s"></span>
      <span class="kingdom-ai-live-bar" style="--h:68%;--d:1.55s;--delay:-.35s"></span>
      <span class="kingdom-ai-live-bar" style="--h:84%;--d:2.05s;--delay:-1.4s"></span>
      <span class="kingdom-ai-live-bar" style="--h:48%;--d:1.6s;--delay:-.65s"></span>
      <span class="kingdom-ai-live-bar" style="--h:72%;--d:1.8s;--delay:-1.25s"></span>
      <span class="kingdom-ai-live-bar" style="--h:90%;--d:1.5s;--delay:-.5s"></span>
      <span class="kingdom-ai-live-bar" style="--h:62%;--d:1.95s;--delay:-1.05s"></span>
    </div>

    <div class="kingdom-ai-live-sub">מנוע הלמידה פעיל</div>
  </div>
'''
    s = s[:section_end] + card + '\n' + s[section_end:]

for old in ['IAKIDS • build 0.7.4','IAKIDS • build 0.7.5']:
    s = s.replace(old, 'IAKIDS • build 0.7.6')

p.write_text(s, encoding='utf-8')
