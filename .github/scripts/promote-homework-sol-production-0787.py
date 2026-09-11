from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'
backend_path = root / 'backend-ai-tutor-he/main.py'

core = core_path.read_text(encoding='utf-8')
backend = backend_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

# ---------------- Backend: promote temporary endpoint to production ----------------
backend = backend.replace('class HomeworkSimpleTestRequest(BaseModel):', 'class HomeworkCoachRequest(BaseModel):')
backend = backend.replace('@app.post("/api/tutor/homework-simple-test")', '@app.post("/api/tutor/homework-coach")')
backend = backend.replace('async def homework_simple_test(', 'async def homework_coach(')
backend = backend.replace('req: HomeworkSimpleTestRequest,', 'req: HomeworkCoachRequest,')
backend = backend.replace('"test_mode": True', '"production_mode": True')

if '/api/tutor/homework-coach' not in backend:
    raise SystemExit('backend production homework coach route was not created')
if 'model="gpt-5.6-sol"' not in backend:
    raise SystemExit('gpt-5.6-sol model missing from production homework coach')

# ---------------- Frontend: remove temporary test choice ----------------
simple_choice = re.compile(
    r'\n\s*\{\n\s*id:\s*"simple_test",\n\s*icon:\s*"[^"]+",\n\s*label:\s*"טסט[^\n]+\n\s*childText:\s*"תלמדי אותי פשוט, שלב אחרי שלב"\n\s*\},',
    re.M,
)
core, removed_choices = simple_choice.subn('', core)
if removed_choices < 1 and 'id: "simple_test"' in core:
    raise SystemExit('could not remove temporary simple_test choice')

# Rename temporary state/function into production names.
core = core.replace('runHomeworkSimpleTest', 'runHomeworkProductionCoach')
core = core.replace('HOMEWORK_SIMPLE_TEST_MODE', 'HOMEWORK_PRODUCTION_COACH_MODE')
core = core.replace('HOMEWORK_SIMPLE_TEST_HISTORY', 'HOMEWORK_PRODUCTION_COACH_HISTORY')
core = core.replace('Simple test auth missing', 'Homework coach auth missing')
core = core.replace('/api/tutor/homework-simple-test', '/api/tutor/homework-coach')
core = core.replace('/* SIMPLE TEST AUTO ADVANCE 0.7.86 */', '/* PRODUCTION HOMEWORK COACH AUTO ADVANCE 0.7.87 */')

# Replace the old temporary button branch with the real solve_together production branch.
branch_pattern = re.compile(
    r'\s*if\(choice\?\.id === "simple_test"\)\{.*?await runHomeworkProductionCoach\(""\);\n\s*return;\n\s*\}\n\s*window\.HOMEWORK_PRODUCTION_COACH_MODE = false;',
    re.S,
)
branch_replacement = '''
    if(choice?.id === "solve_together"){
      window.HOMEWORK_PRODUCTION_COACH_MODE = true;
      window.HOMEWORK_PRODUCTION_COACH_HISTORY = [];
      removeHomeworkHelpOptions();
      setHomeworkSidebarStep(4);
      await runHomeworkProductionCoach("");
      return;
    }
    window.HOMEWORK_PRODUCTION_COACH_MODE = false;'''
core, branch_count = branch_pattern.subn(branch_replacement, core)
if branch_count < 1:
    raise SystemExit('could not promote solve_together to production coach branch')

