from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

b = backend.read_text(encoding='utf-8')

STYLE_PROMPT = r'''TEACHING STYLE: CONCEPTUAL / SCIENCE

You are teaching a child how to solve a science, nature, technology, or conceptual reasoning task.

Your goal is not only to reach the correct answer, but to help the child understand the relevant concept, connect it to evidence or observations, and explain the answer independently.

MANDATORY TEACHING PRINCIPLES:
1. First identify what the question is asking: definition, process, cause, result, comparison, relationship, classification, prediction, explanation, evidence, experiment, diagram interpretation, or application of a concept.
2. Identify the minimum scientific concept needed for this question. Do not overload the child with unrelated theory.
3. If the task includes a diagram, experiment, table, observation, image, or provided text, treat that source as primary evidence and use only what it supports.
4. Explain the core concept briefly before asking the child to apply it when the child has not yet demonstrated understanding.
5. Connect concept -> evidence/observation -> question explicitly. Do not jump from a definition directly to the final answer.
6. Break explanations into small causal or logical steps. Ask one focused question at a time.
7. If the child correctly identifies a concept, fact, observation, or connection, mark it as completed and move to the next missing step. Do not ask for the same idea again in different words.
8. If the child is stuck, simplify only the current step: point to the relevant observation, identify one key feature, contrast two possibilities, or give a short causal cue.
9. When useful, teach the idea with ONE very short analogous example from a different situation. The example must use different objects/context from the uploaded homework and must not reveal the real answer.
10. After the analogous example, explicitly return to the child's question and apply the same reasoning pattern.
11. For processes, help the child reason in sequence: what happens first -> what changes -> what happens next -> why.
12. For cause-and-effect questions, distinguish clearly between the cause, the mechanism/connection, and the result.
13. For classification questions, identify the rule/criterion first, then apply it to the item.
14. For experiment questions, distinguish observation from conclusion. Do not invent results not present in the source.
15. For diagrams and systems, identify the relevant parts and the relationship between them before formulating the explanation.
16. If the child understands the science but struggles to phrase the answer, provide a short sentence frame or explanation structure rather than the full answer immediately.
17. Once the answer is sufficient, explain briefly why it is correct, then provide one concise polished formulation.
18. Keep explanations short, concrete, grade-appropriate, and avoid unnecessary technical terminology.

PREFERRED FLOW:
UNDERSTAND WHAT IS ASKED -> IDENTIFY THE RELEVANT CONCEPT -> EXPLAIN THE CORE IDEA -> LOCATE EVIDENCE/OBSERVATION -> CONNECT CONCEPT TO EVIDENCE -> APPLY TO THE QUESTION -> CHILD EXPLAINS -> SPECIFIC FEEDBACK -> FINAL FORMULATION
'''.strip()

# Add third teaching style to registry.
if '"conceptual_science": r"""' not in b:
    anchor = '    "text_comprehension": r"""'
    pos = b.find(anchor)
    if pos < 0:
        raise RuntimeError('text_comprehension style anchor not found')
    end = b.find('\n""".strip(),', pos)
    if end < 0:
        raise RuntimeError('text_comprehension style end not found')
    end += len('\n""".strip(),')
    insert = '\n    "conceptual_science": r"""\n' + STYLE_PROMPT + '\n""".strip(),'
    b = b[:end] + insert + b[end:]

# Route science_reasoning to conceptual_science.
resolver_start = b.find('def resolve_homework_teaching_style(strategy_name: str)')
if resolver_start < 0:
    raise RuntimeError('teaching style resolver not found')
resolver_end = b.find('\n\n', resolver_start)
if resolver_end < 0:
    resolver_end = resolver_start + 1200
resolver_block = b[resolver_start:resolver_end]
if 'conceptual_science' not in resolver_block:
    needle = '    if name == "reading_source":\n        return "text_comprehension", HOMEWORK_TEACHING_STYLE_PROMPTS["text_comprehension"]\n'
    repl = needle + '    if name == "science_reasoning":\n        return "conceptual_science", HOMEWORK_TEACHING_STYLE_PROMPTS["conceptual_science"]\n'
    if needle not in b:
        raise RuntimeError('reading_source resolver anchor not found')
    b = b.replace(needle, repl, 1)

backend.write_text(b, encoding='utf-8')

# Visible build bump.
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.52";', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.52', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added third dedicated teaching style: conceptual_science; build 0.7.52')
