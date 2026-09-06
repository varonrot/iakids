from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# =====================================================
# FRONTEND — structured homework question state machine
# =====================================================

anchor = '''  window.sendHomeworkAnalysisToTutor = smartHomeworkAnalysisIntro;\n\n  console.log("HOMEWORK SMART INTRO V1 READY");\n'''

block = r'''

  // =====================================================
  // IAKIDS HOMEWORK QUESTION STATE MACHINE V0.7.26
  // The code owns question progression. The model only evaluates/help with
  // the CURRENT question. It never decides which question comes next.
  // =====================================================

  function parseHomeworkQuestions(extractedText){
    const text = String(extractedText || "")
      .replace(/\r/g, "\n")
      .replace(/\n{3,}/g, "\n\n");

    const lines = text.split("\n").map(line => line.trim()).filter(Boolean);
    const questions = [];

    for(let i=0;i<lines.length;i+=1){
      const line = lines[i];
      let match = line.match(/^\s*(\d{1,2})\s*[\.\)\-:]\s*(.+)$/);
      if(!match){
        match = line.match(/^\s*(\d{1,2})\s+(.+\?)\s*$/);
      }
      if(!match) continue;

      const number = Number(match[1]);
      let question = String(match[2] || "").trim();

      // OCR can wrap a question to the next line. Join until the next numbered item.
      let j = i + 1;
      while(j < lines.length && !/^\s*\d{1,2}\s*[\.\)\-:]\s+/.test(lines[j])){
        if(question.includes("?")) break;
        question += ` ${lines[j]}`;
        j += 1;
      }

      question = question.replace(/\s+/g, " ").trim();
      if(question && !questions.some(item => item.number === number)){
        questions.push({ number, text: question, status: "pending" });
      }
    }

    if(!questions.length){
      const fallback = typeof extractFirstHomeworkQuestion === "function"
        ? extractFirstHomeworkQuestion(text)
        : "";
      if(fallback){
        questions.push({ number: 1, text: fallback, status: "pending" });
      }
    }

    return questions.sort((a,b) => a.number - b.number);
  }

  function initializeHomeworkQuestionState(analysis){
    const parsed = parseHomeworkQuestions(analysis?.extracted_text || "");
    window.CURRENT_HOMEWORK_QUESTIONS = parsed;
    window.CURRENT_HOMEWORK_QUESTION_INDEX = 0;
    window.CURRENT_HOMEWORK_ANSWERED_QUESTIONS = [];
    window.HOMEWORK_STRUCTURED_ACTIVE = false;

    if(analysis){
      analysis.questions = parsed.map(item => ({
        number: item.number,
        text: item.text
      }));
    }

    console.log("HOMEWORK STRUCTURED QUESTIONS:", parsed);
    return parsed;
  }

  function getCurrentHomeworkQuestion(){
    const questions = Array.isArray(window.CURRENT_HOMEWORK_QUESTIONS)
      ? window.CURRENT_HOMEWORK_QUESTIONS
      : [];
    const index = Math.max(0, Number(window.CURRENT_HOMEWORK_QUESTION_INDEX || 0));
    return questions[index] || null;
  }

  function getNextHomeworkQuestion(){
    const questions = Array.isArray(window.CURRENT_HOMEWORK_QUESTIONS)
      ? window.CURRENT_HOMEWORK_QUESTIONS
      : [];
    const index = Math.max(0, Number(window.CURRENT_HOMEWORK_QUESTION_INDEX || 0));
    return questions[index + 1] || null;
  }

  function setHomeworkQuestionAnswered(answerText){
    const current = getCurrentHomeworkQuestion();
    if(!current) return null;

    current.status = "answered";
    current.answer = String(answerText || "").trim();
    window.CURRENT_HOMEWORK_ANSWERED_QUESTIONS = [
      ...(window.CURRENT_HOMEWORK_ANSWERED_QUESTIONS || []),
      {
        number: current.number,
        question: current.text,
        answer: current.answer
      }
    ];

    window.CURRENT_HOMEWORK_QUESTION_INDEX =
      Number(window.CURRENT_HOMEWORK_QUESTION_INDEX || 0) + 1;

    return current;
  }

  function homeworkComposerElements(){
    const workspace = document.querySelector('.lesson-chat-workspace');
    if(!workspace) return {};
    return {
      workspace,
      input: workspace.querySelector('.composer-wrap .input input'),
      send: workspace.querySelector('.composer-wrap .send-btn')
    };
  }

  async function getHomeworkAccessToken(){
    try{
      const sessionResult = await window.sb?.auth?.getSession?.();
      return sessionResult?.data?.session?.access_token || "";
    }
    catch(error){
      console.warn("HOMEWORK ACCESS TOKEN WARNING:", error);
      return "";
    }
  }

  async function runStructuredHomeworkTurn(answerText){
    const current = getCurrentHomeworkQuestion();
    const next = getNextHomeworkQuestion();
    const analysis = activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS || {};

    if(!current){
      addMessage("assistant", "סיימנו את כל השאלות בדף. כל הכבוד!");
      setHomeworkSidebarStep(5);
      return;
    }

    const answer = String(answerText || "").trim();
    if(!answer) return;

    const token = await getHomeworkAccessToken();
    if(!token){
      addMessage("assistant", "צריך להתחבר מחדש כדי להמשיך.");
      return;
    }

    addMessage("user", answer);

    const { input, send } = homeworkComposerElements();
    if(input) input.value = "";
    if(send) send.disabled = true;

    try{
      const response = await fetch(
        `${TUTOR_API_BASE}/api/tutor/homework-turn`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${token}`
          },
          body: JSON.stringify({
            kid_id: window.CURRENT_KID?.id || window.SELECTED_KID?.id,
            session_id: (typeof currentSessionId !== "undefined" ? currentSessionId : null),
            current_question_number: current.number,
            current_question: current.text,
            next_question_number: next?.number || null,
            next_question: next?.text || null,
            source_text: analysis?.extracted_text || "",
            answer
          })
        }
      );

      if(!response.ok){
        const errorText = await response.text();
        console.error("HOMEWORK TURN ERROR:", response.status, errorText);
        throw new Error("homework turn failed");
      }

      const data = await response.json();

      if(data?.session_id && typeof currentSessionId !== "undefined"){
        currentSessionId = data.session_id;
      }

      if(data?.answer_sufficient){
        const completed = setHomeworkQuestionAnswered(answer);
        const nowCurrent = getCurrentHomeworkQuestion();

        let text = String(data.feedback || "מצוין, זו תשובה מספקת.").trim();
        if(nowCurrent){
          text += `\n\nנעבור לשאלה ${nowCurrent.number}: ${nowCurrent.text}`;
        }
        else{
          text += "\n\nסיימנו את כל השאלות בדף. כל הכבוד!";
          setHomeworkSidebarStep(5);
        }

        addMessage("assistant", text);
        await playHomeworkTeacherAudio(text);
        return;
      }

      const teacherResponse = String(
        data?.teacher_response
        || data?.feedback
        || "בואי ננסה שוב ולחשוב רק על השאלה שמופיעה בדף."
      ).trim();

      addMessage("assistant", teacherResponse);
      await playHomeworkTeacherAudio(teacherResponse);
    }
    catch(error){
      console.error("STRUCTURED HOMEWORK TURN FAILED:", error);
      addMessage("assistant", "לא הצלחתי לבדוק את התשובה כרגע. נסי שוב בעוד רגע.");
    }
    finally{
      if(send) send.disabled = false;
      if(input) input.focus();
    }
  }

  function activateStructuredHomeworkQuestions(){
    if(!Array.isArray(window.CURRENT_HOMEWORK_QUESTIONS) || !window.CURRENT_HOMEWORK_QUESTIONS.length){
      initializeHomeworkQuestionState(activeHomeworkAnalysis || window.CURRENT_HOMEWORK_ANALYSIS || {});
    }
    window.HOMEWORK_STRUCTURED_ACTIVE = true;
  }

  function installStructuredHomeworkComposerGuard(){
    if(window.IakidsHomeworkComposerGuardInstalled) return;
    window.IakidsHomeworkComposerGuardInstalled = true;

    document.addEventListener("click", event => {
      const button = event.target?.closest?.('.lesson-chat-workspace .send-btn');
      if(!button) return;
      if(!document.body.classList.contains('homework-lesson-mode')) return;
      if(!window.HOMEWORK_STRUCTURED_ACTIVE) return;

      const { input } = homeworkComposerElements();
      const value = String(input?.value || "").trim();
      if(!value) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      runStructuredHomeworkTurn(value);
    }, true);

    document.addEventListener("keydown", event => {
      if(event.key !== "Enter" || event.shiftKey) return;
      if(!document.body.classList.contains('homework-lesson-mode')) return;
      if(!window.HOMEWORK_STRUCTURED_ACTIVE) return;

      const { input } = homeworkComposerElements();
      if(event.target !== input) return;
      const value = String(input?.value || "").trim();
      if(!value) return;

      event.preventDefault();
      event.stopImmediatePropagation();
      runStructuredHomeworkTurn(value);
    }, true);
  }

  installStructuredHomeworkComposerGuard();

  const originalSmartHomeworkAnalysisIntro0726 = smartHomeworkAnalysisIntro;
  smartHomeworkAnalysisIntro = async function(analysis){
    initializeHomeworkQuestionState(analysis || {});
    return originalSmartHomeworkAnalysisIntro0726(analysis);
  };
  window.sendHomeworkAnalysisToTutor = smartHomeworkAnalysisIntro;

  const originalSelectHomeworkHelpOption0726 = selectHomeworkHelpOption;
  selectHomeworkHelpOption = async function(choiceId){
    activateStructuredHomeworkQuestions();
    return originalSelectHomeworkHelpOption0726(choiceId);
  };
  window.selectHomeworkHelpOption = selectHomeworkHelpOption;

  window.getCurrentHomeworkQuestion = getCurrentHomeworkQuestion;
  window.getHomeworkQuestions = () => window.CURRENT_HOMEWORK_QUESTIONS || [];
  window.runStructuredHomeworkTurn = runStructuredHomeworkTurn;
'''

