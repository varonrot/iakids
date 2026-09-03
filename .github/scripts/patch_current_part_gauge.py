from pathlib import Path
import re

path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')
original = text

pattern = re.compile(
    r'\n\s*<!-- 2 — חלוקה ללמידה -->\s*\n\s*<article class="mastery-hud-card mastery-parts-hud">.*?</article>',
    re.S,
)
replacement = '''

  <!-- 2 — החלק הנוכחי -->
  <article class="mastery-hud-card mastery-parts-hud mastery-current-part-hud">

    <div class="mastery-hud-title">
      הבנה בחלק הנוכחי
    </div>

    <div class="mastery-current-part-wrap">
      <div class="mastery-current-part-label" id="lessonCurrentPartLabel">
        חלק 1 מתוך 1
      </div>

      <div
        class="mastery-mini-ring mastery-current-part-ring"
        id="lessonCurrentPartGauge"
        style="--value:0"
      >
        <div>
          <b id="lessonCurrentPartSummary">0%</b>
          <small>הבנה בחלק</small>
        </div>
      </div>
    </div>

  </article>'''

text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise SystemExit(f'Expected one learning split card, replaced {count}')

css = '''

/* =====================================================
   DYNAMIC CURRENT PART GAUGE
===================================================== */
.mastery-current-part-hud{
  display:flex;
  flex-direction:column;
  align-items:center;
}
.mastery-current-part-wrap{
  min-height:130px;
  width:100%;
  display:flex;
  flex-direction:column;
  align-items:center;
  justify-content:center;
  gap:4px;
}
.mastery-current-part-label{
  color:#fff;
  font-size:14px;
  font-weight:900;
  text-align:center;
}
.mastery-current-part-ring{
  width:92px;
  height:92px;
  margin-top:2px;
}
'''
if 'DYNAMIC CURRENT PART GAUGE' not in text:
    text = text.replace('</style>', css + '\n</style>', 1)

lookup_pattern = re.compile(
    r'const\s+partOneSummary\s*=\s*document\.getElementById\(\s*"lessonPartOneSummary"\s*\);',
    re.S,
)
lookup_replacement = '''const currentPartSummary =
    document.getElementById(
      "lessonCurrentPartSummary"
    );

  const currentPartGauge =
    document.getElementById(
      "lessonCurrentPartGauge"
    );

  const currentPartLabel =
    document.getElementById(
      "lessonCurrentPartLabel"
    );'''
text, count = lookup_pattern.subn(lookup_replacement, text, count=1)
if count != 1:
    raise SystemExit(f'Expected one Part 1 summary lookup, replaced {count}')

score_pattern = re.compile(
    r'if\(\s*partOneSummary\s*&&\s*Number\(\s*window\.CURRENT_LESSON_VISUAL_PART\s*\|\|\s*1\s*\)\s*===\s*1\s*\)\s*\{\s*partOneSummary\.textContent\s*=\s*`\$\{safeScore\}%`;\s*\}',
    re.S,
)
score_replacement = '''if(currentPartSummary){
    currentPartSummary.textContent = `${safeScore}%`;
  }

  if(currentPartGauge){
    currentPartGauge.style.setProperty("--value", safeScore);
  }

  const activePartNumber = Math.max(
    1,
    Number(window.CURRENT_LESSON_VISUAL_PART || 1)
  );

  const totalPartCount = Math.max(
    activePartNumber,
    Number(window.CURRENT_LESSON_PARTS_COUNT || activePartNumber)
  );

  if(currentPartLabel){
    currentPartLabel.textContent =
      `חלק ${activePartNumber} מתוך ${totalPartCount}`;
  }'''
text, count = score_pattern.subn(score_replacement, text, count=1)
if count != 1:
    raise SystemExit(f'Expected one Part 1-only score block, replaced {count}')

helper_marker = '''/* =====================================================
   LESSON VISUALS
===================================================== */'''
helper = '''/* =====================================================
   CURRENT PART SCORE HUD
===================================================== */
window.CURRENT_SCORE_PART_NUMBER = 0;
window.CURRENT_LESSON_PARTS_COUNT = Number(
  window.CURRENT_LESSON_PARTS_COUNT || 1
);

function syncCurrentPartScoreHud(
  partNumber,
  totalParts = window.CURRENT_LESSON_PARTS_COUNT
){
  const safePartNumber = Math.max(1, Number(partNumber || 1));
  const safeTotalParts = Math.max(
    safePartNumber,
    Number(totalParts || safePartNumber)
  );

  window.CURRENT_LESSON_PARTS_COUNT = safeTotalParts;

  const label = document.getElementById("lessonCurrentPartLabel");
  if(label){
    label.textContent = `חלק ${safePartNumber} מתוך ${safeTotalParts}`;
  }

  if(Number(window.CURRENT_SCORE_PART_NUMBER || 0) === safePartNumber){
    return;
  }

  window.CURRENT_SCORE_PART_NUMBER = safePartNumber;

  const summary = document.getElementById("lessonCurrentPartSummary");
  const gauge = document.getElementById("lessonCurrentPartGauge");

  if(summary){
    summary.textContent = "0%";
  }

  if(gauge){
    gauge.style.setProperty("--value", 0);
  }
}

'''
if 'function syncCurrentPartScoreHud' not in text:
    if helper_marker not in text:
        raise SystemExit('Lesson visuals marker not found')
    text = text.replace(helper_marker, helper + helper_marker, 1)

active_assignment = '''  window.CURRENT_LESSON_VISUAL_PART =
    activeVisualPart;'''
active_replacement = '''  window.CURRENT_LESSON_VISUAL_PART =
    activeVisualPart;

  const structuredPartCount =
    Array.isArray(structuredLesson?.parts)
      ? structuredLesson.parts.length
      : Number(
          window.CURRENT_LESSON_PARTS_COUNT
          ||
          activeVisualPart
        );

  syncCurrentPartScoreHud(
    activeVisualPart,
    structuredPartCount
  );'''
if active_assignment not in text:
    raise SystemExit('Active visual Part assignment not found')
text = text.replace(active_assignment, active_replacement, 1)

if text == original:
    raise SystemExit('No changes made')

path.write_text(text, encoding='utf-8')
print('Current part gauge patch applied successfully')
