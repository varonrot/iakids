from pathlib import Path
import re

root = Path('.')
backend_path = root / 'backend-ai-tutor-he/main.py'
core_path = root / 'he/workspace/lesson-completion-core.js'
loader_path = root / 'he/workspace/lesson-completion.js'
index_path = root / 'he/workspace/index.html'

backend = backend_path.read_text(encoding='utf-8')
core = core_path.read_text(encoding='utf-8')
loader = loader_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')

# ------------------------------------------------------------------
# 1) Backend: a clean V2 route with one short system prompt only.
#    No legacy teaching strategies, guards, modes or COMPLETE markers.
# ------------------------------------------------------------------
if '@app.post("/api/tutor/homework-coach-v2")' not in backend:
    marker = '@app.post("/api/tutor/homework-coach")\n'
    if marker not in backend:
        raise SystemExit('homework-coach route marker not found')

    v2_route = '''@app.post("/api/tutor/homework-coach-v2")
async def homework_coach_v2(
        req: HomeworkCoachRequest,
        authorization: str = Header(None)
):
    user = authenticate_user(authorization)
    child = get_child_by_id(user.id, req.kid_id)
    grade = child.get("grade") if isinstance(child, dict) else None

    system_prompt = (
        "את מורה פרטית מצוינת לילדים. "
        "המטרה שלך היא לעזור לילד להבין ולפתור את שיעורי הבית בעצמו. "
        "קודם הסתכלי על המשימה והביני מה השאלה מבקשת. "
        "הסבירי לילד בקצרה ובמילים פשוטות מה צריך לעשות ואיך ניגשים לשאלה. "
        "אחר כך למדי אותו שלב אחרי שלב. "
        "בכל הודעה הסבירי רק צעד אחד ברור, הסבירי למה עושים את הצעד הזה, שאלי שאלה קצרה אחת וחכי לתשובת הילד. "
        "אל תתני את התשובה הסופית לפני שהילד ניסה להגיע אליה בעצמו. "
        "אם הילד מתקשה, הסבירי שוב בדרך פשוטה יותר או תני רמז קטן. "
        "אם הילד כבר אמר משהו נכון, זכרי אותו ואל תשאלי עליו שוב. "
        "כשהילד כבר אסף מספיק מידע או ביצע את כל השלבים, בקשי ממנו לנסח או לפתור את התשובה בעצמו. "
        "רק אחרי שהוא ענה, בדקי את התשובה ועזרי לתקן אם צריך. "
        "התאימי את ההסבר לגיל הילד ולסוג המשימה. "
        "התנהגי כמו מורה פרטית אמיתית, לא כמו שאלון."
    )

    context = (
        f"כיתה: {grade or 'לא ידוע'}\\n"
        f"השאלה שעליה עובדים עכשיו: {req.current_question}\\n"
        f"דף העבודה / חומר המקור:\\n{req.source_text}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]
    for item in (req.history or [])[-12:]:
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    if req.message.strip():
        messages.append({"role": "user", "content": req.message.strip()})
    else:
        messages.append({"role": "user", "content": "תתחילי ללמד אותי ולעזור לי לפתור את השאלה הזאת."})

    response = await aclient.chat.completions.create(
        model="gpt-5.6-sol",
        messages=messages,
    )
    text = str(response.choices[0].message.content or "").strip()
    return {"reply": text, "model": "gpt-5.6-sol", "v2": True}


'''
    backend = backend.replace(marker, v2_route + marker, 1)

# ------------------------------------------------------------------
# 2) Frontend: separate V2 runner. It only talks to the V2 endpoint.
# ------------------------------------------------------------------
if 'async function runHomeworkV2Coach(messageText="")' not in core:
    marker = '  async function runHomeworkProductionCoach(messageText=""){\n'
    if marker not in core:
        raise SystemExit('runHomeworkProductionCoach marker not found')

    v2_runner = '''  async function runHomeworkV2Coach(messageText=""){
    const analysis = activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS || {};
    const current = getCurrentHomeworkQuestion ? getCurrentHomeworkQuestion() : null;
    const kidId = (typeof CURRENT_KID !== "undefined" && CURRENT_KID?.id) ? CURRENT_KID.id : window.CURRENT_KID?.id;
    const token = await getHomeworkAccessToken();
    if(!kidId || !token) throw new Error("Homework V2 auth missing");

    window.HOMEWORK_V2_HISTORY = Array.isArray(window.HOMEWORK_V2_HISTORY)
      ? window.HOMEWORK_V2_HISTORY
      : [];

    const response = await fetch(`${TUTOR_API_BASE}/api/tutor/homework-coach-v2`, {
      method:"POST",
      headers:{"Content-Type":"application/json","Authorization":`Bearer ${token}`},
      body:JSON.stringify({
        kid_id:kidId,
        source_text:String(analysis?.extracted_text || ""),
        current_question:String(current?.text || ""),
        history:window.HOMEWORK_V2_HISTORY,
        message:String(messageText || "")
      })
    });

    if(!response.ok){
      const details = await response.text().catch(()=>"");
      throw new Error(`Homework V2 failed ${response.status}: ${details}`);
    }

    const data = await response.json();
    const reply = String(data?.reply || "").trim();
    const displayReply = reply
      .replace(/\\*\\*/g, "")
      .replace(/^#{1,6}\\s*/gm, "")
      .trim();

    if(messageText){
      window.HOMEWORK_V2_HISTORY.push({role:"user",content:String(messageText)});
    }
    if(displayReply){
      window.HOMEWORK_V2_HISTORY.push({role:"assistant",content:displayReply});
    }
    if(window.HOMEWORK_V2_HISTORY.length > 14){
      window.HOMEWORK_V2_HISTORY = window.HOMEWORK_V2_HISTORY.slice(-14);
    }

    await Promise.all([
      renderHomeworkStructuredTeacherMessage(displayReply),
      playHomeworkTeacherAudio(displayReply)
    ]);
  }

'''
    core = core.replace(marker, v2_runner + marker, 1)

