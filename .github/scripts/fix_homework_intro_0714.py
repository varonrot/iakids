from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Keep the intro visible instead of auto-scrolling it above the chat viewport.
old = '''    row.appendChild(panel);\n    messages.appendChild(row);\n    scrollHomeworkChatToBottom();\n    return true;\n'''
new = '''    row.appendChild(panel);\n    messages.appendChild(row);\n\n    /* Keep the detected subject/topic visible at the top of the chat. */\n    requestAnimationFrame(() => {\n      messages.scrollTop = 0;\n    });\n\n    return true;\n'''
if old not in core:
    raise SystemExit('renderHomeworkHelpOptions anchor not found')
core = core.replace(old, new, 1)

# 2) Shorter, grade-aware opening message.
start = core.index('  function getHomeworkIntroByGrade(analysis){')
end = core.index('\n  function ensureHomeworkHelpStyles(){', start)
replacement = '''  function getHomeworkIntroByGrade(analysis){\n    const grade = getHomeworkGrade();\n    const detection = getHomeworkDetectionSentence(analysis);\n\n    if(grade <= 2){\n      return `${detection}\\nאני יכולה להסביר, לתת רמז או לפתור איתך יחד.`;\n    }\n\n    if(grade <= 4){\n      return `${detection}\\nאני יכולה להסביר, לתת רמז, לפתור יחד או לבדוק תשובה.`;\n    }\n\n    return `${detection}\\nאפשר לקבל הסבר, רמז, לפתור יחד או לבדוק תשובה.`;\n  }\n'''
core = core[:start] + replacement + core[end:]

# 3) Add sidebar-step sync helper before smart intro.
anchor = '  async function smartHomeworkAnalysisIntro(analysis){\n'
helper = '''  function setHomeworkSidebarStep(stepNumber){\n    const steps = document.querySelectorAll('.homework-sidebar-step');\n    if(!steps.length) return;\n\n    steps.forEach(step => step.classList.remove('active'));\n    const index = Math.max(0, Math.min(steps.length - 1, Number(stepNumber || 1) - 1));\n    steps[index]?.classList.add('active');\n  }\n\n'''
if helper not in core:
    if anchor not in core:
        raise SystemExit('smartHomeworkAnalysisIntro anchor not found')
    core = core.replace(anchor, helper + anchor, 1)

# 4) On analysis completion: show concise intro, advance sidebar to identification, keep chat at top.
old = '''  async function smartHomeworkAnalysisIntro(analysis){\n    activeHomeworkAnalysis = analysis || null;\n    window.CURRENT_HOMEWORK_ANALYSIS = analysis || null;\n\n    addMessage("user", "📷 העליתי צילום של שיעורי הבית");\n    addMessage("assistant", getHomeworkIntroByGrade(analysis));\n    renderHomeworkHelpOptions();\n'''
new = '''  async function smartHomeworkAnalysisIntro(analysis){\n    activeHomeworkAnalysis = analysis || null;\n    window.CURRENT_HOMEWORK_ANALYSIS = analysis || null;\n\n    setHomeworkSidebarStep(2);\n    addMessage("assistant", getHomeworkIntroByGrade(analysis));\n    renderHomeworkHelpOptions();\n\n    const messages = getHomeworkMessagesContainer();\n    if(messages){\n      requestAnimationFrame(() => { messages.scrollTop = 0; });\n    }\n'''
if old not in core:
    raise SystemExit('smartHomeworkAnalysisIntro body anchor not found')
core = core.replace(old, new, 1)

# 5) Advance the homework sidebar based on the selected help mode.
old = '''    addMessage("user", choice.childText);\n    removeHomeworkHelpOptions();\n\n    try{\n'''
new = '''    addMessage("user", choice.childText);\n    removeHomeworkHelpOptions();\n\n    if(choice.id === "check_answer"){\n      setHomeworkSidebarStep(5);\n    }\n    else if(choice.id === "understand_question"){\n      setHomeworkSidebarStep(3);\n    }\n    else{\n      setHomeworkSidebarStep(4);\n    }\n\n    try{\n'''
if old not in core:
    raise SystemExit('selectHomeworkHelpOption anchor not found')
core = core.replace(old, new, 1)

# 6) Bump visible frontend build and cache-bust both extension/core loaders.
index = index.replace('IAKIDS • build 0.7.13', 'IAKIDS • build 0.7.14')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.13";', 'window.IAKIDS_BUILD_VERSION = "0.7.14";')
index = index.replace('/he/workspace/lesson-completion.js?v=0713', '/he/workspace/lesson-completion.js?v=0714')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.13";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.14";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0713', '/he/workspace/lesson-completion-core.js?v=0714')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')

print('Homework intro 0.7.14 patch applied')
# trigger workflow
