from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

pattern = re.compile(r'''  function buildHomeworkCoachSourceText\(analysis, current\)\{.*?\n  \}\n\n  async function runHomeworkProductionCoach\(messageText=""\)\{''', re.S)
replacement = r'''  function buildHomeworkCoachSourceText(analysis, current){
    const raw = String(analysis?.extracted_text || "").replace(/\r/g, "\n").trim();
    if(!raw) return "";

    // For reading-comprehension worksheets, the reliable source is the passage itself.
    // Never send the question section to the coach; the active question is supplied separately.
    const questionSection = raw.search(/(?:^|\n)\s*שאלות\s*[:：]?\s*(?:\n|$)/m);
    if(questionSection > 40){
      const passageOnly = raw.slice(0, questionSection).trim();
      if(passageOnly.length >= 40) return passageOnly;
    }

    // Fallback: if OCR missed the "שאלות" heading, cut at the first numbered question
    // once we already have enough source text before it.
    const numberedQuestion = raw.search(/(?:^|\n)\s*1\s*[.\)]\s*[^\n?]{4,}\?/m);
    if(numberedQuestion > 80){
      const passageOnly = raw.slice(0, numberedQuestion).trim();
      if(passageOnly.length >= 40) return passageOnly;
    }

    // Final fallback for worksheets without a clear question section: remove every parsed
    // worksheet question line, but keep the source passage.
    const questions = Array.isArray(window.CURRENT_HOMEWORK_QUESTIONS)
      ? window.CURRENT_HOMEWORK_QUESTIONS
      : [];
    const normalizedQuestions = questions
      .map(item => normalizeHomeworkCoachText(item?.text))
      .filter(Boolean);

    const kept = raw.split("\n").filter(line => {
      const normalizedLine = normalizeHomeworkCoachText(line);
      if(!normalizedLine) return true;
      const withoutNumber = normalizedLine.replace(/^\s*\d{1,2}\s*[.\)\-:]\s*/, "").trim();
      return !normalizedQuestions.some(question =>
        normalizedLine === question ||
        withoutNumber === question ||
        (question.length >= 12 && normalizedLine.includes(question)) ||
        (withoutNumber.length >= 18 && question.includes(withoutNumber))
      );
    }).join("\n").trim();

    return kept.length >= 40 ? kept : raw;
  }

  async function runHomeworkProductionCoach(messageText=""){'''

core, count = pattern.subn(replacement, core, count=1)
if count != 1:
    raise SystemExit('Could not replace buildHomeworkCoachSourceText')

loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.93";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0793', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0793', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.93', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.93";', index, count=1)

core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Homework coach now receives passage-only source; build 0.7.93')
