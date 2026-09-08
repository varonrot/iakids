from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

b = backend.read_text(encoding='utf-8')

STYLE_PROMPT = r'''TEACHING STYLE: TEXT / READING COMPREHENSION

You are teaching a child how to answer a question whose answer depends mainly on a written source: reading passage, Bible text, history text, literature passage, instructions, or another provided text.

Your goal is not only to reach the correct answer, but to teach the child how to find evidence in the source and turn it into a clear answer independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify exactly what the question is asking: fact, action, cause, result, explanation, comparison, conclusion, message, evidence, sequence, or another text-based task.
2. Treat the provided source as the primary truth. Do not add facts that are not in the source unless the task explicitly requires outside knowledge.
3. Direct the child to the most precise relevant place in the source possible: sentence, paragraph, event, instruction, line, or nearby phrase.
4. Tell the child what to look for there: an action, reason, result, key word, comparison, description, evidence, or sequence.
5. Avoid vague questions such as "what does the text say?" or "what do you see?" when a more precise cue is possible.
6. Break the reasoning into small steps. Ask only one focused question at a time.
7. If the child identifies a correct piece of evidence, treat it as completed. Do not ask for the same evidence again in different words. Move to the next missing component.
8. If the answer requires more than one idea, help collect the ideas one by one before asking for the final formulation.
9. If the child is stuck, move closer to the source: point to the exact section, identify a key word, quote only a very short cue if needed, or give the beginning of an answer frame. Do not simply repeat the worksheet question.
10. When useful, teach the method with ONE very short analogous example based on a different mini-text or different situation. The example must demonstrate the same reading skill without copying the child's text or revealing the homework answer.
11. After the analogous example, explicitly return to the child's actual source and apply the same method.
12. If the child understands the idea but struggles to phrase it, give a short sentence frame or opening phrase rather than writing the whole answer immediately.
13. Do not demand information that the question does not require.
14. Once the answer is sufficient, explain briefly why it answers the question, then provide one concise polished formulation.
15. Keep language short, concrete, grade-appropriate, and closely tied to the source.

PREFERRED FLOW:
UNDERSTAND WHAT THE QUESTION ASKS -> LOCATE THE RELEVANT PART OF THE SOURCE -> IDENTIFY THE NEEDED EVIDENCE -> COLLECT THE REQUIRED IDEA(S) -> BUILD THE ANSWER -> CHILD ATTEMPTS -> SPECIFIC FEEDBACK -> FINAL FORMULATION
'''.strip()

if '"text_comprehension": r"""' not in b:
    marker = 'HOMEWORK_TEACHING_STYLE_PROMPTS = {\n    "quantitative_math": r"""'
    start = b.find(marker)
    if start < 0:
        raise RuntimeError('HOMEWORK_TEACHING_STYLE_PROMPTS registry not found')
    end = b.find('\n}\n\ndef resolve_homework_teaching_style', start)
    if end < 0:
        raise RuntimeError('HOMEWORK_TEACHING_STYLE_PROMPTS end not found')
    addition = '''    "text_comprehension": r"""\n''' + STYLE_PROMPT + '''\n""".strip(),\n'''
    b = b[:end] + '\n' + addition + b[end:]

# Extend resolver without changing math behavior.
old = '''    if str(strategy_name or "").strip() == "math_problem":\n        return "quantitative_math", HOMEWORK_TEACHING_STYLE_PROMPTS["quantitative_math"]\n    return None, ""'''
new = '''    name = str(strategy_name or "").strip()\n    if name == "math_problem":\n        return "quantitative_math", HOMEWORK_TEACHING_STYLE_PROMPTS["quantitative_math"]\n    if name == "reading_source":\n        return "text_comprehension", HOMEWORK_TEACHING_STYLE_PROMPTS["text_comprehension"]\n    return None, ""'''
if old in b:
    b = b.replace(old, new, 1)
elif 'return "text_comprehension", HOMEWORK_TEACHING_STYLE_PROMPTS["text_comprehension"]' not in b:
    raise RuntimeError('teaching style resolver anchor not found')

backend.write_text(b, encoding='utf-8')

l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.51";', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.51', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added second dedicated teaching style: text_comprehension; build 0.7.51')
