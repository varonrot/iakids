from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

old = '''    const greeting = kidName
      ? `היי ${kidName}, `
      : "היי, ";

    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. בואי נתחיל יחד.`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. בואי נתחיל יחד.`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. בואי נתחיל יחד.`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. בואי נתחיל יחד.`;
'''
new = '''    const greeting = kidName
      ? `היי ${kidName}, `
      : "היי, ";
    const startTogether = language.gender === "נקבה"
      ? "בואי נתחיל יחד."
      : language.gender === "זכר"
        ? "בוא נתחיל יחד."
        : "נתחיל יחד.";

    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. ${startTogether}`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. ${startTogether}`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. ${startTogether}`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. ${startTogether}`;
'''
if old not in core:
    raise SystemExit('Could not find auto-start intro block')
core = core.replace(old, new, 1)

loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.89";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0789', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0789', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.89', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.89";', index, count=1)

core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Gender-aware automatic homework intro; build 0.7.89')
