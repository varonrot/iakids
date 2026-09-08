from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

b = backend.read_text(encoding='utf-8')
c = core.read_text(encoding='utf-8')
l = loader.read_text(encoding='utf-8')
i = index.read_text(encoding='utf-8')

MODE_PROMPT = r'''HELP MODE: UNDERSTAND THE QUESTION

The child explicitly chose help understanding what the worksheet question is asking.

Your job in this mode is NOT to solve the exercise and NOT to begin the full solution process. Your job is to make the task itself clear enough that the child knows what they are being asked to do.

MANDATORY BEHAVIOR:
1. Focus only on the current worksheet question.
2. Start by explaining in one or two short sentences what the question is asking the child to find, explain, identify, compare, calculate, write, or prove.
3. Translate difficult wording into simpler age-appropriate language without changing the meaning of the task.
4. Identify the important instruction word(s) or signal(s) in the question, when relevant: for example calculate, explain, compare, according to the text, give a reason, describe, identify, complete, or justify.
5. Identify what information/source the child is expected to use: numbers in the problem, a passage, diagram, table, scientific concept, grammar rule, instructions, or other supplied material.
6. Do NOT calculate the result, reveal the answer, collect all answer components, or walk through the complete solution in this mode.
7. Do NOT immediately interrogate the child. First TEACH what the question means.
8. After the explanation, ask at most ONE short check-for-understanding question whose purpose is only to verify that the child understands the task. The check must not secretly become the first solving step.
9. If a tiny analogous example would make the wording clearer, you may give ONE very short example with completely different content or numbers. The example must illustrate the meaning of the instruction, not solve the uploaded homework.
10. If the child says they still do not understand, simplify the wording further or separate the task into: "what is given" and "what are we being asked to find/do". Do not repeat the same explanation verbatim.
11. Once the child clearly understands what is being asked, stop teaching this mode. Do not continue into a full solution unless the child chooses another help mode or explicitly asks to proceed.
12. Respect the active TEACHING STYLE for how you describe the task: mathematical task language for quantitative work, source/evidence language for text comprehension, concept/process language for science, and rule/structure language for language-writing tasks.

PREFERRED FLOW:
READ THE QUESTION -> SAY IN SIMPLE WORDS WHAT IT ASKS -> IDENTIFY THE SOURCE/INFORMATION TO USE -> OPTIONAL TINY DIFFERENT EXAMPLE -> ONE UNDERSTANDING CHECK -> STOP WHEN THE TASK IS CLEAR
'''.strip()

# 1) Backend request carries the selected help mode on structured turns.
if 'help_mode: str | None = None' not in b:
    anchor = '    progress_context: str | None = None\n'
    if anchor not in b:
        raise RuntimeError('HomeworkTurnRequest progress_context anchor not found')
    b = b.replace(anchor, anchor + '    help_mode: str | None = None\n', 1)

# 2) First help-mode registry entry.
if 'HOMEWORK_HELP_MODE_PROMPTS' not in b:
    anchor = '\ndef resolve_homework_teaching_style(strategy_name: str) -> tuple[str | None, str]:\n'
    pos = b.find(anchor)
    if pos < 0:
        raise RuntimeError('teaching style resolver anchor not found')
    block = '''\nHOMEWORK_HELP_MODE_PROMPTS = {\n    "understand_question": r"""\n''' + MODE_PROMPT + '''\n""".strip(),\n}\n\ndef resolve_homework_help_mode(help_mode: str | None) -> tuple[str | None, str]:\n    name = str(help_mode or "").strip()\n    if name == "understand_question":\n        return name, HOMEWORK_HELP_MODE_PROMPTS[name]\n    return None, ""\n\n'''
    b = b[:pos] + block + b[pos:]

# 3) Resolve and inject active help mode into the structured homework evaluator.
needle = '    style_name, style_instruction = resolve_homework_teaching_style(strategy_name)\n\n    system_prompt = f"""'
if needle in b and 'mode_name, mode_instruction = resolve_homework_help_mode(req.help_mode)' not in b:
    b = b.replace(
        needle,
        '    style_name, style_instruction = resolve_homework_teaching_style(strategy_name)\n    mode_name, mode_instruction = resolve_homework_help_mode(req.help_mode)\n\n    system_prompt = f"""',
        1
    )
