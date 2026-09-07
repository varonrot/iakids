from pathlib import Path
import re

ROOT = Path('.')
backend = ROOT / 'backend-ai-tutor-he' / 'main.py'
core = ROOT / 'he' / 'workspace' / 'lesson-completion-core.js'
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

b = backend.read_text(encoding='utf-8')

# 1) Add homework_session_id to HomeworkTurnRequest if missing.
if 'homework_session_id: str | None = None' not in b:
    b = b.replace(
        '    session_id: str | None = None\n\n\nclass HomeworkTurnEvaluation',
        '    session_id: str | None = None\n    homework_session_id: str | None = None\n\n\nclass HomeworkTurnEvaluation',
        1
    )

# 2) Add start request + endpoint before HomeworkTurnEvaluation.
if 'class HomeworkSessionStartRequest' not in b:
    anchor = 'class HomeworkTurnEvaluation(BaseModel):\n'
    insert = '''class HomeworkSessionStartRequest(BaseModel):\n    kid_id: str\n    tutor_session_id: str | None = None\n    subject: str | None = None\n    topic: str | None = None\n    source_file_name: str | None = None\n    source_file_url: str | None = None\n    source_type: str | None = None\n    total_questions: int = 0\n\n\n@app.post("/api/tutor/homework-session/start")\ndef start_homework_session(\n        req: HomeworkSessionStartRequest,\n        authorization: str = Header(None)\n):\n    user = authenticate_user(authorization)\n    child = get_child_by_id(user.id, req.kid_id)\n\n    now_iso = datetime.now(timezone.utc).isoformat()\n    payload = {\n        "user_id": user.id,\n        "kid_id": child["id"],\n        "tutor_session_id": req.tutor_session_id,\n        "subject": req.subject,\n        "topic": req.topic,\n        "source_file_name": req.source_file_name,\n        "source_file_url": req.source_file_url,\n        "source_type": req.source_type,\n        "total_questions": max(0, int(req.total_questions or 0)),\n        "completed_questions": 0,\n        "status": "in_progress",\n        "started_at": now_iso,\n        "last_activity_at": now_iso,\n        "updated_at": now_iso\n    }\n\n    result = supabase_with_retry(\n        lambda: sb.table("homework_sessions").insert(payload).execute(),\n        label="HOMEWORK SESSION START"\n    )\n\n    if not result.data:\n        raise HTTPException(status_code=500, detail="Failed to create homework session")\n\n    return result.data[0]\n\n\n'''
    if anchor not in b:
        raise RuntimeError('HomeworkTurnEvaluation anchor missing')
    b = b.replace(anchor, insert + anchor, 1)

# 3) Update homework session after each turn, before transcript save.
if 'HOMEWORK SESSION PROGRESS' not in b:
    anchor = '    session = get_or_create_tutor_session(user.id, req.kid_id)\n'
    block = '''    # =====================================================\n    # HOMEWORK SESSION PROGRESS\n    # =====================================================\n    if req.homework_session_id:\n        try:\n            existing_hw = (\n                sb.table("homework_sessions")\n                .select("id,user_id,kid_id,total_questions,completed_questions,status")\n                .eq("id", req.homework_session_id)\n                .eq("user_id", user.id)\n                .eq("kid_id", req.kid_id)\n                .limit(1)\n                .execute()\n            )\n\n            if existing_hw.data:\n                hw = existing_hw.data[0]\n                now_iso = datetime.now(timezone.utc).isoformat()\n                update_payload = {\n                    "last_activity_at": now_iso,\n                    "updated_at": now_iso\n                }\n\n                if result.get("answer_sufficient"):\n                    previous_completed = int(hw.get("completed_questions") or 0)\n                    completed_now = max(previous_completed, int(req.current_question_number or 0))\n                    total_questions = int(hw.get("total_questions") or 0)\n\n                    # If the client knows there is no next question, the worksheet is complete.\n                    is_complete = not bool(req.next_question)\n                    if total_questions > 0:\n                        completed_now = min(total_questions, completed_now)\n                        is_complete = is_complete or completed_now >= total_questions\n\n                    update_payload["completed_questions"] = completed_now\n                    if is_complete:\n                        update_payload["status"] = "completed"\n                        update_payload["completed_at"] = now_iso\n\n                if req.session_id:\n                    update_payload["tutor_session_id"] = req.session_id\n\n                supabase_with_retry(\n                    lambda: (\n                        sb.table("homework_sessions")\n                        .update(update_payload)\n                        .eq("id", req.homework_session_id)\n                        .eq("user_id", user.id)\n                        .eq("kid_id", req.kid_id)\n                        .execute()\n                    ),\n                    label="HOMEWORK SESSION UPDATE"\n                )\n        except Exception as hw_error:\n            print("HOMEWORK SESSION PROGRESS WARNING:", repr(hw_error))\n\n'''
    if anchor not in b:
        raise RuntimeError('session anchor missing')
    b = b.replace(anchor, block + anchor, 1)

