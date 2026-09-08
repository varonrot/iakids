from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

MODE_PROMPT = r'''HELP MODE: CHECK THE CHILD'S ANSWER

The child explicitly chose: "check an answer I wrote".

Your role in this mode is to evaluate the CHILD'S OWN answer to the CURRENT worksheet question, explain what is correct and what still needs improvement, and help the child repair the answer independently.

MANDATORY BEHAVIOR:
1. If the child has not yet supplied an answer, do NOT solve the worksheet question. Ask the child to type or say the answer they wrote, and stop.
2. Once an answer is supplied, compare it only with what the CURRENT question requires and with the provided source/data/concept. Do not require extra details that the worksheet does not ask for.
3. Judge meaning, reasoning and completeness — not exact wording. A differently worded answer can be fully correct.
4. Start feedback with a precise statement of what is correct in the child's answer. Do not use praise alone.
5. If something is missing or incorrect, identify ONLY the specific missing/incorrect part and explain why it matters for this question.
6. Do not immediately replace a partial answer with the full correct answer. Give ONE focused repair instruction, clue, source cue, calculation check, rule cue, or sentence frame, then let the child improve the answer.
7. If the answer contains a mathematical calculation, check both the method and result. If one step is wrong, point to that exact step rather than restarting the entire problem.
8. If the answer depends on a text/source, verify that the answer is supported by the source. Point to the precise relevant evidence if correction is needed; never invent evidence.
9. If the answer is scientific, check that the relevant concept and the required cause/process/evidence connection are correct.
10. If the answer is language/writing, separate content correctness from wording/grammar. Correct only what is needed for the task and grade level.
11. Respect PEDAGOGICAL PROGRESS STATE: any step already established as correct remains completed. Never make the child re-prove it.
12. If the answer is already sufficient, say specifically why it answers the question, mark it sufficient, and provide ONE concise polished formulation only if useful.
13. When the answer is sufficient, do not keep searching for optional details. Allow the application to complete the question and move on.
14. Ask at most ONE repair question/action at a time.
15. Keep feedback short, clear, concrete, supportive, and grade-appropriate.

MODE-SPECIFIC FLOW:
NO CHILD ANSWER YET -> ASK FOR THE CHILD'S ANSWER -> CHECK AGAINST CURRENT QUESTION/SOURCE -> STATE WHAT IS CORRECT -> IDENTIFY ONE MISSING/WRONG PART IF ANY -> GIVE ONE REPAIR STEP -> CHILD REVISES -> RECHECK -> MARK SUFFICIENT -> OPTIONAL POLISHED FORMULATION
'''.strip()

b = backend.read_text(encoding='utf-8')

# Add fifth help mode to the backend registry.
if '"check_answer": r"""' not in b:
    marker = '\n}\n\ndef resolve_homework_help_mode'
    pos = b.find(marker, b.find('HOMEWORK_HELP_MODE_PROMPTS = {'))
    if pos < 0:
        raise RuntimeError('backend help-mode registry end not found')
    entry = ',\n    "check_answer": r"""\n' + MODE_PROMPT + '\n""".strip()\n'
    # Avoid a double comma when the previous item already ends with comma.
    before = b[:pos].rstrip()
    if before.endswith(','):
        entry = '\n    "check_answer": r"""\n' + MODE_PROMPT + '\n""".strip()\n'
    b = b[:pos] + entry + b[pos:]

backend.write_text(b, encoding='utf-8')

c = core.read_text(encoding='utf-8')

# Add fifth help mode to frontend registry.
if 'check_answer: `' not in c:
    start = c.find('const HOMEWORK_HELP_MODE_PROMPTS = {')
    if start < 0:
        raise RuntimeError('frontend help-mode registry not found')
    end = c.find('\n  };', start)
    if end < 0:
        raise RuntimeError('frontend help-mode registry end not found')
    prefix = c[:end].rstrip()
    sep = '' if prefix.endswith(',') else ','
    entry = sep + '\n    check_answer: `\n' + MODE_PROMPT.replace('`', '\\`') + '\n`\n'
    c = c[:end] + entry + c[end:]

# Wire the existing check-answer button to the dedicated prompt.
pattern = r'(case\s+"check_answer":\s*\n\s*)return\s+"[\s\S]*?";'
if re.search(pattern, c):
    c = re.sub(pattern, r'\1return HOMEWORK_HELP_MODE_PROMPTS.check_answer;', c, count=1)
elif 'case "check_answer":' in c and 'HOMEWORK_HELP_MODE_PROMPTS.check_answer' not in c:
    raise RuntimeError('check_answer case exists but could not patch it safely')

core.write_text(c, encoding='utf-8')

# Version/cache bump.
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.58";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0758', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.58', i, count=1)
i = re.sub(r'window\.IAKIDS_BUILD_VERSION = "0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.58";', i, count=1)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0758', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added fifth homework help mode: check_answer; build 0.7.58')
