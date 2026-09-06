from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''    const { data: sessionData } = await sb.auth.getSession();
    const session = sessionData.session;
    if(!session){
      throw new Error("No active session");
    }
'''
new = '''    const token = await getHomeworkAccessToken();
    if(!token){
      throw new Error("No active session");
    }

    const kidId = getHomeworkKidId();
    if(!kidId){
      throw new Error("Homework kid id missing");
    }
'''
if old not in core:
    raise SystemExit('old homework choice auth block not found')
core = core.replace(old, new, 1)

old = '''          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          message,
          kid_id: CURRENT_KID.id
        })
'''
new = '''          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          message,
          kid_id: kidId
        })
'''
if old not in core:
    raise SystemExit('homework choice request payload not found')
core = core.replace(old, new, 1)

old = '''    if(data?.message || data?.text || data?.response){
      const homeworkReply = data.message || data.text || data.response;
      addMessage("assistant", homeworkReply);
      await playHomeworkTeacherAudio(homeworkReply);
      return;
    }

    console.error("Invalid homework tutor response:", data);
    addMessage("assistant", "אני כאן. נסה לבחור שוב איך תרצה שאעזור.");
'''
new = '''    if(data?.message || data?.text || data?.response){
      const homeworkReply = data.message || data.text || data.response;
      await Promise.all([
        renderHomeworkStructuredTeacherMessage(homeworkReply),
        playHomeworkTeacherAudio(homeworkReply)
      ]);
      return;
    }

    console.error("Invalid homework tutor response:", data);
    const fallbackText = `נתחיל מהשאלה הראשונה: ${currentQuestion}`;
    await Promise.all([
      renderHomeworkStructuredTeacherMessage(fallbackText),
      playHomeworkTeacherAudio(fallbackText)
    ]);
'''
if old not in core:
    raise SystemExit('homework choice fallback block not found')
core = core.replace(old, new, 1)

old = '''    catch(error){
      console.error("HOMEWORK HELP OPTION FAILED:", error);
      addMessage("assistant", "לא הצלחתי להתחיל את העזרה. נסה שוב בעוד רגע.");
      renderHomeworkHelpOptions();
    }
'''
new = '''    catch(error){
      console.error("HOMEWORK HELP OPTION FAILED:", error);

      // Do not throw the child back to the option menu. The worksheet and
      // current-question state already exist, so continue with a deterministic
      // first step even if the general tutor-chat request fails.
      const current = getCurrentHomeworkQuestion();
      const fallbackText = current
        ? `נתחיל מהשאלה ${current.number}: ${current.text}`
        : "נתחיל מהשאלה הראשונה בדף ונפתור אותה יחד.";

      await Promise.all([
        renderHomeworkStructuredTeacherMessage(fallbackText),
        playHomeworkTeacherAudio(fallbackText)
      ]);
    }
'''
if old not in core:
    raise SystemExit('homework help option catch block not found')
core = core.replace(old, new, 1)

# Avoid white legacy bubbles for missing-analysis branch too.
core = core.replace(
    '      addMessage("assistant", "לא מצאתי את התרגיל שהעלית. אפשר להעלות אותו שוב?");',
    '      await renderHomeworkStructuredTeacherMessage("לא מצאתי את התרגיל שהעלית. אפשר להעלות אותו שוב?");',
    1
)

# Bump build/cache.
index = index.replace('IAKIDS • build 0.7.31', 'IAKIDS • build 0.7.32')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.31";', 'window.IAKIDS_BUILD_VERSION = "0.7.32";')
index = index.replace('/he/workspace/lesson-completion.js?v=0731', '/he/workspace/lesson-completion.js?v=0732')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.31";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.32";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0731', '/he/workspace/lesson-completion-core.js?v=0732')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Homework help start hardened: real auth/kid context + dark fallback + no option reset; build 0.7.32')

# trigger 0.7.32
