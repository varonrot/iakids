from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

PROMPT = r'''HELP MODE: SMALL HINT

The child explicitly chose to receive a SMALL HINT for the current homework question.

Your job in this mode is NOT to explain the whole topic, NOT to solve the problem step by step, and NOT to reveal the final answer. Give only the smallest useful clue that moves the child from the current PEDAGOGICAL PROGRESS STATE to the single next unresolved step.

MANDATORY BEHAVIOR:
1. Focus only on the current worksheet question and the next unresolved step.
2. Give ONE hint only in each response.
3. The hint must be short, specific, and actionable. It should narrow where to look, what relation to notice, what rule to recall, what word/data to use, or what first micro-step to try.
4. Do not give a broad explanation of the topic. If the child wanted teaching, that belongs to EXPLAIN THE TOPIC mode.
5. Do not solve several steps at once. If a multi-step task is involved, hint only at the immediate next step.
6. Never reveal the final answer unless the child has already received several increasingly explicit hints and remains genuinely stuck, and the global pedagogy rules allow it.
7. Preserve all completed steps. Never hint toward a step that has already been completed or ask the child to redo it.
8. After the hint, ask at most ONE short question or instruction that lets the child try the hinted step.
9. If the child is still stuck, make the NEXT hint slightly more explicit, but still only for the same unresolved step. Do not restart from the beginning.
10. Respect the active TEACHING STYLE:
   - quantitative_math: point to the needed relation, operation, quantity, or next calculation without doing it for the child;
   - text_comprehension: point to the precise sentence/event/keyword/evidence location and what to notice there;
   - conceptual_science: point to the relevant concept, observation, cause-effect link, or diagram feature;
   - language_writing: point to the relevant grammar rule, word cue, sentence structure, idea component, or writing frame.
11. If the child asks "why?" about the hint, explain only the reasoning behind that hint briefly; do not expand into a full lesson unless the child switches modes.
12. Keep the response concise and age-appropriate. A hint should feel like a nudge, not a mini-lecture.

PREFERRED FLOW:
READ CURRENT PROGRESS -> IDENTIFY SINGLE NEXT UNRESOLVED STEP -> GIVE ONE SMALL SPECIFIC HINT -> ASK CHILD TO TRY THAT STEP -> WAIT
'''.strip()

# Backend registry: append hint mode after explain_topic.
b = backend.read_text(encoding='utf-8')
if '"hint": r"""\nHELP MODE: SMALL HINT' not in b:
    anchor = 'PREFERRED FLOW:\nIDENTIFY NEEDED KNOWLEDGE -> EXPLAIN THE CORE IDEA -> OPTIONAL SHORT DIFFERENT EXAMPLE -> RETURN TO THE CHILD\'S QUESTION -> ONE APPLICATION STEP -> CONTINUE FROM PROGRESS STATE\n""".strip(),\n}'
    if anchor not in b:
        raise RuntimeError('backend help mode registry anchor not found')
    addition = 'PREFERRED FLOW:\nIDENTIFY NEEDED KNOWLEDGE -> EXPLAIN THE CORE IDEA -> OPTIONAL SHORT DIFFERENT EXAMPLE -> RETURN TO THE CHILD\'S QUESTION -> ONE APPLICATION STEP -> CONTINUE FROM PROGRESS STATE\n""".strip(),\n    "hint": r"""\n' + PROMPT + '\n""".strip(),\n}'
    b = b.replace(anchor, addition, 1)
backend.write_text(b, encoding='utf-8')

# Frontend registry and choice mapping.
c = core.read_text(encoding='utf-8')
if 'hint: `\nHELP MODE: SMALL HINT' not in c:
    anchor = 'PREFERRED FLOW:\nIDENTIFY NEEDED KNOWLEDGE -> EXPLAIN THE CORE IDEA -> OPTIONAL SHORT DIFFERENT EXAMPLE -> RETURN TO THE CHILD\'S QUESTION -> ONE APPLICATION STEP -> CONTINUE FROM PROGRESS STATE\n`\n  };'
    if anchor not in c:
        raise RuntimeError('frontend help mode registry anchor not found')
    addition = 'PREFERRED FLOW:\nIDENTIFY NEEDED KNOWLEDGE -> EXPLAIN THE CORE IDEA -> OPTIONAL SHORT DIFFERENT EXAMPLE -> RETURN TO THE CHILD\'S QUESTION -> ONE APPLICATION STEP -> CONTINUE FROM PROGRESS STATE\n`,\n    hint: `\n' + PROMPT.replace('`','\\`') + '\n`\n  };'
    c = c.replace(anchor, addition, 1)

c = c.replace(
    'case "hint":\n        return "תן רמז קטן אחד בלבד שמתייחס ישירות לשאלה הנוכחית בדף. אל תשאל שאלות כלליות או שאלות על חיי הילד/ה. מיד אחרי הרמז בקש מהילד/ה לנסות לענות על השאלה המקורית.";',
    'case "hint":\n        return HOMEWORK_HELP_MODE_PROMPTS.hint;',
    1
)
core.write_text(c, encoding='utf-8')

# Build/cache bump 0.7.55 -> 0.7.56.
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.56";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0756', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.56', i, count=1)
i = re.sub(r'window\.IAKIDS_BUILD_VERSION = "0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.56";', i, count=1)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0756', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added Help Mode 3: hint; build 0.7.56')
