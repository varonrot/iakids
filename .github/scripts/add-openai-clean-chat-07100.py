from pathlib import Path
import re

root=Path('.')
backend_path=root/'backend-ai-tutor-he/main.py'
index_path=root/'he/workspace/index.html'
backend=backend_path.read_text(encoding='utf-8')
index=index_path.read_text(encoding='utf-8')

# Backend model + endpoint
if 'class OpenAICleanChatRequest(BaseModel):' not in backend:
    marker='class HomeworkCoachRequest(BaseModel):\n'
    if marker not in backend:
        raise SystemExit('HomeworkCoachRequest marker not found')
    model='''class OpenAICleanChatRequest(BaseModel):\n    message: str = ""\n    image_url: str = ""\n    history: list = []\n\n\n'''
    backend=backend.replace(marker,model+marker,1)

if '@app.post("/api/tutor/openai-clean-chat")' not in backend:
    marker='@app.post("/api/tutor/homework-coach-v2")\n'
    if marker not in backend:
        raise SystemExit('homework-coach-v2 marker not found')
    route='''@app.post("/api/tutor/openai-clean-chat")\nasync def openai_clean_chat(\n        req: OpenAICleanChatRequest,\n        authorization: str = Header(None)\n):\n    authenticate_user(authorization)\n\n    system_prompt = (\n        "את מורה פרטית מצוינת לילדים. "\n        "עזרי לילד להבין ולפתור את המשימה בעצמו. "\n        "הסבירי בפשטות, שלב אחרי שלב, ואל תתני את התשובה הסופית מיד. "\n        "אם הילד העלה תמונה, קראי אותה בעצמך והשתמשי בה כמקור הראשי. "\n        "התנהגי כמו מורה פרטית טבעית וחכמה, לא כמו שאלון."\n    )\n\n    messages=[{"role":"system","content":system_prompt}]\n    for item in (req.history or [])[-16:]:\n        role=str(item.get("role") or "")\n        content=str(item.get("content") or "").strip()\n        if role in ("user","assistant") and content:\n            messages.append({"role":role,"content":content})\n\n    user_parts=[]\n    if str(req.message or "").strip():\n        user_parts.append({"type":"text","text":str(req.message).strip()})\n    elif req.image_url:\n        user_parts.append({"type":"text","text":"תסתכלי על דף העבודה ותעזרי לי להבין איך לפתור אותו שלב אחרי שלב."})\n    if str(req.image_url or "").strip():\n        user_parts.append({"type":"image_url","image_url":{"url":str(req.image_url).strip(),"detail":"high"}})\n    if not user_parts:\n        user_parts.append({"type":"text","text":"היי"})\n    messages.append({"role":"user","content":user_parts})\n\n    response=await aclient.chat.completions.create(\n        model="gpt-5.6-sol",\n        messages=messages\n    )\n    text=str(response.choices[0].message.content or "").strip()\n    return {"reply":text,"model":"gpt-5.6-sol","openai_only":True}\n\n\n'''
    backend=backend.replace(marker,route+marker,1)

# Sidebar button
if 'id="openaiCleanChatBtn"' not in index:
    marker='''    <!-- עזרה בשיעורי בית V2 — clean isolated tutor -->'''
    pos=index.find(marker)
    if pos<0:
        raise SystemExit('V2 sidebar marker not found')
    # insert before V2, so visible near homework
    button='''    <!-- OpenAI clean test -->\n    <button class="side-item" id="openaiCleanChatBtn" type="button" onclick="openOpenAICleanChat(this)">\n      <i class="fa-solid fa-bolt"></i>\n      <div class="side-text"><span class="side-title">OpenAI נקי</span></div>\n    </button>\n\n'''
    index=index[:pos]+button+index[pos:]

# Script include
if '/he/workspace/openai-clean-chat.js?v=07100' not in index:
    marker='</body>'
    if marker not in index:
        raise SystemExit('body end not found')
    index=index.replace(marker,'<script src="/he/workspace/openai-clean-chat.js?v=07100"></script>\n'+marker,1)

# Version
index=re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+','IAKIDS • build 0.7.100',index)
index=re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";','window.IAKIDS_BUILD_VERSION = "0.7.100";',index,count=1)

backend_path.write_text(backend,encoding='utf-8')
index_path.write_text(index,encoding='utf-8')
print('Added isolated OpenAI-only clean chat; build 0.7.100')