backend.write_text(b, encoding='utf-8')

c = core.read_text(encoding='utf-8')

# 4) Add client-side helpers before runStructuredHomeworkTurn.
if 'async function createHomeworkTrackingSession' not in c:
    anchor = '  async function runStructuredHomeworkTurn(answerText){\n'
    helper = '''  async function createHomeworkTrackingSession(analysis){\n    try{\n      const token = await getHomeworkAccessToken();\n      const kidId = getHomeworkKidId();\n      if(!token || !kidId) return null;\n\n      const classification = resolveHomeworkClassification(analysis || {});\n      const questions = Array.isArray(window.CURRENT_HOMEWORK_QUESTIONS)\n        ? window.CURRENT_HOMEWORK_QUESTIONS\n        : [];\n\n      const response = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-session/start`, {\n        method: "POST",\n        headers: {\n          "Content-Type": "application/json",\n          "Authorization": `Bearer ${token}`\n        },\n        body: JSON.stringify({\n          kid_id: kidId,\n          tutor_session_id: (typeof currentSessionId !== "undefined" ? currentSessionId : null),\n          subject: classification?.subject || null,\n          topic: classification?.topic || null,\n          source_file_name: analysis?.file_name || analysis?.source_file_name || null,\n          source_file_url: analysis?.file_url || analysis?.source_file_url || null,\n          source_type: analysis?.source_type || analysis?.file_type || null,\n          total_questions: questions.length\n        })\n      });\n\n      if(!response.ok){\n        console.warn("HOMEWORK SESSION START FAILED", response.status, await response.text());\n        return null;\n      }\n\n      const data = await response.json();\n      window.CURRENT_HOMEWORK_SESSION_ID = data?.id || null;\n      window.CURRENT_HOMEWORK_SESSION = data || null;\n      console.log("HOMEWORK TRACKING SESSION STARTED", data?.id);\n      return data;\n    }\n    catch(error){\n      console.warn("HOMEWORK TRACKING SESSION WARNING", error);\n      return null;\n    }\n  }\n\n'''
    if anchor not in c:
        raise RuntimeError('runStructuredHomeworkTurn anchor missing')
    c = c.replace(anchor, helper + anchor, 1)

# 5) Send homework_session_id with each turn.
if 'homework_session_id: window.CURRENT_HOMEWORK_SESSION_ID || null' not in c:
    c = c.replace(
        '            session_id: (typeof currentSessionId !== "undefined" ? currentSessionId : null),\n            current_question_number:',
        '            session_id: (typeof currentSessionId !== "undefined" ? currentSessionId : null),\n            homework_session_id: window.CURRENT_HOMEWORK_SESSION_ID || null,\n            current_question_number:',
        1
    )

# 6) Create homework session after analysis/questions are initialized.
old = '''  smartHomeworkAnalysisIntro = async function(analysis){\n    initializeHomeworkQuestionState(analysis || {});\n    return originalSmartHomeworkAnalysisIntro0726(analysis);\n  };'''
new = '''  smartHomeworkAnalysisIntro = async function(analysis){\n    initializeHomeworkQuestionState(analysis || {});\n    window.CURRENT_HOMEWORK_SESSION_ID = null;\n    window.CURRENT_HOMEWORK_SESSION = null;\n    await createHomeworkTrackingSession(analysis || {});\n    return originalSmartHomeworkAnalysisIntro0726(analysis);\n  };'''
if old in c:
    c = c.replace(old, new, 1)
elif 'await createHomeworkTrackingSession(analysis || {});' not in c:
    raise RuntimeError('smartHomeworkAnalysisIntro wrapper not found')

core.write_text(c, encoding='utf-8')

# 7) Version bump/cache bust.
l = loader.read_text(encoding='utf-8')
l = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.45";', l, count=1)
l = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0745', l, count=1)
loader.write_text(l, encoding='utf-8')

i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.45', i, count=1)
i = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0745', i, count=1)
index.write_text(i, encoding='utf-8')

print('Connected homework_sessions tracking; bumped to 0.7.45')