# Route every child answer through V2 when V2 is active.
old_turn = '''  async function runStructuredHomeworkTurn(answerText){
    if(window.HOMEWORK_PRODUCTION_COACH_MODE === true){
      await runHomeworkProductionCoach(answerText);
      return;
    }
'''
new_turn = '''  async function runStructuredHomeworkTurn(answerText){
    if(window.HOMEWORK_V2_MODE === true){
      await runHomeworkV2Coach(answerText);
      return;
    }
    if(window.HOMEWORK_PRODUCTION_COACH_MODE === true){
      await runHomeworkProductionCoach(answerText);
      return;
    }
'''
if old_turn not in core:
    raise SystemExit('runStructuredHomeworkTurn block not found')
core = core.replace(old_turn, new_turn, 1)

# Auto-start V2 after worksheet analysis, without entering the legacy production coach.
old_auto = '''    /* No help-mode chooser anymore: the production Sol coach starts automatically. */
    window.HOMEWORK_HELP_MODE = "solve_together";
    window.HOMEWORK_PRODUCTION_COACH_MODE = true;
    window.HOMEWORK_PRODUCTION_COACH_HISTORY = [];
    setHomeworkSidebarStep(4);
    await runHomeworkProductionCoach("");
'''
new_auto = '''    /* V2 is a clean isolated tutor path. Legacy coach stays untouched for A/B comparison. */
    if(window.HOMEWORK_V2_MODE === true){
      window.HOMEWORK_HELP_MODE = "v2_clean";
      window.HOMEWORK_PRODUCTION_COACH_MODE = false;
      window.HOMEWORK_V2_HISTORY = [];
      setHomeworkSidebarStep(4);
      await runHomeworkV2Coach("");
      return;
    }

    /* Legacy production coach. */
    window.HOMEWORK_HELP_MODE = "solve_together";
    window.HOMEWORK_PRODUCTION_COACH_MODE = true;
    window.HOMEWORK_PRODUCTION_COACH_HISTORY = [];
    setHomeworkSidebarStep(4);
    await runHomeworkProductionCoach("");
'''
if old_auto not in core:
    raise SystemExit('homework auto-start block not found')
core = core.replace(old_auto, new_auto, 1)

# ------------------------------------------------------------------
# 3) Sidebar: keep old button and add a clearly separate V2 button.
# ------------------------------------------------------------------
old_button = '''    <!-- עזרה בשיעורי בית -->
    <button
      class="side-item homework-side-item"
      id="homeworkSidebarBtn"
      onclick="showLearning('homework')"
    >
      <i class="fa-solid fa-camera"></i>

      <div class="side-text">
        <span class="side-title">
          עזרה בשיעורי בית
        </span>
      </div>
    </button>
'''
new_button = '''    <!-- עזרה בשיעורי בית -->
    <button
      class="side-item homework-side-item"
      id="homeworkSidebarBtn"
      onclick="window.HOMEWORK_V2_MODE=false;showLearning('homework')"
    >
      <i class="fa-solid fa-camera"></i>

      <div class="side-text">
        <span class="side-title">
          עזרה בשיעורי בית
        </span>
      </div>
    </button>

    <!-- עזרה בשיעורי בית V2 — clean isolated tutor -->
    <button
      class="side-item homework-side-item homework-v2-side-item"
      id="homeworkV2SidebarBtn"
      onclick="window.HOMEWORK_V2_MODE=true;window.HOMEWORK_V2_HISTORY=[];showLearning('homework')"
      title="מסלול V2 נקי לבדיקה"
    >
      <i class="fa-solid fa-wand-magic-sparkles"></i>

      <div class="side-text">
        <span class="side-title">
          עזרה בשיעורי בית V2
        </span>
      </div>
    </button>
'''
if old_button not in index:
    raise SystemExit('homework sidebar button block not found')
index = index.replace(old_button, new_button, 1)

# Add a subtle visual distinction without changing the sidebar design language.
style_marker = '/* MAIN */\n'
v2_style = '''.homework-v2-side-item{border:1px solid rgba(111,92,255,.45)!important;background:linear-gradient(90deg,rgba(44,31,93,.10),rgba(26,82,150,.08))!important;}
.homework-v2-side-item i{background:linear-gradient(135deg,#6f4dff,#1d9fe8)!important;}

'''
if v2_style not in index:
    if style_marker not in index:
        raise SystemExit('MAIN style marker not found')
    index = index.replace(style_marker, v2_style + style_marker, 1)

# ------------------------------------------------------------------
# 4) Version/cache bump.
# ------------------------------------------------------------------
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.96";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0796', loader, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0796', index)
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.96', index)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.96";', index, count=1)

backend_path.write_text(backend, encoding='utf-8')
core_path.write_text(core, encoding='utf-8')
loader_path.write_text(loader, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')

print('Added clean Homework V2 route + sidebar button; build 0.7.96')