elif 'mode_name, mode_instruction = resolve_homework_help_mode(req.help_mode)' not in b:
    raise RuntimeError('structured homework style resolution anchor not found')

needle = '''TEACHING STYLE INSTRUCTION:\n{style_instruction or "No dedicated teaching-style prompt is active for this task yet; keep the existing strategy behavior."}\n\nACTIVE TEACHING STRATEGY:'''
if needle in b and 'ACTIVE HELP MODE:' not in b[b.find('def homework_turn('):]:
    b = b.replace(
        needle,
        '''TEACHING STYLE INSTRUCTION:\n{style_instruction or "No dedicated teaching-style prompt is active for this task yet; keep the existing strategy behavior."}\n\nACTIVE HELP MODE: {mode_name or "default"}\nHELP MODE INSTRUCTION:\n{mode_instruction or "No dedicated help-mode prompt is active; use the normal tutoring flow."}\n\nACTIVE TEACHING STRATEGY:''',
        1
    )
elif 'ACTIVE HELP MODE:' not in b[b.find('def homework_turn('):]:
    raise RuntimeError('system prompt style block anchor not found')

backend.write_text(b, encoding='utf-8')

# 4) Frontend mode registry: first mode only. This controls the initial /chat turn too.
if 'const HOMEWORK_HELP_MODE_PROMPTS' not in c:
    anchor = '  function getChoiceInstruction(choiceId){\n'
    pos = c.find(anchor)
    if pos < 0:
        raise RuntimeError('getChoiceInstruction anchor not found')
    js_block = '''  const HOMEWORK_HELP_MODE_PROMPTS = {\n    understand_question: `\n''' + MODE_PROMPT.replace('`', '\\`') + '''\n`\n  };\n\n'''
    c = c[:pos] + js_block + c[pos:]

# Use the dedicated mode prompt instead of the old short understand-question instruction.
pattern = r'case "understand_question":\s*\n\s*return ".*?";'
replacement = 'case "understand_question":\n        return HOMEWORK_HELP_MODE_PROMPTS.understand_question;'
c, n = re.subn(pattern, replacement, c, count=1, flags=re.S)
if n != 1 and 'return HOMEWORK_HELP_MODE_PROMPTS.understand_question;' not in c:
    raise RuntimeError('could not switch understand_question to dedicated mode prompt')

# Remember the child's mode choice for all subsequent turns.
anchor = '  async function runHomeworkChoiceWithTutor(choice){\n'
if anchor in c and 'window.HOMEWORK_HELP_MODE = String(choice?.id || "").trim() || null;' not in c:
    c = c.replace(anchor, anchor + '    window.HOMEWORK_HELP_MODE = String(choice?.id || "").trim() || null;\n', 1)

# Send mode to /homework-turn.
if 'help_mode: window.HOMEWORK_HELP_MODE || null' not in c:
    anchor = '            progress_context: buildHomeworkProgressContext(current),\n'
    if anchor not in c:
        raise RuntimeError('structured turn progress_context body anchor not found')
    c = c.replace(anchor, anchor + '            help_mode: window.HOMEWORK_HELP_MODE || null,\n', 1)

# Reset mode for a newly analyzed worksheet so a previous session does not leak.
if 'window.HOMEWORK_HELP_MODE = null;' not in c:
    anchor = '    window.HOMEWORK_QUESTION_STEP_STATE = {};\n'
    if anchor in c:
        c = c.replace(anchor, anchor + '    window.HOMEWORK_HELP_MODE = null;\n', 1)

core.write_text(c, encoding='utf-8')

# 5) Visible version/cache bump.
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.54";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0754', l, count=1)
loader.write_text(l, encoding='utf-8')

i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.54', i, count=1)
i = re.sub(r'window\.IAKIDS_BUILD_VERSION = "0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.54";', i, count=1)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0754', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added help mode 1/5: understand_question; build 0.7.54')
