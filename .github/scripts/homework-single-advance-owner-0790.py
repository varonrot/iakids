from pathlib import Path
import re

root = Path('.')
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

# In production-coach mode, only runHomeworkProductionCoach may advance the worksheet question.
old_setter = '''  function setHomeworkQuestionAnswered(answerText){
    const current = getCurrentHomeworkQuestion();
    if(!current) return null;
'''
new_setter = '''  function setHomeworkQuestionAnswered(answerText){
    if(
      window.HOMEWORK_PRODUCTION_COACH_MODE === true
      && window.HOMEWORK_PRODUCTION_ADVANCE_AUTHORIZED !== true
    ){
      console.warn("HOMEWORK QUESTION ADVANCE BLOCKED: production coach owns progression");
      return null;
    }

    const current = getCurrentHomeworkQuestion();
    if(!current) return null;
'''
if old_setter not in core:
    raise SystemExit('setHomeworkQuestionAnswered anchor not found')
core = core.replace(old_setter, new_setter, 1)

old_accept = '''    if(finalAnswerAccepted){
      const completedQuestion = setHomeworkQuestionAnswered(String(messageText || "").trim());
      if(completedQuestion?.answer && typeof window.writeHomeworkNotebookAnswer === "function"){
'''
new_accept = '''    if(finalAnswerAccepted){
      window.HOMEWORK_PRODUCTION_ADVANCE_AUTHORIZED = true;
      let completedQuestion = null;
      try{
        completedQuestion = setHomeworkQuestionAnswered(String(messageText || "").trim());
      }finally{
        window.HOMEWORK_PRODUCTION_ADVANCE_AUTHORIZED = false;
      }
      if(completedQuestion?.answer && typeof window.writeHomeworkNotebookAnswer === "function"){
'''
if old_accept not in core:
    raise SystemExit('production final-answer advance anchor not found')
core = core.replace(old_accept, new_accept, 1)

# Reset the authorization gate whenever a new homework worksheet is initialized.
old_init = '''    window.CURRENT_HOMEWORK_ANSWERED_QUESTIONS = [];
    window.HOMEWORK_STRUCTURED_ACTIVE = false;
'''
new_init = '''    window.CURRENT_HOMEWORK_ANSWERED_QUESTIONS = [];
    window.HOMEWORK_STRUCTURED_ACTIVE = false;
    window.HOMEWORK_PRODUCTION_ADVANCE_AUTHORIZED = false;
'''
if old_init not in core:
    raise SystemExit('homework initialize anchor not found')
core = core.replace(old_init, new_init, 1)

# Bump cache/build.
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.90";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0790', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0790', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.90', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.90";', index, count=1)

core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
print('Locked homework progression to production coach owner; build 0.7.90')
