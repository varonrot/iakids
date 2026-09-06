from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Add analysis-aware classification helpers.
anchor = '  function getHomeworkDetectionSentence(analysis){\n'
helpers = r'''  function resolveHomeworkClassification(analysis){
    const extracted = String(analysis?.extracted_text || "").trim();
    const rawSubject = cleanHomeworkValue(analysis?.subject);
    const rawTopic = cleanHomeworkValue(analysis?.topic);
    const combined = `${extracted}\n${rawSubject}\n${rawTopic}`;
    const lower = combined.toLowerCase();

    let subject = normalizeHomeworkSubjectForDisplay(rawSubject);
    let topic = normalizeHomeworkTopicForDisplay(rawTopic);
    let taskType = "";

    /* Explicit worksheet headings/content outrank a generic AI label such as Literature. */
    const hasTanakhEvidence =
      /תנ[״"']?ך/.test(combined)
      || /שיעורי\s+בית\s+בתנ/.test(combined)
      || /פרשת\s+/.test(combined)
      || /ספר\s+(בראשית|שמות|ויקרא|במדבר|דברים)/.test(combined)
      || /\b(bible|biblical|scripture|tanakh)\b/i.test(combined);

    if(hasTanakhEvidence){
      subject = "תנ״ך";
    }

    if(
      /אברהם\s+מכניס\s+אורחים/.test(combined)
      || (combined.includes("אברהם") && /אורח/.test(combined))
    ){
      topic = "אברהם מכניס אורחים";
    }
    else if(
      (combined.includes("בראשית") || /genesis/i.test(combined))
      &&
      (combined.includes("בריאת") || /creation/i.test(combined))
    ){
      topic = "בריאת העולם";
    }

    const readingTask =
      /קטע\s+קריאה|הבנת\s+הנקרא|reading\s+comprehension|literature/i.test(combined);

    if(readingTask){
      taskType = "הבנת הנקרא";
    }

    /* Literature/Reading Comprehension describes the task, not the school subject. */
    if(
      subject
      &&
      /^(literature|reading comprehension)$/i.test(subject)
      &&
      hasTanakhEvidence
    ){
      subject = "תנ״ך";
    }

    if(
      topic
      &&
      /^(literature|reading comprehension)$/i.test(topic)
    ){
      topic = "";
    }

    return {
      subject,
      topic,
      taskType
    };
  }

'''
if 'function resolveHomeworkClassification' not in core:
    if anchor not in core:
        raise SystemExit('getHomeworkDetectionSentence anchor not found')
    core = core.replace(anchor, helpers + anchor, 1)

# 2) Detection sentence must use resolved classification.
old = '''  function getHomeworkDetectionSentence(analysis){\n    const subject = normalizeHomeworkSubjectForDisplay(analysis?.subject);\n    const topic = normalizeHomeworkTopicForDisplay(analysis?.topic);\n'''
new = '''  function getHomeworkDetectionSentence(analysis){\n    const classification = resolveHomeworkClassification(analysis);\n    const subject = classification.subject;\n    const topic = classification.topic;\n'''
if old not in core:
    raise SystemExit('getHomeworkDetectionSentence values not found')
core = core.replace(old, new, 1)

# 3) Detection card uses subject/topic/task type from worksheet-aware classification.
old = '''    const subject = normalizeHomeworkSubjectForDisplay(analysis?.subject);\n    const topic = normalizeHomeworkTopicForDisplay(analysis?.topic);\n    const sentence = getHomeworkIntroByGrade(analysis);\n'''
new = '''    const classification = resolveHomeworkClassification(analysis);\n    const subject = classification.subject;\n    const topic = classification.topic;\n    const taskType = classification.taskType;\n    const sentence = getHomeworkIntroByGrade(analysis);\n'''
if old not in core:
    raise SystemExit('detection card classification block not found')
core = core.replace(old, new, 1)

