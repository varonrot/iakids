from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

# 1) The spoken intro should only identify the homework; no "how would you like help?" question.
old_intro = '''    if(subject && topic){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject} בנושא ${topic}. ${language.howHelp}`;
    }

    if(subject){
      return `${greeting}זיהיתי שזה שיעורי בית ב${subject}. ${language.howHelp}`;
    }

    if(topic){
      return `${greeting}זיהיתי את הנושא ${topic}. ${language.howHelp}`;
    }

    return `${greeting}זיהיתי את שיעורי הבית. ${language.howHelp}`;
'''
new_intro = '''    if(subject && topic){
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
if old_intro not in core:
    raise SystemExit('Could not find homework spoken intro block')
core = core.replace(old_intro, new_intro, 1)

# 2) After analysis, do not render the help-choice menu. Start the production Sol coach immediately.
old_flow = '''    setHomeworkSidebarStep(2);
    removeHomeworkReadingStatus();
    renderHomeworkDetectionCard(analysis);
    renderHomeworkHelpOptions();

    /* Speak only the teacher's short intro — not tags/buttons/loading text. */
    playHomeworkTeacherAudio(
      getHomeworkSpokenIntro(analysis)
    );

    const messages = getHomeworkMessagesContainer();
    if(messages){
      requestAnimationFrame(() => { messages.scrollTop = 0; });
    }

    /*
      שומרים גם את הפענוח בהקשר של מנוע המורה כדי שהילד יוכל
      לכתוב תשובה חופשית במקום ללחוץ על כפתור ועדיין המורה תדע
      לאיזה דף שיעורי בית הוא מתייחס.
    */
    await primeHomeworkTutorContext(analysis);
'''
new_flow = '''    setHomeworkSidebarStep(2);
    removeHomeworkReadingStatus();
    renderHomeworkDetectionCard(analysis);
    removeHomeworkHelpOptions();

    /* Identify the homework, then immediately begin teaching it. */
    await playHomeworkTeacherAudio(
      getHomeworkSpokenIntro(analysis)
    );

    const messages = getHomeworkMessagesContainer();
    if(messages){
      requestAnimationFrame(() => { messages.scrollTop = 0; });
    }

    /* No help-mode chooser anymore: the production Sol coach starts automatically. */
    window.HOMEWORK_HELP_MODE = "solve_together";
    window.HOMEWORK_PRODUCTION_COACH_MODE = true;
    window.HOMEWORK_PRODUCTION_COACH_HISTORY = [];
    setHomeworkSidebarStep(4);
    await runHomeworkProductionCoach("");
'''
if old_flow not in core:
    raise SystemExit('Could not find smart homework intro flow')
core = core.replace(old_flow, new_flow, 1)

# 3) Bump versions/cache.
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.88";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0788', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0788', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.88', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.88";', index, count=1)

if 'renderHomeworkHelpOptions();\n\n    /* Speak only' in core:
    raise SystemExit('Help choice render still active in smart intro')
if 'window.HOMEWORK_PRODUCTION_COACH_MODE = true;' not in core:
    raise SystemExit('Production coach auto-start missing')

core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

print('Homework now starts production GPT-5.6 Sol coach immediately; build 0.7.88')
