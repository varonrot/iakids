from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
LOADER = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

marker = '/* SIMPLE TEST AUTO ADVANCE 0.7.86 */'
if marker not in core:
    old = '''    await renderHomeworkStructuredTeacherMessage(reply);\n    return true;\n  }\n'''
    new = '''    await renderHomeworkStructuredTeacherMessage(reply);\n\n    /* SIMPLE TEST AUTO ADVANCE 0.7.86 */\n    const normalizedReply = reply\n      .replace(/\\*\\*/g, "")\n      .replace(/\\s+/g, " ")\n      .trim();\n\n    const finalAnswerAccepted = Boolean(String(messageText || "").trim()) && (\n      /התשובה\\s+נכונה/.test(normalizedReply) ||\n      /נכונה[, ]+מלאה/.test(normalizedReply) ||\n      /מנוסחת\\s+היטב/.test(normalizedReply) ||\n      /ענית\\s+תשובה\\s+מלאה/.test(normalizedReply)\n    );\n\n    if(finalAnswerAccepted){\n      const completedQuestion = setHomeworkQuestionAnswered(String(messageText || "").trim());\n      window.HOMEWORK_SIMPLE_TEST_HISTORY = [];\n\n      const nextQuestion = getCurrentHomeworkQuestion ? getCurrentHomeworkQuestion() : null;\n      if(nextQuestion){\n        await new Promise(resolve => setTimeout(resolve, 500));\n        await renderHomeworkStructuredTeacherMessage(`מעולה. נעבור לשאלה ${nextQuestion.number}.`);\n        await new Promise(resolve => setTimeout(resolve, 350));\n        await runHomeworkSimpleTest("");\n      }else{\n        setHomeworkSidebarStep(5);\n        await new Promise(resolve => setTimeout(resolve, 450));\n        await renderHomeworkStructuredTeacherMessage("סיימנו את כל השאלות בדף. כל הכבוד!");\n      }\n      return true;\n    }\n\n    return true;\n  }\n'''
    if old not in core:
        raise SystemExit('runHomeworkSimpleTest render block not found')
    core = core.replace(old, new, 1)

loader = loader.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.83";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.86";')
loader = loader.replace('/he/workspace/lesson-completion-core.js?v=0783', '/he/workspace/lesson-completion-core.js?v=0786')

for oldv in ('0.7.83','0.7.84','0.7.85'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.86')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.86";')
for oldq in ('0783','0784','0785'):
    index = index.replace(f'/he/workspace/lesson-completion.js?v={oldq}', '/he/workspace/lesson-completion.js?v=0786')

CORE.write_text(core, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Simple test auto-advance patched; build 0.7.86')