# Clean model Markdown before rendering/TTS and restore production audio.
old_reply_block = '''    const data=await response.json();
    const reply=String(data?.reply||"").trim();
    if(messageText) window.HOMEWORK_PRODUCTION_COACH_HISTORY.push({role:"user",content:String(messageText)});
    window.HOMEWORK_PRODUCTION_COACH_HISTORY.push({role:"assistant",content:reply});
    if(window.HOMEWORK_PRODUCTION_COACH_HISTORY.length>10) window.HOMEWORK_PRODUCTION_COACH_HISTORY=window.HOMEWORK_PRODUCTION_COACH_HISTORY.slice(-10);
    await renderHomeworkStructuredTeacherMessage(reply);
'''
new_reply_block = '''    const data=await response.json();
    const reply=String(data?.reply||"").trim();
    const displayReply = reply
      .replace(/\\*\\*/g, "")
      .replace(/^#{1,6}\\s*/gm, "")
      .trim();
    if(messageText) window.HOMEWORK_PRODUCTION_COACH_HISTORY.push({role:"user",content:String(messageText)});
    window.HOMEWORK_PRODUCTION_COACH_HISTORY.push({role:"assistant",content:displayReply});
    if(window.HOMEWORK_PRODUCTION_COACH_HISTORY.length>10) window.HOMEWORK_PRODUCTION_COACH_HISTORY=window.HOMEWORK_PRODUCTION_COACH_HISTORY.slice(-10);
    await Promise.all([
      renderHomeworkStructuredTeacherMessage(displayReply),
      playHomeworkTeacherAudio(displayReply)
    ]);
'''
if old_reply_block in core:
    core = core.replace(old_reply_block, new_reply_block)
else:
    # tolerate whitespace drift
    core, n = re.subn(
        r'    const data=await response\.json\(\);\n    const reply=String\(data\?\.reply\|\|""\)\.trim\(\);\n    if\(messageText\) window\.HOMEWORK_PRODUCTION_COACH_HISTORY\.push\(\{role:"user",content:String\(messageText\)\}\);\n    window\.HOMEWORK_PRODUCTION_COACH_HISTORY\.push\(\{role:"assistant",content:reply\}\);\n    if\(window\.HOMEWORK_PRODUCTION_COACH_HISTORY\.length>10\) window\.HOMEWORK_PRODUCTION_COACH_HISTORY=window\.HOMEWORK_PRODUCTION_COACH_HISTORY\.slice\(-10\);\n    await renderHomeworkStructuredTeacherMessage\(reply\);\n',
        new_reply_block,
        core,
    )
    if n < 1:
        raise SystemExit('could not add production render/audio handling')

# Auto-advance should save the child's own final formulation to the notebook.
needle = '''      const completedQuestion = setHomeworkQuestionAnswered(String(messageText || "").trim());
      window.HOMEWORK_PRODUCTION_COACH_HISTORY = [];
'''
replacement = '''      const completedQuestion = setHomeworkQuestionAnswered(String(messageText || "").trim());
      if(completedQuestion?.answer && typeof window.writeHomeworkNotebookAnswer === "function"){
        await window.writeHomeworkNotebookAnswer(
          completedQuestion.number,
          completedQuestion.answer
        );
      }
      window.HOMEWORK_PRODUCTION_COACH_HISTORY = [];
'''
if needle in core:
    core = core.replace(needle, replacement)
else:
    raise SystemExit('could not attach child answer to notebook before auto-advance')

# Remove any lingering test badge/text and temporary identifiers.
core = re.sub(r'\n\s*document\.querySelectorAll\(\'\.homework-simple-test-badge\'\).*?chat\.appendChild\(badge\);\n\s*\}\n', '\n', core, flags=re.S)
core = core.replace('TEST MODE · GPT-5.6 SOL', '')
core = core.replace('homework-simple-test-badge', '')

if 'id: "simple_test"' in core:
    raise SystemExit('temporary test button still present')
if '/api/tutor/homework-simple-test' in core:
    raise SystemExit('temporary endpoint still referenced by frontend')
if 'HOMEWORK_SIMPLE_TEST' in core:
    raise SystemExit('temporary test state still referenced by frontend')

# ---------------- Version/cache bump ----------------
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.87";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0787', loader, count=1)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.87', index)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0787', index)

core_path.write_text(core, encoding='utf-8')
backend_path.write_text(backend, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

print('Promoted GPT-5.6 Sol homework coach to production; removed temporary test mode; build 0.7.87')
