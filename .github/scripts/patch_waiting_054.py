from pathlib import Path

completion = Path("he/workspace/lesson-completion.js")
s = completion.read_text(encoding="utf-8")

old_css = """.lesson-ai-waiting-orbit{position:relative;z-index:4;width:205px;height:205px;flex:0 0 205px;margin:26px 0 22px;display:grid;place-items:center;border-radius:50%;background:radial-gradient(circle,rgba(24,53,117,.70),rgba(8,19,54,.95) 67%);border:3px solid #38c9ff;box-shadow:0 0 0 5px rgba(126,67,255,.26),0 0 26px rgba(51,202,255,.75),0 0 52px rgba(116,56,255,.48),inset 0 0 30px rgba(61,135,255,.24);}
    .lesson-ai-waiting-orbit img{width:184px;height:184px;border-radius:50%;object-fit:cover;object-position:center 18%;position:relative;z-index:3;}
    .lesson-ai-waiting-wave{position:absolute;z-index:2;left:-26%;right:-26%;top:48%;height:165px;pointer-events:none;opacity:.92;background:repeating-radial-gradient(ellipse at center,transparent 0 23px,rgba(50,207,255,.50) 24px 26px,transparent 27px 36px,rgba(157,70,255,.58) 37px 40px,transparent 41px 52px);filter:drop-shadow(0 0 6px rgba(47,201,255,.72)) drop-shadow(0 0 10px rgba(142,57,255,.62));transform:translateY(-50%) scaleY(.38);animation:iakidsWaitingWave 6s ease-in-out infinite alternate;-webkit-mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent);mask-image:linear-gradient(90deg,transparent,#000 12%,#000 88%,transparent);}
    .lesson-ai-waiting-wave.wave-b{top:51%;opacity:.58;transform:translateY(-50%) scaleY(.28) scaleX(1.14);animation-duration:7.5s;animation-direction:alternate-reverse;}"""

new_css = """.lesson-ai-waiting-orbit{position:relative;z-index:4;width:272px;height:272px;flex:0 0 272px;margin:24px 0 20px;display:grid;place-items:center;border-radius:50%;background:radial-gradient(circle,rgba(24,53,117,.70),rgba(8,19,54,.95) 67%);border:3px solid #38c9ff;box-shadow:0 0 0 6px rgba(126,67,255,.28),0 0 32px rgba(51,202,255,.82),0 0 62px rgba(116,56,255,.52),inset 0 0 34px rgba(61,135,255,.26);}
    .lesson-ai-waiting-orbit img{width:244px;height:244px;border-radius:50%;object-fit:cover;object-position:center 18%;position:relative;z-index:3;}
    .lesson-ai-waiting-wave{position:absolute;z-index:2;left:-12%;right:-12%;top:49%;height:190px;pointer-events:none;opacity:.94;filter:drop-shadow(0 0 5px rgba(47,201,255,.80)) drop-shadow(0 0 9px rgba(142,57,255,.70));overflow:visible;}
    .lesson-ai-waiting-wave svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible;}
    .lesson-ai-waiting-wave .wave-line{fill:none;stroke-linecap:round;vector-effect:non-scaling-stroke;stroke-width:2.1;opacity:.88;animation:iakidsWaitingSvgShift 6.8s ease-in-out infinite alternate;}
    .lesson-ai-waiting-wave .wave-line:nth-child(2){animation-duration:7.6s;animation-direction:alternate-reverse;opacity:.70;}
    .lesson-ai-waiting-wave .wave-line:nth-child(3){animation-duration:8.4s;opacity:.54;}
    .lesson-ai-waiting-wave.wave-b{top:51%;opacity:.62;transform:scaleX(1.08);}
    .lesson-ai-waiting-wave.wave-b .wave-line{animation-duration:9s;animation-direction:alternate-reverse;opacity:.45;}"""

if old_css not in s:
    raise SystemExit("waiting panel CSS anchor not found")
s = s.replace(old_css, new_css, 1)