old = '''            ${subject ? `<span class="homework-detection-tag">${subject}</span>` : ''}\n            ${topic ? `<span class="homework-detection-tag">${topic}</span>` : ''}\n'''
new = '''            ${subject ? `<span class="homework-detection-tag">${subject}</span>` : ''}\n            ${topic ? `<span class="homework-detection-tag">${topic}</span>` : ''}\n            ${taskType ? `<span class="homework-detection-tag">${taskType}</span>` : ''}\n'''
if old not in core:
    raise SystemExit('detection tags block not found')
core = core.replace(old, new, 1)

# 4) Context sent silently to the tutor must also use corrected Hebrew classification.
old = '''  function buildHomeworkContextMessage(analysis){\n    return `\nהילד העלה צילום של שיעורי הבית.\n\nמקצוע שזוהה:\n${cleanHomeworkValue(analysis?.subject) || "לא ידוע"}\n\nנושא שזוהה:\n${cleanHomeworkValue(analysis?.topic) || "לא ידוע"}\n\nכיתה:\n${getHomeworkGrade()}\n'''
new = '''  function buildHomeworkContextMessage(analysis){\n    const classification = resolveHomeworkClassification(analysis);\n    return `\nהילד העלה צילום של שיעורי הבית.\n\nמקצוע שזוהה:\n${classification.subject || "לא ידוע"}\n\nנושא שזוהה:\n${classification.topic || "לא ידוע"}\n\nסוג משימה:\n${classification.taskType || "לא ידוע"}\n\nכיתה:\n${getHomeworkGrade()}\n'''
if old not in core:
    raise SystemExit('buildHomeworkContextMessage block not found')
core = core.replace(old, new, 1)

# 5) Every help-choice request uses corrected classification instead of raw English labels.
old = '''    const firstQuestion =\n      choice.id === "understand_question"\n        ? extractFirstHomeworkQuestion(analysis.extracted_text)\n        : "";\n\n    const message = `\nאנחנו ממשיכים עם שיעורי הבית שכבר נותחו.\n\nמקצוע: ${cleanHomeworkValue(analysis.subject) || "לא ידוע"}\nנושא: ${cleanHomeworkValue(analysis.topic) || "לא ידוע"}\nכיתה: ${getHomeworkGrade()}\n'''
new = '''    const firstQuestion =\n      choice.id === "understand_question"\n        ? extractFirstHomeworkQuestion(analysis.extracted_text)\n        : "";\n\n    const classification = resolveHomeworkClassification(analysis);\n\n    const message = `\nאנחנו ממשיכים עם שיעורי הבית שכבר נותחו.\n\nמקצוע: ${classification.subject || "לא ידוע"}\nנושא: ${classification.topic || "לא ידוע"}\nסוג משימה: ${classification.taskType || "לא ידוע"}\nכיתה: ${getHomeworkGrade()}\n'''
if old not in core:
    raise SystemExit('runHomeworkChoice classification block not found')
core = core.replace(old, new, 1)

# 6) Broaden basic mappings so English analyzer labels never leak directly for common cases.
core = core.replace(
    '    if(/history|היסטור/.test(lower)) return "היסטוריה";\n',
    '    if(/history|היסטור/.test(lower)) return "היסטוריה";\n    if(/literature/.test(lower)) return "ספרות";\n    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";\n'
)
core = core.replace(
    '    if(/ecosystem/.test(lower)) return "מערכות אקולוגיות";\n',
    '    if(/ecosystem/.test(lower)) return "מערכות אקולוגיות";\n    if(/reading comprehension/.test(lower)) return "הבנת הנקרא";\n    if(/abraham/.test(lower) && /guest|hospitality/.test(lower)) return "אברהם מכניס אורחים";\n'
)

# 7) Bump visible build/cache keys.
index = index.replace('IAKIDS • build 0.7.16', 'IAKIDS • build 0.7.17')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.16";', 'window.IAKIDS_BUILD_VERSION = "0.7.17";')
index = index.replace('/he/workspace/lesson-completion.js?v=0716', '/he/workspace/lesson-completion.js?v=0717')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.16";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.17";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0716', '/he/workspace/lesson-completion-core.js?v=0717')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Homework worksheet-aware classification 0.7.17 applied')
