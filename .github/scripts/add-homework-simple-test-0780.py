from pathlib import Path

BACKEND=Path('backend-ai-tutor-he/main.py')
CORE=Path('he/workspace/lesson-completion-core.js')
INDEX=Path('he/workspace/index.html')

backend=BACKEND.read_text(encoding='utf-8')
core=CORE.read_text(encoding='utf-8')
index=INDEX.read_text(encoding='utf-8')

if 'class HomeworkSimpleTestRequest(BaseModel):' not in backend:
    anchor='class HomeworkAnalyzeRequest(BaseModel):\n'
    block='''class HomeworkSimpleTestRequest(BaseModel):\n    kid_id: str\n    source_text: str = ""\n    current_question: str = ""\n    message: str = ""\n    history: list[dict] | None = None\n\n\n'''
    backend=backend.replace(anchor, block+anchor,1)

if '@app.post("/api/tutor/homework-simple-test")' not in backend:
    anchor='@app.post("/api/tutor/homework-turn")\n'
    endpoint='''@app.post("/api/tutor/homework-simple-test")\ndef homework_simple_test(\n        req: HomeworkSimpleTestRequest,\n        authorization: str = Header(None)\n):\n    user = authenticate_user(authorization)\n    child = get_child_by_id(user.id, req.kid_id)\n    grade = child.get("grade") if isinstance(child, dict) else None\n\n    system_prompt = (\n        "את מורה פרטית לילדים. עזרי לילד להבין ולפתור את שיעורי הבית בעצמו. "\n        "למדי אותו שלב אחרי שלב, בשפה פשוטה שמתאימה לכיתה שלו. "\n        "בכל פעם הסבירי צעד אחד בלבד, שאלי שאלה קצרה אחת, ואז חכי לתשובה. "\n        "אל תתני את התשובה המלאה לפני שהילד ניסה."\n    )\n\n    context = (\n        f"כיתה: {grade or 'לא ידוע'}\\n"\n        f"השאלה: {req.current_question}\\n"\n        f"חומר המקור:\\n{req.source_text}"\n    )\n\n    messages = [{"role":"system","content":system_prompt}, {"role":"user","content":context}]\n    for item in (req.history or [])[-8:]:\n        role = str(item.get("role") or "")\n        content = str(item.get("content") or "").strip()\n        if role in ("user","assistant") and content:\n            messages.append({"role":role,"content":content})\n    if req.message.strip():\n        messages.append({"role":"user","content":req.message.strip()})\n    else:\n        messages.append({"role":"user","content":"תתחילי ללמד אותי את השאלה הזאת שלב אחרי שלב."})\n\n    response = client.chat.completions.create(\n        model="gpt-5.6-sol",\n        messages=messages,\n        temperature=0.3\n    )\n    text = str(response.choices[0].message.content or "").strip()\n    return {"reply": text, "model": "gpt-5.6-sol", "test_mode": True}\n\n\n'''
    backend=backend.replace(anchor, endpoint+anchor,1)

if 'id: "simple_test"' not in core:
    anchor='''  const HELP_CHOICES = [\n'''
    addition='''  const HELP_CHOICES = [\n    {\n      id: "simple_test",\n      icon: "fa-flask",\n      label: "טסט — מורה פשוטה",\n      childText: "תלמדי אותי פשוט, שלב אחרי שלב"\n    },\n'''
    core=core.replace(anchor,addition,1)

if 'async function runHomeworkSimpleTest' not in core:
    anchor='''  async function runHomeworkChoiceWithTutor(choice){\n'''
    helper='''  async function runHomeworkSimpleTest(messageText=""){\n    const analysis = activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS || {};\n    const current = getCurrentHomeworkQuestion ? getCurrentHomeworkQuestion() : null;\n    const kidId = (typeof CURRENT_KID !== "undefined" && CURRENT_KID?.id) ? CURRENT_KID.id : window.CURRENT_KID?.id;\n    const token = await getHomeworkAccessToken();\n    if(!kidId || !token) throw new Error("Simple test auth missing");\n    window.HOMEWORK_SIMPLE_TEST_HISTORY = window.HOMEWORK_SIMPLE_TEST_HISTORY || [];\n    const response = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-simple-test`, {\n      method:"POST",\n      headers:{"Content-Type":"application/json","Authorization":`Bearer ${token}`},\n      body:JSON.stringify({\n        kid_id:kidId,\n        source_text:analysis?.extracted_text || "",\n        current_question:current?.text || "",\n        message:String(messageText||""),\n        history:window.HOMEWORK_SIMPLE_TEST_HISTORY\n      })\n    });\n    if(!response.ok) throw new Error(await response.text());\n    const data=await response.json();\n    const reply=String(data?.reply||"").trim();\n    if(messageText) window.HOMEWORK_SIMPLE_TEST_HISTORY.push({role:"user",content:String(messageText)});\n    window.HOMEWORK_SIMPLE_TEST_HISTORY.push({role:"assistant",content:reply});\n    if(window.HOMEWORK_SIMPLE_TEST_HISTORY.length>10) window.HOMEWORK_SIMPLE_TEST_HISTORY=window.HOMEWORK_SIMPLE_TEST_HISTORY.slice(-10);\n    await renderHomeworkStructuredTeacherMessage(reply);\n    return true;\n  }\n\n'''
    core=core.replace(anchor,helper+anchor,1)

old='''  async function runHomeworkChoiceWithTutor(choice){\n    window.HOMEWORK_HELP_MODE = String(choice?.id || "").trim() || null;\n'''
new='''  async function runHomeworkChoiceWithTutor(choice){\n    window.HOMEWORK_HELP_MODE = String(choice?.id || "").trim() || null;\n    if(choice?.id === "simple_test"){\n      window.HOMEWORK_SIMPLE_TEST_MODE = true;\n      window.HOMEWORK_SIMPLE_TEST_HISTORY = [];\n      removeHomeworkHelpOptions();\n      setHomeworkSidebarStep(4);\n      await runHomeworkSimpleTest("");\n      return;\n    }\n    window.HOMEWORK_SIMPLE_TEST_MODE = false;\n'''
if old in core and 'choice?.id === "simple_test"' not in core:
    core=core.replace(old,new,1)

old2='''  async function runStructuredHomeworkTurn(answerText){\n    const current = getCurrentHomeworkQuestion();\n'''
new2='''  async function runStructuredHomeworkTurn(answerText){\n    if(window.HOMEWORK_SIMPLE_TEST_MODE === true){\n      await runHomeworkSimpleTest(answerText);\n      return;\n    }\n    const current = getCurrentHomeworkQuestion();\n'''
if old2 in core and 'HOMEWORK_SIMPLE_TEST_MODE === true' not in core:
    core=core.replace(old2,new2,1)

# icon mapping
core=core.replace('''        check_answer: "✓"\n''','''        check_answer: "✓",\n        simple_test: "🧪"\n''')

for oldv in ('0.7.77','0.7.78','0.7.79'):
    index=index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.80')
    index=index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.80";')
index=index.replace('/he/workspace/lesson-completion.js?v=0776','/he/workspace/lesson-completion.js?v=0780')

BACKEND.write_text(backend,encoding='utf-8')
CORE.write_text(core,encoding='utf-8')
INDEX.write_text(index,encoding='utf-8')
print('Added temporary simple homework tutor test mode 0.7.80')
