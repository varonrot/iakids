from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'
backend_path = root / 'backend-ai-tutor-he/main.py'

core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
backend = backend_path.read_text(encoding='utf-8')

# 1) Frontend: never send the coach the other worksheet questions as source material.
marker = '  async function runHomeworkProductionCoach(messageText=""){\n'
helper = r'''  function normalizeHomeworkCoachText(value){
    return String(value || "")
      .replace(/\r/g, "\n")
      .replace(/[״”“"']/g, "")
      .replace(/\s+/g, " ")
      .trim()
      .toLowerCase();
  }

  function buildHomeworkCoachSourceText(analysis, current){
    const raw = String(analysis?.extracted_text || "").replace(/\r/g, "\n").trim();
    if(!raw) return "";

    const questions = Array.isArray(window.CURRENT_HOMEWORK_QUESTIONS)
      ? window.CURRENT_HOMEWORK_QUESTIONS
      : [];
    const normalizedQuestions = questions
      .map(item => normalizeHomeworkCoachText(item?.text))
      .filter(Boolean);

    if(!normalizedQuestions.length) return raw;

    const kept = raw.split("\n").filter(line => {
      const normalizedLine = normalizeHomeworkCoachText(line);
      if(!normalizedLine) return true;
      if(/^שאלות\s*[:：]?$/.test(normalizedLine)) return false;

      const withoutNumber = normalizedLine
        .replace(/^\s*\d{1,2}\s*[.\)\-:]\s*/, "")
        .trim();

      return !normalizedQuestions.some(question => {
        if(normalizedLine === question || withoutNumber === question) return true;
        if(question.length >= 12 && (normalizedLine.includes(question) || withoutNumber.includes(question))) return true;
        if(withoutNumber.length >= 18 && question.includes(withoutNumber)) return true;
        return false;
      });
    }).join("\n").trim();

    // Keep the original only when filtering would remove essentially all useful context.
    return kept.length >= 40 ? kept : raw;
  }

'''
if helper not in core:
    if marker not in core:
        raise SystemExit('runHomeworkProductionCoach marker not found')
    core = core.replace(marker, helper + marker, 1)

old_source = '        source_text:analysis?.extracted_text || "",\n'
new_source = '        source_text:buildHomeworkCoachSourceText(analysis, current),\n'
if old_source not in core:
    raise SystemExit('homework coach source_text line not found')
core = core.replace(old_source, new_source, 1)

# 2) Backend: make the current question the only active task, even if source text still contains question-like text.
old_prompt = '''        "קראי את השאלה ואת חומר המקור, הביני מה צריך למצוא, ולמדי את הילד בצורה טבעית שלב אחרי שלב. "\n        "שמרי כל דבר נכון שהילד כבר מצא ואל תחזרי אחורה. בכל תשובה הסבירי בקצרה מה כבר מצאנו ומה עדיין חסר. "'''
new_prompt = '''        "קראי את השאלה הפעילה ואת חומר המקור, הביני מה צריך למצוא, ולמדי את הילד בצורה טבעית שלב אחרי שלב. "\n        "יש בכל רגע שאלה פעילה אחת בלבד: השאלה שנשלחה בשדה השאלה הפעילה. חומר המקור הוא מקור מידע בלבד, והוא עלול להכיל שאלות נוספות מהדף. התעלמי מהן לחלוטין. "\n        "אסור להזכיר, לשאול, להסביר או לעבור לשאלה אחרת לפני שהמערכת עצמה שולחת אותה כשאלה הפעילה. גם אם מופיעה בחומר המקור שאלה ממוספרת נוספת, היא אינה חלק מהשיחה הנוכחית. "\n        "אם הילד נותן תשובת ביניים, המשיכי רק לאסוף את הפרטים שחסרים כדי לענות על השאלה הפעילה. אל תגלשי לנושא של שאלה אחרת. "\n        "שמרי כל דבר נכון שהילד כבר מצא ואל תחזרי אחורה. בכל תשובה הסבירי בקצרה מה כבר מצאנו ומה עדיין חסר. "'''
if old_prompt not in backend:
    raise SystemExit('homework coach prompt block not found')
backend = backend.replace(old_prompt, new_prompt, 1)

old_context = '''    context = (\n        f"כיתה: {grade or 'לא ידוע'}\\n"\n        f"השאלה: {req.current_question}\\n"\n        f"חומר המקור:\\n{req.source_text}"\n    )\n'''
new_context = '''    context = (\n        f"כיתה: {grade or 'לא ידוע'}\\n"\n        f"השאלה הפעילה היחידה: {req.current_question}\\n"\n        f"חומר מקור בלבד — אין להתייחס לשאלות אחרות שמופיעות בו:\\n<<<SOURCE>>>\\n{req.source_text}\\n<<<END SOURCE>>>"\n    )\n'''
if old_context not in backend:
    raise SystemExit('homework coach context block not found')
backend = backend.replace(old_context, new_context, 1)

# 3) Cache/version bump.
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.91";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0791', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0791', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.91', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.91";', index, count=1)

core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
backend_path.write_text(backend, encoding='utf-8')

print('Isolated homework coach to current question only; build 0.7.91')
