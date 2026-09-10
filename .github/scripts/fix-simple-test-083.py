from pathlib import Path

BACKEND = Path('backend-ai-tutor-he/main.py')
CORE = Path('he/workspace/lesson-completion-core.js')
INDEX = Path('he/workspace/index.html')

backend = BACKEND.read_text(encoding='utf-8')
core = CORE.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# GPT-5.6 Sol chat-completions only supports the default temperature.
backend = backend.replace(
'''    response = (await aclient.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages,
        temperature=0.3
    ))
''',
'''    response = (await aclient.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages
    ))
''',
1
)

# Make test mode unmistakable in the UI.
old_simple = '''    if(choice?.id === "simple_test"){
      window.HOMEWORK_SIMPLE_TEST_MODE = true;
      window.HOMEWORK_SIMPLE_TEST_HISTORY = [];
      removeHomeworkHelpOptions();
      setHomeworkSidebarStep(4);
      await runHomeworkSimpleTest("");
      return;
    }
'''
new_simple = '''    if(choice?.id === "simple_test"){
      window.HOMEWORK_SIMPLE_TEST_MODE = true;
      window.HOMEWORK_SIMPLE_TEST_HISTORY = [];
      removeHomeworkHelpOptions();
      setHomeworkSidebarStep(4);
      document.querySelectorAll('.homework-simple-test-badge').forEach(el=>el.remove());
      const chat = document.querySelector('.lesson-chat-workspace');
      if(chat){
        const badge = document.createElement('div');
        badge.className = 'homework-simple-test-badge';
        badge.textContent = 'TEST MODE · GPT-5.6 SOL';
        badge.style.cssText = 'position:absolute;top:18px;left:18px;z-index:90;padding:6px 10px;border-radius:999px;background:#ff9f1a;color:#08111f;font:900 10px Heebo,Arial,sans-serif;box-shadow:0 0 16px rgba(255,159,26,.35);direction:ltr';
        chat.appendChild(badge);
      }
      await runHomeworkSimpleTest("");
      return;
    }
'''
if old_simple in core:
    core = core.replace(old_simple, new_simple, 1)

# Never disguise a test-endpoint failure as a normal tutor response.
old_catch = '''    catch(error){
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
new_catch = '''    catch(error){
      console.error("HOMEWORK HELP OPTION FAILED:", error);

      if(choice.id === "simple_test"){
        await renderHomeworkStructuredTeacherMessage("טסט GPT-5.6 נכשל טכנית. לא עברתי למסלול הרגיל.");
        return;
      }

      // Normal modes keep their existing deterministic fallback.
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
if old_catch in core:
    core = core.replace(old_catch, new_catch, 1)
else:
    raise SystemExit('simple-test catch anchor not found')

# Cache bust core loader and visible workspace build.
index = index.replace('/he/workspace/lesson-completion.js?v=0782', '/he/workspace/lesson-completion.js?v=0783')
for old in ('0.7.82','0.7.81','0.7.80'):
    index = index.replace(f'IAKIDS • build {old}', 'IAKIDS • build 0.7.83')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{old}";', 'window.IAKIDS_BUILD_VERSION = "0.7.83";')

# Ensure the extension loader itself also busts the core cache.
ext = Path('he/workspace/lesson-completion.js')
ext_text = ext.read_text(encoding='utf-8')
ext_text = ext_text.replace('/he/workspace/lesson-completion-core.js?v=0734', '/he/workspace/lesson-completion-core.js?v=0783')
ext_text = ext_text.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.76";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.83";')
ext.write_text(ext_text, encoding='utf-8')

BACKEND.write_text(backend, encoding='utf-8')
CORE.write_text(core, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Fixed simple test endpoint temperature + no-fallback test mode; build 0.7.83')