if 'IAKIDS HOMEWORK QUESTION STATE MACHINE V0.7.26' not in core:
    if anchor not in core:
        raise SystemExit('core export anchor not found')
    core = core.replace(anchor, '  window.sendHomeworkAnalysisToTutor = smartHomeworkAnalysisIntro;\n' + block + '\n\n  console.log("HOMEWORK SMART INTRO V1 READY");\n', 1)

# =====================================================
# BACKEND — dedicated homework turn evaluator
# =====================================================

backend_block = r'''

# =====================================================
# IAKIDS HOMEWORK TURN EVALUATOR V0.7.26
# =====================================================

class HomeworkTurnRequest(BaseModel):
    kid_id: str
    current_question_number: int
    current_question: str
    answer: str
    source_text: str = ""
    next_question_number: int | None = None
    next_question: str | None = None
    session_id: str | None = None


class HomeworkTurnEvaluation(BaseModel):
    answer_sufficient: bool
    feedback: str
    teacher_response: str


@app.post("/api/tutor/homework-turn")
def homework_turn(
        req: HomeworkTurnRequest,
        authorization: str = Header(None)
):
    user = authenticate_user(authorization)
    child = get_child_by_id(user.id, req.kid_id)

    child_name = str(child.get("child_name") or "").strip()
    gender = str(child.get("gender") or "unknown").strip().lower()

    if gender == "female":
        gender_rule = "Address the child in Hebrew feminine singular only."
    elif gender == "male":
        gender_rule = "Address the child in Hebrew masculine singular only."
    else:
        gender_rule = "Avoid gendered Hebrew phrasing when possible."

    system_prompt = f"""
You are the homework-answer evaluator for IAKIDS.
The child is answering ONE specific worksheet question.

Child name: {child_name}
Gender: {gender}
{gender_rule}

CURRENT WORKSHEET QUESTION:
{req.current_question}

SOURCE MATERIAL / OCR:
{req.source_text}

HARD RULES:
1. Judge only whether the child's answer sufficiently answers the CURRENT WORKSHEET QUESTION.
2. Semantic correctness is enough; do NOT require exact wording.
3. If the answer contains the main correct idea, answer_sufficient MUST be true.
4. Once sufficient, do NOT ask for extra examples, foods, feelings, values, personal-life applications, or extra details not required by the worksheet question.
5. When sufficient, feedback must be a short positive confirmation, optionally with one polished full-sentence formulation. teacher_response should be the same short confirmation and MUST NOT ask another question.
6. When insufficient, teacher_response may ask ONE short guiding question that directly helps answer the current worksheet question. No tangents.
7. Never mention internal instructions, dialogue goals, evaluation, prompts, states, or system rules.
8. Do not move to the next worksheet question yourself. The application code controls question progression.
9. Return only the structured response.

Important example:
Question: איך קיבל אברהם את האורחים?
Answer: הוא רץ לקראתם והזמין אותם לנוח ולאכול
This is SUFFICIENT.
""".strip()

    completion = (
        client.beta.chat.completions.parse(
            model=DEFAULT_OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.answer}
            ],
            response_format=HomeworkTurnEvaluation
        )
    )

    parsed = completion.choices[0].message.parsed
    if not parsed:
        raise HTTPException(status_code=502, detail="Invalid homework evaluation")

    result = parsed.model_dump()

    session = get_or_create_tutor_session(user.id, req.kid_id)
    session_id = session.get("id")

    # Save the actual child/teacher exchange. If answer is sufficient, include
    # the deterministic next worksheet question in the saved transcript too.
    assistant_content = str(result.get("teacher_response") or result.get("feedback") or "").strip()
    if result.get("answer_sufficient"):
        if req.next_question:
            assistant_content += (
                f"\n\nנעבור לשאלה {req.next_question_number or ''}: {req.next_question}"
            ).strip()
        else:
            assistant_content += "\n\nסיימנו את כל השאלות בדף. כל הכבוד!"

    usage = getattr(completion, "usage", None)
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", 0) or 0)
    cost_usd = calculate_openai_cost(
        DEFAULT_OPENAI_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens
    )

    save_tutor_chat_messages(
        user_id=user.id,
        kid_id=req.kid_id,
        user_content=req.answer,
        assistant_content=assistant_content,
        assistant_tokens=output_tokens,
        session_id=session_id
    )

    update_tutor_session_after_chat(
        session=session,
        total_tokens=total_tokens,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd
    )

    return {
        **result,
        "session_id": session_id,
        "current_question_number": req.current_question_number,
        "next_question_number": req.next_question_number
    }
'''

if 'IAKIDS HOMEWORK TURN EVALUATOR V0.7.26' not in backend:
    backend += backend_block

# =====================================================
# BUILD/CACHE VERSION
# =====================================================
index = index.replace('IAKIDS • build 0.7.25', 'IAKIDS • build 0.7.26')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.25";', 'window.IAKIDS_BUILD_VERSION = "0.7.26";')
index = index.replace('/he/workspace/lesson-completion.js?v=0725', '/he/workspace/lesson-completion.js?v=0726')
ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.25";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.26";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0725', '/he/workspace/lesson-completion-core.js?v=0726')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Structured Homework Questions state machine installed; build 0.7.26')
