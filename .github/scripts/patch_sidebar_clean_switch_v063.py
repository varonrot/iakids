from pathlib import Path

p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

marker = '''  /* =============================================
     CLICK — שיעור אמיתי
  ============================================= */
'''
helper = '''  /* =============================================
     CLEAN LESSON WORKSPACE SWITCH
     לחיצה מהסרגל צריכה להתחיל שיעור חדש
     בלי DOM / audio / flow שנשארו מהשיעור הקודם.
  ============================================= */

  async function resetLessonWorkspaceBeforeSidebarSwitch(){

    clearNoResponseTimer();

    try{
      stopLessonBackgroundMusic();
    }
    catch(error){
      console.warn(
        "SIDEBAR SWITCH — BACKGROUND AUDIO STOP WARNING:",
        error
      );
    }

    if(window.currentLessonAudio){
      try{
        window.currentLessonAudio.pause();
        window.currentLessonAudio.currentTime = 0;
      }
      catch(error){
        console.warn(
          "SIDEBAR SWITCH — LESSON AUDIO STOP WARNING:",
          error
        );
      }

      window.currentLessonAudio = null;
    }

    if(window.lessonRenderer){
      window.lessonRenderer.isRunning = false;
    }

    const messages =
      document.querySelector(
        ".messages"
      );

    if(messages){
      messages.innerHTML = "";
    }

    const input =
      document.querySelector(
        ".lesson-chat-workspace input, .lesson-chat-workspace textarea"
      );

    if(input){
      input.value = "";
    }

    const visualStage =
      document.querySelector(
        ".lesson-visual-stage"
      );

    if(visualStage){
      visualStage.innerHTML = "";
    }

    window.CURRENT_UNIVERSAL_LESSON_DATA = null;
    window.CURRENT_LESSON_VISUALS = [];
    window.CURRENT_DISPLAYED_VISUAL_ORDER = null;
    window.CURRENT_LESSON_VISUAL_PART = 1;
    window.CURRENT_LESSON_PARTS_COUNT = 1;
    window.CURRENT_LESSON_FLOW_PHASE = "explanation";
    window.LAST_LESSON_FLOW_RENDER_KEY = null;

    currentLearningMode =
      "lesson_intro";

    currentLessonId =
      null;

    renderDynamicLessonFlow(
      "explanation",
      1,
      1
    );

    console.log(
      "SIDEBAR LESSON WORKSPACE RESET COMPLETE"
    );

    await new Promise(
      resolve =>
        requestAnimationFrame(
          () => resolve()
        )
    );
  }


''' + marker

if marker not in text:
    raise SystemExit('sidebar click marker not found')
if 'resetLessonWorkspaceBeforeSidebarSwitch' in text:
    raise SystemExit('clean switch helper already exists')
text = text.replace(marker, helper, 1)

old = '''            await startSelectedUnitLesson(
              lesson
            );
'''
new = '''            await resetLessonWorkspaceBeforeSidebarSwitch();

            await startSelectedUnitLesson(
              lesson
            );
'''
# Replace only the sidebar occurrence: it is after our inserted helper.
start = text.index('resetLessonWorkspaceBeforeSidebarSwitch')
pos = text.find(old, start)
if pos == -1:
    raise SystemExit('sidebar startSelectedUnitLesson call not found')
text = text[:pos] + text[pos:].replace(old, new, 1)

if 'IAKIDS • build 0.6.2' not in text:
    raise SystemExit('expected build 0.6.2 not found')
text = text.replace('IAKIDS • build 0.6.2', 'IAKIDS • build 0.6.3')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.6.2";', 'window.IAKIDS_BUILD_VERSION = "0.6.3";')

p.write_text(text, encoding='utf-8')
