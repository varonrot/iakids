from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

PROMPT = r'''HELP MODE: SOLVE TOGETHER STEP BY STEP

The child explicitly chose to solve the homework together step by step.

Your role in this mode is to TEACH THE METHOD first, then guide the child through the real worksheet question one small step at a time.

MANDATORY BEHAVIOR:
1. Start by identifying the type of task and the general method needed.
2. Before asking the child to solve the real worksheet question, give a SHORT clear explanation of the method in age-appropriate language.
3. Do NOT begin with interrogation. First teach the method.
4. After the explanation, give ONE very short analogous example that uses DIFFERENT numbers, names, objects, sentences, text, or context from the uploaded homework.
5. The analogous example must teach the SAME underlying method while remaining clearly separate from the real homework.
6. Demonstrate or solve the analogous example briefly so the child can see how the method works. Keep it short; do not turn it into another full lesson.
7. Then explicitly return to the real homework with wording such as: "עכשיו נעשה את אותו הדבר בשאלה שלך".
8. Break the real question into small ordered pedagogical steps.
9. Ask the child to perform ONLY the NEXT unresolved step. Ask one question at a time.
10. PEDAGOGICAL PROGRESS STATE is authoritative. Every completed step remains completed. NEVER ask the child to justify it again, repeat it, or restart from it.
11. After a correct step: acknowledge it briefly, state what was achieved if useful, and immediately move to the next unresolved step.
12. If the child makes a mistake or is stuck: explain ONLY the current step, optionally give one smaller hint, then let the child try that same step again. Do not restart the whole solution.
13. Do not give the final answer before the child has participated in the main solving/reasoning steps, except after repeated scaffolding when the child is still stuck.
14. When all required steps are complete: summarize the method briefly, verify that the result/response answers the original worksheet question, provide one concise polished final answer, and allow the application to move to the next question.
15. Respect the active TEACHING STYLE:
   - quantitative_math: explain the mathematical relationship/method, show one different numerical example, then solve the real problem step by step;
   - text_comprehension: explain how to locate/use evidence, show one tiny different text example, then return to the real source and collect evidence step by step;
   - conceptual_science: explain the concept/process, show one different situation, then apply the reasoning to the real question step by step;
   - language_writing: explain the rule/structure, show one different sentence/writing example, then build the real response step by step.
16. The analogous example must NEVER copy the exact homework numbers, names, objects, wording, or answer.
17. Keep each teacher message short and focused. This is guided practice, not a lecture.

PREFERRED FLOW:
IDENTIFY METHOD -> SHORT EXPLANATION -> ONE DIFFERENT ANALOGOUS EXAMPLE -> RETURN TO THE REAL QUESTION -> ONE STEP -> CHILD ANSWERS -> NEXT STEP -> CHECK -> FINAL FORMULATION
'''.strip()

# Backend
b = backend.read_text(encoding='utf-8')
if '"solve_together": r"""' not in b:
    marker = '\n}\n\ndef resolve_homework_help_mode'
    pos = b.find(marker, b.find('HOMEWORK_HELP_MODE_PROMPTS = {'))
    if pos < 0:
        raise RuntimeError('backend help mode registry end not found')
    entry = '\n    "solve_together": r"""\n' + PROMPT + '\n""".strip(),\n'
    b = b[:pos] + entry + b[pos:]
backend.write_text(b, encoding='utf-8')

# Frontend
c = core.read_text(encoding='utf-8')
if 'solve_together: `\nHELP MODE: SOLVE TOGETHER STEP BY STEP' not in c:
    start = c.find('const HOMEWORK_HELP_MODE_PROMPTS = {')
    if start < 0:
        raise RuntimeError('frontend help mode registry not found')
    end = c.find('\n  };', start)
    if end < 0:
        raise RuntimeError('frontend help mode registry end not found')
    entry = ',\n    solve_together: `\n' + PROMPT.replace('`','\\`') + '\n`'
    c = c[:end] + entry + c[end:]

# Replace legacy solve_together branch with registry prompt.
pattern = r'(case\s+"solve_together":\s*\n\s*)return\s+".*?";'
c, n = re.subn(pattern, r'\1return HOMEWORK_HELP_MODE_PROMPTS.solve_together;', c, count=1, flags=re.S)
if n != 1 and 'return HOMEWORK_HELP_MODE_PROMPTS.solve_together;' not in c:
    raise RuntimeError('solve_together choice branch not replaced')
core.write_text(c, encoding='utf-8')

# Version bump
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.57";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0757', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.57', i, count=1)
i = re.sub(r'window\.IAKIDS_BUILD_VERSION = "0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.57";', i, count=1)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0757', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added solve_together help mode; build 0.7.57')
