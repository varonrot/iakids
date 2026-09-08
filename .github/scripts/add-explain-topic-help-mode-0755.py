from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

MODE_PROMPT = r'''HELP MODE: EXPLAIN THE TOPIC

The child explicitly chose an explanation of the material/topic needed for the current homework question.

Your job in this mode is to TEACH the minimum concept, rule, method, or background knowledge the child needs BEFORE asking them to solve the real worksheet question.

MANDATORY BEHAVIOR:
1. Focus only on the knowledge needed for the current worksheet question. Do not turn this into a broad lesson about the whole subject.
2. Start with a short, direct explanation in age-appropriate language. Do not begin by interrogating the child.
3. Explain the core idea before asking the child to apply it.
4. Keep the explanation concrete: define the idea, show how it works, and identify the key signal/rule/relationship the child should notice.
5. When useful, give ONE short analogous example that is different from the uploaded homework. Use different numbers, names, objects, sentences, text, or context so the example teaches the method without revealing the real answer.
6. Demonstrate the analogous example briefly enough that the child can see the method. Do not create a second full exercise unless needed.
7. After the explanation/example, explicitly return to the child's actual question with wording such as: "עכשיו נחזור לשאלה שלך".
8. Ask at most ONE short application question that helps the child use the newly explained idea on the real worksheet question.
9. Do not give the final answer immediately. The child should apply the explanation to at least one meaningful step unless they are still stuck after several hints.
10. If the child says they still do not understand, simplify the explanation, use a smaller example, or explain only the confusing sub-concept. Do not repeat the same explanation verbatim.
11. If the child already demonstrates understanding of the concept, do not reteach it. Move directly to the next unresolved application step.
12. Respect the active TEACHING STYLE:
   - quantitative_math: explain the relationship/method and show a tiny different numerical example;
   - text_comprehension: explain the reading skill, evidence type, or instruction meaning with a tiny different text example;
   - conceptual_science: explain the needed concept/process and connect it to an observation or different example;
   - language_writing: explain the relevant rule/structure/pattern and show a different sentence or writing example.
13. Keep the response short enough for homework help: explanation first, then one example if useful, then return to the real question.
14. Never drift to unrelated theory, personal discussion, values, or examples that do not help answer the current worksheet question.
15. Preserve PEDAGOGICAL PROGRESS STATE. If a concept or step has already been mastered, continue from the next unresolved step instead of restarting the explanation.

PREFERRED FLOW:
IDENTIFY NEEDED KNOWLEDGE -> EXPLAIN THE CORE IDEA -> OPTIONAL SHORT DIFFERENT EXAMPLE -> RETURN TO THE CHILD'S QUESTION -> ONE APPLICATION STEP -> CONTINUE FROM PROGRESS STATE
'''.strip()

b = backend.read_text(encoding='utf-8')

# Add the second help-mode prompt next to understand_question.
if '"explain_topic": r"""' not in b:
    marker = '"understand_question": r"""'
    start = b.find(marker)
    if start < 0:
        raise RuntimeError('understand_question backend mode prompt not found')
    end = b.find('""".strip(),', start)
    if end < 0:
        raise RuntimeError('understand_question backend mode prompt end not found')
    end += len('""".strip(),')
    insertion = '\n    "explain_topic": r"""\n' + MODE_PROMPT + '\n""".strip(),'
    b = b[:end] + insertion + b[end:]

# Extend resolver.
old = '''def resolve_homework_help_mode(help_mode: str | None) -> tuple[str | None, str]:\n    name = str(help_mode or "").strip()\n    if name == "understand_question":\n        return name, HOMEWORK_HELP_MODE_PROMPTS[name]\n    return None, ""'''
new = '''def resolve_homework_help_mode(help_mode: str | None) -> tuple[str | None, str]:\n    name = str(help_mode or "").strip()\n    if name in HOMEWORK_HELP_MODE_PROMPTS:\n        return name, HOMEWORK_HELP_MODE_PROMPTS[name]\n    return None, ""'''
if old in b:
    b = b.replace(old, new, 1)
elif 'if name in HOMEWORK_HELP_MODE_PROMPTS:' not in b:
    raise RuntimeError('backend help-mode resolver anchor not found')

backend.write_text(b, encoding='utf-8')

# Frontend registry + selection instruction.
c = core.read_text(encoding='utf-8')
if 'explain_topic: `' not in c:
    marker = 'understand_question: `'
    start = c.find(marker)
    if start < 0:
        raise RuntimeError('frontend understand_question mode prompt not found')
    end = c.find('\n`\n  };', start)
    if end < 0:
        raise RuntimeError('frontend mode registry end not found')
    insertion = ',\n    explain_topic: `\n' + MODE_PROMPT.replace('`', '\\`') + '\n`'
    c = c[:end+2] + insertion + c[end+2:]

old_case = '''      case "explain_topic":\n        return "הסבר בקצרה רק את הידע שצריך כדי לענות על השאלה הנוכחית בדף. אל תפתח שיחה כללית, ערכית או אישית ואל תשאל על חיי הילד/ה. אחרי ההסבר חזור מיד לשאלה המקורית ובקש מהילד/ה לנסח תשובה קצרה אליה.";'''
new_case = '''      case "explain_topic":\n        return HOMEWORK_HELP_MODE_PROMPTS.explain_topic;'''
if old_case in c:
    c = c.replace(old_case, new_case, 1)
elif 'case "explain_topic":\n        return HOMEWORK_HELP_MODE_PROMPTS.explain_topic;' not in c:
    raise RuntimeError('frontend explain_topic case anchor not found')

core.write_text(c, encoding='utf-8')

# Version/cache bump to 0.7.55.
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.55";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0755', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'/he/workspace/lesson-completion\.js\?v=\d+', '/he/workspace/lesson-completion.js?v=0755', i, count=1)
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.55', i, count=1)
i = re.sub(r'window\.IAKIDS_BUILD_VERSION = "0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.55";', i, count=1)
index.write_text(i, encoding='utf-8')

print('Added explain_topic help mode; build 0.7.55')
