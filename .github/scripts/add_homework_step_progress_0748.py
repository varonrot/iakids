from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

b = backend.read_text(encoding='utf-8')

# -----------------------------------------------------
# 1) Request/response schema: carry pedagogical progress.
# -----------------------------------------------------
if 'progress_context: str | None = None' not in b:
    b, n = re.subn(
        r'(homework_session_id:\s*str\s*\|\s*None\s*=\s*None\s*\n)',
        r'\1    progress_context: str | None = None\n',
        b,
        count=1
    )
    if n != 1:
        raise RuntimeError('could not add progress_context to HomeworkTurnRequest')

if 'completed_step: str | None = None' not in b:
    b, n = re.subn(
        r'(class\s+HomeworkTurnEvaluation\(BaseModel\):\s*\n)',
        r'\1    completed_step: str | None = None\n    next_step: str | None = None\n',
        b,
        count=1
    )
    if n != 1:
        raise RuntimeError('could not extend HomeworkTurnEvaluation')

# -----------------------------------------------------
# 2) Inject progress state into the homework evaluator prompt.
# -----------------------------------------------------
section_start = b.find('def homework_turn(')
if section_start < 0:
    raise RuntimeError('homework_turn function not found')
section_tail = b[section_start:]

if 'PEDAGOGICAL PROGRESS STATE' not in section_tail:
    # Put it immediately before HARD RULES, inside the prompt.
    hard_idx = section_tail.find('HARD RULES:')
    if hard_idx < 0:
        raise RuntimeError('HARD RULES not found in homework_turn')
    progress_block = '''PEDAGOGICAL PROGRESS STATE:\n{req.progress_context or "No earlier step state for this question."}\n\nPROGRESS RULES:\n- Treat every completed step listed above as already learned/accepted. NEVER ask the child to justify it again and NEVER restart from an earlier step.\n- Continue only from NEXT UNRESOLVED STEP.\n- If the child answer correctly completes the next unresolved step, acknowledge it briefly and immediately advance one step.\n- For multi-step math, preserve the chain of operations/results already established. Example pattern only: identify operation -> calculate intermediate result -> use that result in the next operation -> final contextual answer. Do not restart the chain.\n- For reading/science/writing, use the same principle: evidence/idea/structure already established remains completed and the next response advances from there.\n- Populate completed_step with the newest step the child has successfully completed in THIS turn, or leave it empty if none.\n- Populate next_step with the single next unresolved pedagogical action the child should do next, or leave it empty when the worksheet answer is complete.\n\n'''
    section_tail = section_tail[:hard_idx] + progress_block + section_tail[hard_idx:]
    b = b[:section_start] + section_tail

# Strengthen hard rules with explicit anti-regression rule.
start = b.find('HARD RULES:', b.find('def homework_turn('))
if start >= 0:
    end = b.find('""".strip()', start)
    if end >= 0:
        rules = b[start:end]
        if 'Never regress to an already completed pedagogical step' not in rules:
            rules = rules.replace(
                'HARD RULES:\n',
                'HARD RULES:\n0. Never regress to an already completed pedagogical step. The progress state is authoritative for sequencing.\n',
                1
            )
            b = b[:start] + rules + b[end:]

backend.write_text(b, encoding='utf-8')

# -----------------------------------------------------
# 3) Frontend: maintain per-question pedagogical step state.
# -----------------------------------------------------
c = core.read_text(encoding='utf-8')