old_keyframe = "@keyframes iakidsWaitingWave{0%{transform:translate(-3%,-50%) scaleY(.32) scaleX(1.02)}50%{transform:translate(2%,-50%) scaleY(.46) scaleX(1.12)}100%{transform:translate(4%,-50%) scaleY(.34) scaleX(1.05)}}"
new_keyframe = "@keyframes iakidsWaitingSvgShift{0%{transform:translateX(-10px)}50%{transform:translateX(8px)}100%{transform:translateX(18px)}}"
if old_keyframe not in s:
    raise SystemExit("old waiting wave keyframe not found")
s = s.replace(old_keyframe, new_keyframe, 1)

old_html = """      <div class=\"lesson-ai-waiting-wave\"></div>
      <div class=\"lesson-ai-waiting-wave wave-b\"></div>
      <div class=\"lesson-ai-waiting-orbit\"><img src=\"/assets/lesson/lesson-teacher.webp\" alt=\"המורה AI\"></div>"""

new_html = """      <div class=\"lesson-ai-waiting-wave\" aria-hidden=\"true\">
        <svg viewBox=\"0 0 1000 190\" preserveAspectRatio=\"none\">
          <defs>
            <linearGradient id=\"iakidsWaveGradientA\" x1=\"0\" x2=\"1\">
              <stop offset=\"0%\" stop-color=\"#36cfff\" stop-opacity=\"0\"/>
              <stop offset=\"18%\" stop-color=\"#36cfff\" stop-opacity=\".95\"/>
              <stop offset=\"52%\" stop-color=\"#9f57ff\" stop-opacity=\".95\"/>
              <stop offset=\"84%\" stop-color=\"#36cfff\" stop-opacity=\".95\"/>
              <stop offset=\"100%\" stop-color=\"#36cfff\" stop-opacity=\"0\"/>
            </linearGradient>
          </defs>
          <path class=\"wave-line\" stroke=\"url(#iakidsWaveGradientA)\" d=\"M0 95 C70 28 140 162 210 95 S350 28 420 95 S560 162 630 95 S770 28 840 95 S930 150 1000 95\"/>
          <path class=\"wave-line\" stroke=\"#8c54ff\" d=\"M0 104 C78 48 145 148 218 96 S360 42 430 100 S572 150 642 96 S782 42 852 99 S942 142 1000 101\"/>
          <path class=\"wave-line\" stroke=\"#37cfff\" d=\"M0 84 C86 142 150 50 224 91 S366 139 438 88 S580 46 650 94 S790 140 858 88 S944 52 1000 90\"/>
        </svg>
      </div>
      <div class=\"lesson-ai-waiting-wave wave-b\" aria-hidden=\"true\">
        <svg viewBox=\"0 0 1000 190\" preserveAspectRatio=\"none\">
          <path class=\"wave-line\" stroke=\"#744dff\" d=\"M0 96 C92 36 170 154 252 96 S420 38 502 96 S668 154 748 96 S914 40 1000 96\"/>
          <path class=\"wave-line\" stroke=\"#2ecfff\" d=\"M0 110 C88 154 164 56 246 102 S410 146 492 98 S656 54 738 102 S906 146 1000 102\"/>
          <path class=\"wave-line\" stroke=\"#a45cff\" d=\"M0 80 C94 128 170 46 252 88 S418 132 500 86 S668 44 750 90 S916 130 1000 88\"/>
        </svg>
      </div>
      <div class=\"lesson-ai-waiting-orbit\"><img src=\"/assets/lesson/lesson-teacher.webp\" alt=\"המורה AI\"></div>"""

if old_html not in s:
    raise SystemExit("waiting panel wave html anchor not found")
s = s.replace(old_html, new_html, 1)
completion.write_text(s, encoding="utf-8")

index = Path("he/workspace/index.html")
h = index.read_text(encoding="utf-8")
if "IAKIDS • build 0.5.3" not in h:
    raise SystemExit("build stamp 0.5.3 not found")
if 'window.IAKIDS_BUILD_VERSION = "0.5.3"' not in h:
    raise SystemExit("build JS 0.5.3 not found")
h = h.replace("IAKIDS • build 0.5.3", "IAKIDS • build 0.5.4", 1)
h = h.replace('window.IAKIDS_BUILD_VERSION = "0.5.3"', 'window.IAKIDS_BUILD_VERSION = "0.5.4"', 1)
index.write_text(h, encoding="utf-8")
