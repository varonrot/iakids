from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

b = backend.read_text(encoding='utf-8')

STYLE_PROMPT = r'''TEACHING STYLE: QUANTITATIVE / MATHEMATICS

You are teaching a child how to solve a mathematical or quantitative task.

Your goal is not only to reach the correct result, but to teach the child how to understand the problem, choose a method, and solve it independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify what information is given, what the question asks, and what mathematical relationship, operation, or method is needed.
2. Do not jump directly to calculation before the child understands what needs to be found.
3. Break the solution into small logical steps.
4. Teach one step at a time. Do not ask several calculations or reasoning steps in one message.
5. If the child already completed a step correctly: acknowledge it briefly, do not ask them to explain it again, do not repeat the same reasoning, and continue immediately to the next unresolved step.
6. If the child makes a mistake: identify the specific step where the mistake occurred, explain only that step, give a focused hint or simpler sub-step, then let the child try again.
7. If the task involves fractions, percentages, ratios, multiplication, division, measurement, geometry, or multi-step word problems, first explain the underlying relationship before asking for the calculation.
8. When useful, teach the method with ONE very short analogous example using different numbers, names, objects, or context from the child's homework.
9. The analogous example must be short and serve only to demonstrate the method. Never reuse the exact numbers or objects from the uploaded homework.
10. After the example, explicitly return to the child's task and apply the same method step by step.
11. Do not give the final numerical answer too early. The child should participate in the main reasoning or calculation steps.
12. At the end: summarize the calculation briefly, verify that the result answers the original question, and give the final answer with the correct unit or context.
13. For word problems, always connect the final number back to what it represents.
14. Keep explanations short, concrete, and appropriate for the child's grade.
15. Avoid unnecessary formulas or terminology when a simpler explanation is enough.

PREFERRED FLOW:
UNDERSTAND THE PROBLEM -> IDENTIFY GIVEN INFORMATION -> IDENTIFY WHAT IS ASKED -> CHOOSE METHOD -> SHORT ANALOGOUS EXAMPLE IF NEEDED -> SOLVE ONE STEP AT A TIME -> CHECK -> FINAL ANSWER
'''.strip()

# Add the first of the new 4-style registry. Do not alter the other subjects yet.
if 'HOMEWORK_TEACHING_STYLE_PROMPTS' not in b:
    anchor = 'HOMEWORK_TEACHING_STRATEGIES = {'
    pos = b.find(anchor)
    if pos < 0:
        raise RuntimeError('HOMEWORK_TEACHING_STRATEGIES anchor not found')
    end = b.find('\n}\n\ndef resolve_homework_teaching_strategy', pos)
    if end < 0:
        raise RuntimeError('HOMEWORK_TEACHING_STRATEGIES end not found')
    end += len('\n}\n')
    registry = '''\nHOMEWORK_TEACHING_STYLE_PROMPTS = {\n    "quantitative_math": r"""\n''' + STYLE_PROMPT + '''\n""".strip(),\n}\n\ndef resolve_homework_teaching_style(strategy_name: str) -> tuple[str | None, str]:\n    # First new teaching style: math / quantitative.\n    # The remaining three styles will be added separately.\n    if str(strategy_name or "").strip() == "math_problem":\n        return "quantitative_math", HOMEWORK_TEACHING_STYLE_PROMPTS["quantitative_math"]\n    return None, ""\n\n'''
    b = b[:end] + registry + b[end:]

# Resolve the style next to the existing fine-grained strategy.
needle = '''    strategy_name, strategy_instruction = resolve_homework_teaching_strategy(\n        req.current_question,\n        req.source_text\n    )\n\n    system_prompt = f"""'''
if needle in b and 'style_name, style_instruction = resolve_homework_teaching_style(strategy_name)' not in b:
    repl = '''    strategy_name, strategy_instruction = resolve_homework_teaching_strategy(\n        req.current_question,\n        req.source_text\n    )\n    style_name, style_instruction = resolve_homework_teaching_style(strategy_name)\n\n    system_prompt = f"""'''
    b = b.replace(needle, repl, 1)
elif 'style_name, style_instruction = resolve_homework_teaching_style(strategy_name)' not in b:
    raise RuntimeError('homework strategy resolution anchor not found')

# Inject style before the existing strategy block. It is active only for math for now.
needle = '''{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}\n\nACTIVE TEACHING STRATEGY: {strategy_name}\nSTRATEGY INSTRUCTION:\n{strategy_instruction}\n'''
if needle in b and 'ACTIVE TEACHING STYLE:' not in b[b.find('def homework_turn('):]:
    repl = '''{HOMEWORK_GLOBAL_PEDAGOGY_PROMPT}\n\nACTIVE TEACHING STYLE: {style_name or "legacy"}\nTEACHING STYLE INSTRUCTION:\n{style_instruction or "No dedicated teaching-style prompt is active for this task yet; keep the existing strategy behavior."}\n\nACTIVE TEACHING STRATEGY: {strategy_name}\nSTRATEGY INSTRUCTION:\n{strategy_instruction}\n'''
    b = b.replace(needle, repl, 1)
elif 'ACTIVE TEACHING STYLE:' not in b[b.find('def homework_turn('):]:
    raise RuntimeError('system prompt strategy block anchor not found')

backend.write_text(b, encoding='utf-8')

# Visible build bump so tests can be tied to this backend behavior revision.
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.50";', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.50', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added first dedicated teaching style: quantitative_math; build 0.7.50')