if 'function getHomeworkQuestionStepState' not in c:
    anchor = '  async function runStructuredHomeworkTurn(answerText){\n'
    if anchor not in c:
        raise RuntimeError('runStructuredHomeworkTurn anchor not found')

    helper = r'''  window.HOMEWORK_QUESTION_STEP_STATE = window.HOMEWORK_QUESTION_STEP_STATE || {};

  function getHomeworkQuestionStepState(question){
    const number = Number(question?.number || 0);
    if(!number) return {completedSteps:[], nextStep:"", attempts:[]};
    if(!window.HOMEWORK_QUESTION_STEP_STATE[number]){
      window.HOMEWORK_QUESTION_STEP_STATE[number] = {
        completedSteps: [],
        nextStep: "",
        attempts: []
      };
    }
    return window.HOMEWORK_QUESTION_STEP_STATE[number];
  }

  function buildHomeworkProgressContext(question){
    const state = getHomeworkQuestionStepState(question);
    const completed = state.completedSteps.length
      ? state.completedSteps.map((s,i)=>`${i+1}. ${s}`).join("\n")
      : "None yet";
    const attempts = state.attempts.length
      ? state.attempts.slice(-4).map((a,i)=>`${i+1}. Child: ${a.child}\n   Teacher: ${a.teacher}`).join("\n")
      : "None yet";
    return `
CURRENT QUESTION NUMBER: ${question?.number || "?"}
COMPLETED PEDAGOGICAL STEPS — immutable, do not repeat or re-justify:
${completed}

NEXT UNRESOLVED STEP:
${state.nextStep || "Determine the first unresolved step from the current question and child answer."}

RECENT ATTEMPTS FOR THIS QUESTION:
${attempts}

SEQUENCING CONTRACT:
Continue from the NEXT UNRESOLVED STEP only. Do not restart the solution. Do not ask again for a step already listed as completed. If the child's new answer completes the next step, advance immediately to the following step.`.trim();
  }

  function updateHomeworkQuestionStepState(question, childAnswer, teacherText, data){
    const state = getHomeworkQuestionStepState(question);
    const completedStep = String(data?.completed_step || "").trim();
    const nextStep = String(data?.next_step || "").trim();

    if(completedStep && !state.completedSteps.includes(completedStep)){
      state.completedSteps.push(completedStep);
    }
    if(nextStep){
      state.nextStep = nextStep;
    }
    state.attempts.push({
      child: String(childAnswer || "").trim(),
      teacher: String(teacherText || "").trim()
    });
    if(state.attempts.length > 6){
      state.attempts = state.attempts.slice(-6);
    }
  }

'''
    c = c.replace(anchor, helper + anchor, 1)

# Send progress_context in every structured homework turn.
if 'progress_context: buildHomeworkProgressContext(current)' not in c:
    c = c.replace(
        '            homework_session_id: window.CURRENT_HOMEWORK_SESSION_ID || null,\n            current_question_number:',
        '            homework_session_id: window.CURRENT_HOMEWORK_SESSION_ID || null,\n            progress_context: buildHomeworkProgressContext(current),\n            current_question_number:',
        1
    )

# Update state on sufficient and insufficient turns before rendering the response.
if 'updateHomeworkQuestionStepState(current, answer, feedbackText, data);' not in c:
    target = '''        const feedbackText = String(
          data?.teacher_response
          || data?.feedback
          || "נכון. התשובה שלך עונה על מה שהשאלה ביקשה."
        ).trim();
'''
    replacement = target + '''
        updateHomeworkQuestionStepState(current, answer, feedbackText, data);
'''
    if target not in c:
        raise RuntimeError('sufficient feedback anchor not found')
    c = c.replace(target, replacement, 1)

if 'updateHomeworkQuestionStepState(current, answer, teacherResponse, data);' not in c:
    target = '''      const teacherResponse = String(
        data?.teacher_response
        || data?.feedback
        || "בואי ננסה שוב ולחשוב רק על השאלה שמופיעה בדף."
      ).trim();
'''
    replacement = target + '''
      updateHomeworkQuestionStepState(current, answer, teacherResponse, data);
'''
    if target not in c:
        raise RuntimeError('insufficient feedback anchor not found')
    c = c.replace(target, replacement, 1)

# Reset state on a new worksheet analysis.
if 'window.HOMEWORK_QUESTION_STEP_STATE = {};' not in c:
    c = c.replace(
        '    initializeHomeworkQuestionState(analysis || {});\n    window.CURRENT_HOMEWORK_SESSION_ID = null;',
        '    initializeHomeworkQuestionState(analysis || {});\n    window.HOMEWORK_QUESTION_STEP_STATE = {};\n    window.CURRENT_HOMEWORK_SESSION_ID = null;',
        1
    )

core.write_text(c, encoding='utf-8')

# -----------------------------------------------------
# 4) Version/cache bump.
# -----------------------------------------------------
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.48";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0748', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.48', i, count=1)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0748', i, count=1)
index.write_text(i, encoding='utf-8')

print('Homework Step Progress Engine added; build 0.7.48')
