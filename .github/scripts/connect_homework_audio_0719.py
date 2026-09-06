from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Reuse the existing lessonRenderer live TTS + audio player
#    for spoken teacher messages in Homework Help.
# -----------------------------------------------------
anchor = '''  function buildHomeworkContextMessage(analysis){\n'''
helper = r'''  function getHomeworkSpokenIntro(analysis){
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

  async function playHomeworkTeacherAudio(text){
    const spokenText = String(text || "")
      .replace(/\s+/g, " ")
      .trim();

    if(!spokenText){
      return false;
    }

    if(!window.lessonRenderer){
      console.warn("HOMEWORK AUDIO — lessonRenderer not ready");
      return false;
    }

    try{
      /* Use exactly the same browser audio unlock and Gemini TTS path as lessons. */
      if(typeof unlockLessonAudio === "function"){
        await unlockLessonAudio();
      }

      const audioUrl = await window.lessonRenderer.preloadAudioWithRetry(
        spokenText,
        3
      );

      if(!audioUrl){
        console.warn("HOMEWORK AUDIO — no audio URL returned");
        return false;
      }

      await window.lessonRenderer.playAudioUrl(audioUrl);
      return true;
    }
    catch(error){
      /* Audio must never block the homework flow. */
      console.warn("HOMEWORK AUDIO PLAYBACK WARNING:", error);
      return false;
    }
  }

'''

if 'function playHomeworkTeacherAudio' not in core:
    if anchor not in core:
        raise SystemExit('buildHomeworkContextMessage anchor not found')
    core = core.replace(anchor, helper + anchor, 1)

# -----------------------------------------------------
# 2) Speak the short subject/topic detection intro.
#    Do not speak loading/status cards or help buttons.
# -----------------------------------------------------
old = '''    renderHomeworkDetectionCard(analysis);\n    renderHomeworkHelpOptions();\n\n    const messages = getHomeworkMessagesContainer();\n'''
new = '''    renderHomeworkDetectionCard(analysis);\n    renderHomeworkHelpOptions();\n\n    /* Speak only the teacher's short intro — not tags/buttons/loading text. */\n    playHomeworkTeacherAudio(\n      getHomeworkSpokenIntro(analysis)\n    );\n\n    const messages = getHomeworkMessagesContainer();\n'''
if old not in core:
    raise SystemExit('smartHomeworkAnalysisIntro render block not found')
core = core.replace(old, new, 1)

# -----------------------------------------------------
# 3) If the tutor returns a plain text response instead of a renderer
#    sequence, show it and speak the exact teacher reply.
#    Sequence responses already use lessonRenderer.run and its audio path,
#    so we intentionally do not duplicate audio there.
# -----------------------------------------------------
old = '''    if(data?.message || data?.text || data?.response){\n      addMessage("assistant", data.message || data.text || data.response);\n      return;\n    }\n'''
new = '''    if(data?.message || data?.text || data?.response){\n      const homeworkReply = data.message || data.text || data.response;\n      addMessage("assistant", homeworkReply);\n      await playHomeworkTeacherAudio(homeworkReply);\n      return;\n    }\n'''
if old not in core:
    raise SystemExit('plain homework tutor response block not found')
core = core.replace(old, new, 1)

# Expose for debugging/manual replay if needed.
export_anchor = '''  window.getHomeworkIntroByGrade = getHomeworkIntroByGrade;\n'''
export_line = '''  window.playHomeworkTeacherAudio = playHomeworkTeacherAudio;\n'''
if export_line not in core:
    if export_anchor not in core:
        raise SystemExit('homework export anchor not found')
    core = core.replace(export_anchor, export_line + export_anchor, 1)

# -----------------------------------------------------
# 4) Bump visible build/cache versions.
# -----------------------------------------------------
index = index.replace('IAKIDS • build 0.7.18', 'IAKIDS • build 0.7.19')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.18";', 'window.IAKIDS_BUILD_VERSION = "0.7.19";')
index = index.replace('/he/workspace/lesson-completion.js?v=0718', '/he/workspace/lesson-completion.js?v=0719')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.18";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.19";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0718', '/he/workspace/lesson-completion-core.js?v=0719')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Homework teacher audio connected; build 0.7.19')

# trigger 0.7.19
