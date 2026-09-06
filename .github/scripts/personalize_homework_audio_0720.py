from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''  function getHomeworkSpokenIntro(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;

    if(subject && topic){
      return `זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. איך תרצה שאעזור?`;
    }

    if(subject){
      return `זיהיתי שזה שיעורי בית ב${subject}. איך תרצה שאעזור?`;
    }

    if(topic){
      return `זיהיתי את הנושא ${topic}. איך תרצה שאעזור?`;
    }

    return "זיהיתי את שיעורי הבית. איך תרצה שאעזור?";
  }
'''

new = '''  function getHomeworkSpokenIntro(analysis){
    const classification = resolveHomeworkClassification(analysis);
    const subject = classification.subject;
    const topic = classification.topic;

    const kidName = String(
      window.CURRENT_KID?.name
      || window.CURRENT_KID?.first_name
      || window.CURRENT_KID?.display_name
      || ""
    ).trim();

    const greeting = kidName
      ? `היי ${kidName}, `
      : "היי, ";

    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. איך תרצה שאעזור?`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. איך תרצה שאעזור?`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. איך תרצה שאעזור?`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. איך תרצה שאעזור?`;
  }
'''

if old not in core:
    raise SystemExit('getHomeworkSpokenIntro block not found')
core = core.replace(old, new, 1)

index = index.replace('IAKIDS • build 0.7.19', 'IAKIDS • build 0.7.20')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.19";', 'window.IAKIDS_BUILD_VERSION = "0.7.20";')
index = index.replace('/he/workspace/lesson-completion.js?v=0719', '/he/workspace/lesson-completion.js?v=0720')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.19";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.20";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0719', '/he/workspace/lesson-completion-core.js?v=0720')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Personalized homework audio intro with child name; build 0.7.20')
