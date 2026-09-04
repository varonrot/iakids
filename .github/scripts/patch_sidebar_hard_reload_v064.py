from pathlib import Path

p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

# Remove the manual workspace-reset helper added in 0.6.3.
helper_start = text.find('  /* =============================================\n     CLEAN LESSON WORKSPACE SWITCH')
click_marker = '  /* =============================================\n     CLICK — שיעור אמיתי\n  ============================================= */\n'
if helper_start == -1:
    raise SystemExit('0.6.3 reset helper start not found')
helper_end = text.find(click_marker, helper_start)
if helper_end == -1:
    raise SystemExit('sidebar click marker after reset helper not found')
text = text[:helper_start] + text[helper_end:]

old = '''            await resetLessonWorkspaceBeforeSidebarSwitch();

            await startSelectedUnitLesson(
              lesson
            );
'''
new = '''            /*
              HARD RELOAD מבוקר:
              שומרים את יעד השיעור ואת הקונטקסט של העץ,
              מרעננים את כל העמוד, ואז bootstrap בתחתית
              פותח את השיעור מאפס דרך אותו entry flow.
            */

            const pendingSidebarLesson = {
              lesson: {
                ...lesson
              },
              parentLesson: {
                ...CURRENT_PARENT_LESSON
              },
              unit: {
                ...CURRENT_UNIT
              },
              category:
                SCIENCE_SELECTED_CATEGORY
                ||
                CURRENT_PARENT_LESSON?.category
                ||
                null,
              savedAt:
                Date.now()
            };

            sessionStorage.setItem(
              "iakids_pending_sidebar_lesson",
              JSON.stringify(
                pendingSidebarLesson
              )
            );

            window.location.reload();
            return;
'''
if old not in text:
    raise SystemExit('0.6.3 sidebar reset/start block not found')
text = text.replace(old, new, 1)

bootstrap_marker = '<script src="/he/workspace/lesson-completion.js"></script>\n'
bootstrap = '''<script src="/he/workspace/lesson-completion.js"></script>
<script id="iakidsSidebarHardReloadBootstrapV064">
(function(){

  const STORAGE_KEY =
    "iakids_pending_sidebar_lesson";

  const raw =
    sessionStorage.getItem(
      STORAGE_KEY
    );

  if(!raw){
    return;
  }

  let pending =
    null;

  try{
    pending =
      JSON.parse(raw);
  }
  catch(error){
    console.error(
      "SIDEBAR HARD RELOAD — INVALID PENDING DATA:",
      error
    );

    sessionStorage.removeItem(
      STORAGE_KEY
    );

    return;
  }

  if(
    !pending?.lesson?.id
    ||
    Date.now()
      - Number(pending.savedAt || 0)
      > 5 * 60 * 1000
  ){
    sessionStorage.removeItem(
      STORAGE_KEY
    );
    return;
  }

  let attempts = 0;

  const tryResume =
    window.setInterval(
      async () => {

        attempts++;

        const kidReady =
          typeof CURRENT_KID !== "undefined"
          &&
          CURRENT_KID?.id;

        const engineReady =
          typeof startSelectedUnitLesson
          === "function";

        if(
          !kidReady
          ||
          !engineReady
        ){

          if(attempts >= 150){
            window.clearInterval(
              tryResume
            );

            console.error(
              "SIDEBAR HARD RELOAD — APP NOT READY"
            );
          }

          return;
        }

        window.clearInterval(
          tryResume
        );

        /*
          מסירים לפני הפתיחה כדי שגם אם
          startSelectedUnitLesson נכשל לא נקבל reload loop.
        */
        sessionStorage.removeItem(
          STORAGE_KEY
        );

        try{

          CURRENT_PARENT_LESSON = {
            ...pending.parentLesson
          };

          CURRENT_UNIT = {
            ...pending.unit
          };

          if(
            typeof SCIENCE_SELECTED_CATEGORY
            !== "undefined"
            &&
            pending.category
          ){
            SCIENCE_SELECTED_CATEGORY =
              pending.category;
          }

          document.body.classList.remove(
            "science-hierarchy-mode"
          );

          const scienceView =
            document.getElementById(
              "scienceHierarchyView"
            );

          if(scienceView){
            scienceView.style.display =
              "none";
          }

          const dashboard =
            document.getElementById(
              "dashboardView"
            );

          if(dashboard){
            dashboard.style.display =
              "none";
          }

          const pathView =
            document.getElementById(
              "learningPathView"
            );

          if(pathView){
            pathView.style.display =
              "none";
          }

          console.log(
            "SIDEBAR HARD RELOAD — OPENING LESSON:",
            pending.lesson
          );

          await startSelectedUnitLesson(
            pending.lesson
          );

        }
        catch(error){
          console.error(
            "SIDEBAR HARD RELOAD — OPEN FAILED:",
            error
          );
        }

      },
      100
    );

})();
</script>
'''
if bootstrap_marker not in text:
    raise SystemExit('lesson-completion script marker not found')
text = text.replace(bootstrap_marker, bootstrap, 1)

if 'IAKIDS • build 0.6.3' not in text:
    raise SystemExit('expected build 0.6.3 not found')
text = text.replace('IAKIDS • build 0.6.3', 'IAKIDS • build 0.6.4')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.6.3";', 'window.IAKIDS_BUILD_VERSION = "0.6.4";')

p.write_text(text, encoding='utf-8')
