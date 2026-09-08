from pathlib import Path

p = Path('he2/index.html')
s = p.read_text(encoding='utf-8')

css_marker = '/* ===== PARENTS SHOWCASE V2 ===== */'
html_marker = '<!-- PARENTS SHOWCASE V2 -->'

css = r'''
/* ===== PARENTS SHOWCASE V2 ===== */
.parents-showcase-v2{position:relative;min-height:820px;overflow:hidden;background:#041120 url('/assets/he2/sections/parents-section-bg.webp?v=2') center right/cover no-repeat;padding:110px 5vw;display:flex;align-items:center}
.parents-showcase-v2::before{content:"";position:absolute;inset:0;background:linear-gradient(90deg,rgba(4,17,32,.99) 0%,rgba(4,17,32,.96) 24%,rgba(4,17,32,.82) 40%,rgba(4,17,32,.40) 57%,rgba(4,17,32,.12) 72%,rgba(4,17,32,.02) 100%);pointer-events:none}
.parents-showcase-v2::after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(4,17,32,.16),transparent 20%,transparent 80%,rgba(4,17,32,.30));pointer-events:none}
.parents-v2-inner{position:relative;z-index:2;width:100%;max-width:1500px;margin:0 auto;display:grid;grid-template-columns:minmax(420px,560px) 1fr;gap:42px;align-items:center;direction:ltr}
.parents-v2-copy{direction:rtl;text-align:right}
.parents-v2-kicker{display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border:1px solid rgba(61,201,255,.28);border-radius:999px;background:rgba(5,28,48,.60);color:#65d6ff;font-size:12px;font-weight:900;margin-bottom:18px;backdrop-filter:blur(10px)}
.parents-v2-copy h2{font-size:clamp(42px,4vw,68px);line-height:1.04;letter-spacing:-2px;margin-bottom:18px}.parents-v2-copy h2 span{display:block;color:#54cef9}.parents-v2-copy>p{max-width:590px;color:#b7c9d9;font-size:18px;line-height:1.75;margin-bottom:30px}
.parents-v2-features{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.parents-v2-feature{display:grid;grid-template-columns:58px 1fr;gap:14px;align-items:center;padding:18px;border:1px solid rgba(67,164,255,.32);border-radius:20px;background:linear-gradient(180deg,rgba(7,27,49,.88),rgba(5,20,38,.92));box-shadow:inset 0 1px 0 rgba(255,255,255,.035),0 18px 45px rgba(0,0,0,.18);backdrop-filter:blur(12px)}
.parents-v2-icon{width:58px;height:58px;border-radius:17px;display:grid;place-items:center;font-size:27px;color:#61d5ff;background:rgba(51,145,255,.10);border:1px solid rgba(76,173,255,.22)}
.parents-v2-feature strong{display:block;font-size:16px;margin-bottom:5px}.parents-v2-feature span{display:block;color:#9db2c6;font-size:12px;line-height:1.55}.parents-v2-quote{margin-top:18px;padding:18px 20px;border:1px solid rgba(89,177,255,.18);border-radius:18px;background:rgba(5,22,40,.66);color:#c8d8e6;font-size:13px;line-height:1.7}.parents-v2-image-zone{min-height:560px}
@media(max-width:1120px){.parents-showcase-v2{min-height:760px;padding:90px 28px;background-position:62% center}.parents-v2-inner{grid-template-columns:minmax(380px,520px) 1fr}.parents-v2-features{grid-template-columns:1fr}.parents-v2-copy h2{font-size:52px}}
@media(max-width:760px){.parents-showcase-v2{min-height:980px;padding:78px 16px;background-position:68% center;background-size:auto 100%}.parents-showcase-v2::before{background:linear-gradient(180deg,rgba(4,17,32,.96) 0%,rgba(4,17,32,.88) 42%,rgba(4,17,32,.42) 70%,rgba(4,17,32,.10) 100%)}.parents-v2-inner{display:block}.parents-v2-copy{text-align:center}.parents-v2-copy h2{font-size:40px;letter-spacing:-1.2px}.parents-v2-copy>p{font-size:15px;margin:0 auto 24px}.parents-v2-features{grid-template-columns:1fr 1fr}.parents-v2-feature{grid-template-columns:42px 1fr;text-align:right;padding:13px;gap:10px}.parents-v2-icon{width:42px;height:42px;font-size:21px}.parents-v2-feature strong{font-size:13px}.parents-v2-feature span{font-size:10.5px}.parents-v2-image-zone{min-height:360px}}
'''

html = r'''
<!-- PARENTS SHOWCASE V2 -->
<section class="parents-showcase-v2" id="parents-showcase">
  <div class="parents-v2-inner">
    <div class="parents-v2-copy">
      <span class="parents-v2-kicker">🛡️ הורים בראש שקט</span>
      <h2>גם ההורים תמיד בתמונה<span>מעקב חכם, בטוח ופשוט</span></h2>
      <p>ב־IAKids ההורים יכולים לראות את ההתקדמות, תחומי החוזקה, הרגלי הלמידה וזמן השימוש — הכל בזמן אמת, בצורה פשוטה וברורה.</p>
      <div class="parents-v2-features">
        <div class="parents-v2-feature"><div class="parents-v2-icon">▥</div><div><strong>מעקב התקדמות ברור</strong><span>רואים איך הילד מתקדם בכל מקצוע ובכל נושא.</span></div></div>
        <div class="parents-v2-feature"><div class="parents-v2-icon">◷</div><div><strong>זמן מסך מאוזן</strong><span>תמונה ברורה של זמן הלמידה והרגלי השימוש.</span></div></div>
        <div class="parents-v2-feature"><div class="parents-v2-icon">◎</div><div><strong>זיהוי נקודות לחיזוק</strong><span>המערכת מציפה נושאים שכדאי לחזק ולתרגל.</span></div></div>
        <div class="parents-v2-feature"><div class="parents-v2-icon">◇</div><div><strong>למידה בטוחה לילדים</strong><span>סביבה חינוכית מבוקרת, מותאמת לילדים וללא תוכן מיותר.</span></div></div>
      </div>
      <div class="parents-v2-quote">״כיף לראות את הילד מתקדם, לדעת במה הוא חזק ואיפה כדאי לעזור — בלי להפריע לו ללמוד בעצמו.״</div>
    </div>
    <div class="parents-v2-image-zone" aria-hidden="true"></div>
  </div>
</section>
'''

if css_marker not in s:
    s = s.replace('</style>', css + '\n</style>')
if html_marker not in s:
    s = s.replace('</main>', html + '\n</main>')
s = s.replace('href="#parents">להורים</a>', 'href="#parents-showcase">להורים</a>')
p.write_text(s, encoding='utf-8')
