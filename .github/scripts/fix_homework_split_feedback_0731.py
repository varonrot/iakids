from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')
BACKEND = Path('backend-ai-tutor-he/main.py')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')
backend = BACKEND.read_text(encoding='utf-8')

# 1) Split successful homework feedback and next question into separate bubbles/audio chunks.
old = '''      if(data?.answer_sufficient){
        const completed = setHomeworkQuestionAnswered(answer);
        const nowCurrent = getCurrentHomeworkQuestion();

        let text = String(data.feedback || "מצוין, זו תשובה מספקת.").trim();
        if(nowCurrent){
          text += `\\n\\nנעבור לשאלה ${nowCurrent.number}: ${nowCurrent.text}`;
        }
        else{
          text += "\\n\\nסיימנו את כל השאלות בדף. כל הכבוד!";
          setHomeworkSidebarStep(5);
        }

        await Promise.all([
          renderHomeworkStructuredTeacherMessage(text),
          playHomeworkTeacherAudio(text)
        ]);
        return;
      }
'''

new = '''      if(data?.answer_sufficient){
        setHomeworkQuestionAnswered(answer);
        const nowCurrent = getCurrentHomeworkQuestion();

        const feedbackText = String(
          data?.teacher_response
          || data?.feedback
          || "נכון. התשובה שלך עונה על מה שהשאלה ביקשה."
        ).trim();

        // Bubble 1: קצר, מסביר למה התשובה נכונה.
        await Promise.all([
          renderHomeworkStructuredTeacherMessage(feedbackText),
          playHomeworkTeacherAudio(feedbackText)
        ]);

        // Bubble 2: השאלה הבאה עומדת בפני עצמה, כדי לשמור על קצב שיחה טבעי
        // וגם לקצר את מקטע ה-TTS הראשון.
        await new Promise(resolve => setTimeout(resolve, 220));

        if(nowCurrent){
          const nextQuestionText = `נעבור לשאלה ${nowCurrent.number}: ${nowCurrent.text}`;
          await Promise.all([
            renderHomeworkStructuredTeacherMessage(nextQuestionText),
            playHomeworkTeacherAudio(nextQuestionText)
          ]);
        }
        else{
          const closingText = "סיימנו את כל השאלות בדף. כל הכבוד!";
          setHomeworkSidebarStep(5);
          await Promise.all([
            renderHomeworkStructuredTeacherMessage(closingText),
            playHomeworkTeacherAudio(closingText)
          ]);
        }
        return;
      }
'''

if old not in core:
    raise SystemExit('structured sufficient branch not found')
core = core.replace(old, new, 1)

# 2) Make correct-answer feedback shorter but still educational.
old = '''5. When sufficient, do NOT give generic praise alone such as "עבודה מצוינת". Explain WHY the answer is correct in one clear sentence by connecting the child's words to the requirement of the CURRENT WORKSHEET QUESTION and, when useful, to the source text. Then give one polished full-sentence model answer the child can learn from. Keep the whole teacher_response concise: usually 2-3 short sentences.
6. For a sufficient answer, teacher_response should follow this teaching pattern: (a) specific confirmation, (b) why it answers the question, (c) polished full answer. Example: "נכון. ענית על השאלה כי ציינת את שתי הפעולות המרכזיות: אברהם רץ לקראת האורחים והזמין אותם לנוח ולאכול. תשובה מלאה יכולה להיות: אברהם קיבל את האורחים בכך שרץ לקראתם והזמין אותם לנוח ולאכול." Do NOT ask another question when the answer is sufficient.
'''
new = '''5. When sufficient, do NOT give generic praise alone such as "עבודה מצוינת". Give exactly TWO short Hebrew sentences, usually no more than 28 words total: first explain WHY the child's answer is correct by naming the key idea(s) that answer the question; second give a polished full-sentence answer. Do not repeat the same wording twice.
6. For a sufficient answer use this compact pattern: "נכון, כי ציינת ש[הנקודות המרכזיות]. תשובה מלאה: [ניסוח מלא וקצר]." Do NOT ask another question and do NOT mention the next worksheet question; the application will show it in a separate bubble.
'''
if old not in backend:
    raise SystemExit('pedagogy rules block not found')
backend = backend.replace(old, new, 1)

old = '''A good teacher_response is:
"נכון. ענית על השאלה כי ציינת את שתי הפעולות המרכזיות שאברהם עשה: הוא רץ לקראת האורחים והזמין אותם לנוח ולאכול. תשובה מלאה יכולה להיות: אברהם קיבל את האורחים בכך שרץ לקראתם והזמין אותם לנוח ולאכול."
'''
new = '''A good teacher_response is:
"נכון, כי ציינת שאברהם רץ לקראת האורחים והזמין אותם לנוח ולאכול. תשובה מלאה: אברהם קיבל את האורחים בכך שרץ לקראתם והזמין אותם לנוח ולאכול."
'''
if old not in backend:
    raise SystemExit('pedagogy example block not found')
backend = backend.replace(old, new, 1)

# 3) Bump build/cache.
index = index.replace('IAKIDS • build 0.7.30', 'IAKIDS • build 0.7.31')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.30";', 'window.IAKIDS_BUILD_VERSION = "0.7.31";')
index = index.replace('/he/workspace/lesson-completion.js?v=0730', '/he/workspace/lesson-completion.js?v=0731')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.30";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.31";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0730', '/he/workspace/lesson-completion-core.js?v=0731')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
BACKEND.write_text(backend, encoding='utf-8')

print('Homework success feedback split into two short bubbles/audio chunks; build 0.7.31')
