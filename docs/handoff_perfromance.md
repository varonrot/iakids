# handoff_perfromance — שרידות וביצועים של הטוטור העברי

תאריך: 2026-09-14
שירות: `backend-ai-tutor-he/main.py` (כ-19,800 שורות, 20 ראוטים), רץ ב-Render בכתובת
`https://iakids-ai-tutor-he.onrender.com` (הפרונט קורא אליו מ-`he/workspace/index.html:24309`).

## השאלה שנבדקה

האם כדאי להעביר את הטוטור ל-AWS Lambda / פונקציות serverless כדי לשפר שרידות?

## תשובה

**לא.** Lambda לא פותר את בעיות השרידות הקיימות, ובמצב הקוד הנוכחי יחמיר אותן.
השרידות תגיע מהוצאת עבודות הרקע לתור עם worker נפרד, ומהרצת שני מופעים של השרת.

## מה נמצא בקוד (עם מיקומים)

### 1. עבודות רקע אחרי שליחת התשובה — החסם הגדול ביותר

הקוד מחזיר תשובה על שיעור ואז ממשיך לעבוד באותו תהליך דרך `BackgroundTasks`:

| פונקציה | שורה | מה היא עושה |
|---|---|---|
| `generate_kid_lesson_intro_videos_background` | 6895 | וידאו פתיחה ב-Gemini, פולינג עד 60 × 5 שניות (עד 5 דקות), `time.sleep(5)` בשורה 6459 |
| `generate_all_lesson_visuals_background` | 8187 | תמונות לכל חלקי השיעור, ריטריי עם `time.sleep` בשורה 8533 |
| `generate_transition_video_background` | 8976 | וידאו מעבר |
| `generate_unit_lesson_media_background` | 8991 | כל המדיה של יחידת שיעור |
| `generate_unit_lesson_audio_background` | 9982 | TTS (מודל `gemini-3.1-flash-tts-preview`, שורה 4181), העלאת WAV ל-Supabase Storage |

נקודות הקריאה: שורות 11052, 11485, 12120, 12154, 12231, 13139, 13465.

ב-Lambda התהליך מוקפא ברגע שהתשובה נשלחת. כל העבודות האלה ימותו בשקט.
גם היום: כל ריסטארט של Render באמצע ייצור מאבד את הווידאו/האודיו בלי סימן.

### 2. קוד חוסם, מודל של תהליך ארוך-חיים

- `supabase_with_retry` (שורה 395) עם `time.sleep` סינכרוני.
- קריאות OpenAI / Gemini / Supabase רצות ב-`run_in_threadpool`.
- `WORKER_THREADS=128` (שורה 502) מורחב ב-startup (שורה 508). זה כיוונון לתהליך שחי הרבה זמן.

### 3. מצב בזיכרון התהליך

- מגביל קצב (rate limiter) במידלוור, שורות 504-505 ו-526-551: `_rate_buckets` בזיכרון.
- ב-Lambda כל מופע מתחיל מאפס, המגבלה חסרת משמעות.
- גם עם שני מופעים ב-Render המגבלה מפסיקה להיות מדויקת.

### 4. בקשות ארוכות בלי streaming

- ייצור שיעור עם `gpt-5.6-sol` כולל ריטריי (שורות 15897-15972) יכול לקחת דקה ויותר.
- אין `StreamingResponse` ואין websocket בקוד.
- API Gateway חותך ב-29 שניות כברירת מחדל.

### 5. קולד סטארט

ייבוא של `google-genai`, `openai`, `supabase` וקובץ של 500KB יתן 3-8 שניות בקריאה הראשונה.

### מה כן ידידותי ל-serverless

אין websocket, אין streaming, אין מצב מודולרי חוץ ממגביל הקצב. הראוטים עצמם כמעט stateless.

## תוכנית עבודה מומלצת (לפי עדיפות)

### שלב 1 — תור עבודות במקום BackgroundTasks (השינוי היחיד שנותן שרידות אמיתית)

- טבלה ב-Supabase, למשל `media_jobs`: `id, unit_lesson_id, job_type, status (pending/running/done/failed), attempts, error, created_at, updated_at`.
- הראוטים רק מכניסים שורה לטבלה במקום `background_tasks.add_task(...)`.
- worker נפרד (תהליך Python קטן, אפשר Render Background Worker או קונטיינר על השרת הזה) מושך `pending`, מסמן `running`, מריץ את הפונקציות הקיימות מהטבלה למעלה, מסמן `done`/`failed`.
- ריטריי אוטומטי: `running` שלא התעדכן X דקות חוזר ל-`pending`.
- הפרונט כבר מפעיל פולינג על `hero-image` / `visuals` / `unit-lesson/audio` (workspace שורות 17552, 17850, 18044) אז לא צריך שינוי בצד הלקוח.
- הערכה: יומיים.

### שלב 2 — שני מופעים ב-Render + מגביל קצב חיצוני

- להעלות ל-2 instances. בדיקת הבריאות ב-`/` (שורה 513) כבר קיימת.
- להעביר את `_rate_buckets` ל-Redis (יש קונטיינר `redis:7-alpine` על השרת הזה, פורט 6379) או לטבלה ב-Supabase.

### שלב 3 — timeout מפורש על כל קריאה חיצונית

- `timeout=` על כל קריאת OpenAI ו-Gemini, כדי שבקשה תקועה לא תתפוס thread לנצח.
- לבדוק: `grep -n 'timeout=' main.py` מראה שכמעט אין.

## אם בכל זאת רוצים serverless

- ההתאמה הנכונה היא **Cloud Run** עם `min-instances=1` ו-CPU מוקצה תמיד, לא Lambda. זה שומר על מודל התהליך הקיים.
- גם שם שלב 1 חובה.
- מעבר ל-Lambda ידרוש: פיצול חמש פונקציות הרקע (כ-3,000 שורות קוד מדיה) לשירות נפרד, מתאם Mangum, פיצול הקובץ הגדול, העברת מגביל הקצב החוצה. כשבועיים עבודה, ובסוף אותה שרידות ששלב 1 לבד נותן ביומיים.

## מצב השרת המקומי (למידע)

- על המכונה הזו רץ רק האתר הסטטי: קונטיינר `iakids-site` (nginx:alpine, `127.0.0.1:3020`, compose ב-`/opt/iakids-deploy`). הופעל מחדש ב-2026-09-14.
- הבקאנד של הטוטור לא רץ כאן, רק ב-Render.

## סטטוס ביצוע — 2026-09-14

### שלב 1 בוצע בקוד (לא קומיט, לא נבדק מול Supabase אמיתי עדיין)

- `supabase/migrations/20260914_media_jobs.sql` — טבלת `media_jobs` + 5 פונקציות RPC: `enqueue` (עם dedupe על עבודה חיה), `claim` (SKIP LOCKED, בטוח לכמה workers), `heartbeat`, `finish` (done / pending עם backoff / failed), `requeue_stale` (reaper). RLS דלוק בלי policies: רק service role.
- `backend-ai-tutor-he/main.py` — בלוק חדש אחרי מגביל הקצב: `dispatch_media_job`, `enqueue_media_job`, `run_media_job`. שבע נקודות הקריאה של `background_tasks.add_task` הוחלפו. דגל `MEDIA_JOBS_MODE=queue|inline` (ברירת מחדל queue). אם ההכנסה לתור נכשלת, העבודה רצה inline כמו היום.
- `backend-ai-tutor-he/worker.py` — תהליך נפרד: מושך, מריץ את אותן פונקציות, heartbeat כל 30 שניות, reaper כל דקה, SIGTERM מסיים בעדינות. `WORKER_CONCURRENCY` (ברירת מחדל 2).

### מה נבדק

- בדיקות אופליין עם Supabase מדומה: fallback ל-inline כשהתור לא זמין, enqueue דרך RPC, ניתוב סוגי עבודות, לולאת worker מלאה עם הצלחה / כישלון עם ריטריי / סוג לא מוכר.
- ה-SQL הורץ פעמיים (אידמפוטנטי) על Postgres 16 מקומי ב-Docker ונבדקו: dedupe, claim בין שני workers בלי חפיפה, backoff, finish של worker לא נכון מתעלם, reaper מחזיר ל-pending או failed.

### מה צריך כדי לבדוק end-to-end

1. להריץ את ה-SQL ב-SQL Editor של פרויקט ה-dev ב-Supabase.
2. `.env.dev` — `SUPABASE_SERVICE_ROLE_KEY` ריק. בלי זה אי אפשר להריץ את הבקאנד מקומית מול dev.
3. להריץ: `cd backend-ai-tutor-he && APP_ENV=dev ../backend/.venv/bin/python worker.py` לצד `uvicorn main:app`.
4. ב-Render: שירות Background Worker חדש, אותו repo ואותם env vars, פקודת הפעלה `python worker.py`.

### מדדים תפעוליים (נוסף 2026-09-14, אחרי הבדיקה הראשונה שעברה)

- `supabase/migrations/20260914_ops_metrics.sql` — `media_jobs` מקבל `started_at / duration_ms / metrics`; טבלאות `request_log` (בקשה ל-/api/*: ראוט, סטטוס, ms) ו-`service_metrics` (כל 30 שניות לכל תהליך: RSS, CPU, זיכרון פנוי, load, בקשות במקביל / עבודות רצות / אורך תור). views מוכנים: `media_jobs_hourly`, `request_log_hourly`, `service_metrics_5min`. ניקוי אוטומטי אחרי 30 יום (`ops_metrics_prune`). סגור ל-anon.
- `backend-ai-tutor-he/ops_metrics.py` — מודול משותף. כתיבה ב-batch מ-thread רקע, אף פעם לא בתוך הבקשה. `OPS_METRICS_ENABLED=0` מכבה. עותק מקומי ב-`/var/log/iakids/*.metrics.log`.
- `main.py` — מידלוור `_request_log` ודיווח משאבים בהפעלה. `worker.py` — שיא RSS לכל עבודה נשמר ב-`media_jobs.metrics`.
- `tools/e2e_media_jobs.py` — כותב ל-`/var/log/iakids/e2e/<run>/` (server.log, worker.log, resources.csv, phases.log) ומדפיס טבלת CPU/זיכרון לפי שלב.

תוצאת הבדיקה הראשונה על הפרוד (שיעור מה-cache, ילד איתן): PASS. וידאו פתיחה 139 שניות ל-3 סרטונים, אודיו 105 שניות ל-17 קריאות TTS, תמונות 4.7 שניות (cache). RSS כ-100MB לכל תהליך. עם concurrency 1 האודיו חיכה 2:20 דקות מאחורי הווידאו.

### ריצות 2-3 על הפרוד (2026-09-14, יחידות חדשות 5 ו-6) — ממצאים

- ייצור שיעור: 70-92 שניות מול OpenAI, השרת ב-0-2% CPU בזמן הזה. עבודת מדיה: ~130 שניות, שיא RSS של ה-worker ~200MB. תמונה: 3.5-5 שניות, 3 במקביל.
- ריצה 2 קרסה בגלל המכונה: OOM (2GB, בלי swap, Cursor+Claude+mongo+postgres). נוסף swap 2GB.
- **Gemini TTS 429 RESOURCE_EXHAUSTED** — המכסה של מודל ה-TTS נגמרת כבר עם worker אחד. זו התקרה האמיתית.
- Supabase Storage "Server disconnected" (HTTP/2 idle) הפיל אודיו+תמונות בבת אחת. 400 INVALID_ARGUMENT מזדמן מה-TTS.
- תיקונים: ריטריי TTS (4 ניסיונות, 20/40/60 שניות על 429, timeout 90 שניות), ריטריי על כל upload/download ל-Storage, כישלון אודיו מכשיל את העבודה בתור (retry אוטומטי), 5 ניסיונות לעבודת מדיה.
- **event loop חסום**: 72 קריאות DB סינכרוניות (authenticate_user, get_child_by_id, ...) רצו ישירות על ה-loop ב-12 ראוטים async. `tools/async_db_helpers.py` העביר אותן ל-threadpool. בדיקה: 8 בקשות במקביל עם auth של שנייה — 1.1 שניות במקום 8.
- פולינג בפרונט בשיעור חדש: audio כל 1.5 שניות ×40, visuals כל 1.5 שניות ×30, waitForLessonVisual כל שנייה ×120. יחד עד ~160 בקשות לדקה לילד, מעל מגביל הקצב (60/דקה). לוודא ב-`request_log_hourly` (עמודת rate_limited) אחרי פתיחת שיעור חדש מהדפדפן.

### בדיקות עומס (2026-09-14, 10:01-10:13) — ממצאים ותיקונים

מדידה, 30 במקביל, 60 בקשות לראוט, מגביל קצב מורם:

| ראוט | p50 | req/s | CPU שרת | הערה |
|---|---|---|---|---|
| units (GET) | 691ms | 36.5 | 43% | DB בלבד. ~12ms CPU לבקשה → ~85 req/s לליבה |
| active-lesson-state | 1025ms | 29.8 | 32% | DB בלבד |
| shared-transition | 341ms | 51.6 | 18% | DB בלבד |
| hero-image | 9035ms | 2.9 | 121%, RSS 493MB | 30 בקשות → 30 ייצורי תמונה במקביל, בלי dedupe |
| visuals | 6740ms | 3.5 | 38% | signed URL לכל תמונה (21) לכל בקשה |
| audio | ~5.5 שניות לבקשה | | | signed URL לכל קטע (17+) לכל בקשה |
| unit-lesson | 17s (כולן יחד) | 1.7 | 13% | audio + visuals + intro signed URLs לכל בקשה |

תיקונים:
- לקוח Supabase: HTTP/2 יחיד → HTTP/1.1 עם pool של 100 (בנצ'מרק: פי 3.5 → פי 16 מקבילות; HTTP/2 sync קרס ב-30 threads).
- cache ל-signed URLs (תוקף שעה, רענון 5 דקות לפני), חתימת כל קטעי האודיו של שיעור בקריאה אחת (`create_signed_urls`).
- נעילה לייצור hero לכל שיעור: 30 בקשות במקביל → ייצור אחד.
- `storage_with_retry`: ריטריי רק על ניתוקי רשת; "Object not found" חוזר מיד (הצינור משתמש בזה כ"עדיין לא נוצר").
- 72 קריאות DB סינכרוניות בראוטים async הועברו ל-threadpool (`tools/async_db_helpers.py`).

כלים: `tools/load_api.py` (עומס לכל ראוט / סימולציית ילדים / ראוטי AI), `tools/e2e_media_jobs.py --load N`.

### ריצות עומס אחרי התיקונים (10:39-10:58)

| ראוט | לפני | אחרי |
|---|---|---|
| hero-image | p50 9.0s, 2.9 req/s, RSS 493MB | p50 1.5s, 18 req/s, RSS 136MB |
| visuals | 6.7s, 3.5 req/s | 3.2s, 11 req/s (CPU 99% בשיא — JSON גדול לכל בקשה) |
| unit-lesson | 17s, 1.7 req/s | 7.4s, 4.9 req/s (עדיין lockstep — 30 בקשות של אותו ילד לאותו שיעור מתחרות על שורות progress) |
| audio | 5.5s לבקשה | 27×500: הראוט ייצר TTS בתוך הבקשה, 30 במקביל, מכסת Gemini נגמרה |

- 50 ילדים מדומים לדקה, מגביל קצב דלוק: 2,116 בקשות, **1,514 (72%) קיבלו 429**. הפולינג של ה-workspace (audio+visuals כל 1.5 שניות) חורג ממגביל 60/דקה. חובה לתקן בפרונט (מרווח 3-5 שניות + backoff, או Realtime) ו/או להחריג את ראוטי הפולינג מהמגביל.
- צ'אט 5 במקביל: p50 4.5-6 שניות, 0 שגיאות. TTS חי: 5/5 נכשלו — **מכסת Gemini TTS נגמרה** (429 גם על קריאה בודדת). כל בדיקת TTS תיכשל עד שהמכסה תתחדש / תוגדל.
- תיקונים: ראוט `audio` לא מייצר יותר בתוך הבקשה — מכניס עבודה לתור ומחזיר "generating" (dedupe לשיעור). `generating` תקוע מעל 10 דקות נלקח מחדש על ידי ה-worker (קודם שיעור שה-worker שלו מת נשאר "generating" לנצח).
- עדיפויות בתור (`20260914_media_jobs_priority.sql`, הורץ בפרוד): אודיו/מדיה 10, visuals 30, סרטוני פתיחה 60, מעבר 90. ה-hero נוצר ראשון בתוך עבודת המדיה.

### פולינג בפרונט (he/workspace/index.html) — תוקן 2026-09-14

- פונקציה חדשה `iakidsPollSleep(attempt, baseMs, status)`: מתחיל ב-2-2.5 שניות, גדל פי 1.5 עד 8, jitter, 20 שניות אחרי 429, 5 אחרי 5xx, ולא שואל כשהטאב מוסתר.
- כל 7 לולאות הפולינג עוברות דרכה: אודיו (30 ניסיונות, תקציב ~220 ש׳; קודם 40×1.5 = 60 ש׳ — פחות מזמן ייצור האודיו!), תמונות, תמונה-תמונה (40 במקום 120), וידאו מעבר, ייצור שיעור (30 במקום 20).
- 37 סקריפטים inline נבדקו ב-node --check, 0 שגיאות. לא נבדק בדפדפן עדיין.
- `tools/load_api.py --children` מדמה עכשיו את הפולינג החדש; `--old-polling` את הישן, להשוואה.

### אופציית OpenRouter (2026-09-14)

- `AI_PROVIDER=openrouter` — צ'אט וייצור שיעור דרך OpenRouter (אותו OpenAI SDK, base_url אחר, מודלים עם קידומת `openai/`). `TTS_PROVIDER=openrouter` — TTS דרך `/api/v1/audio/speech` עם **אותו מודל** `google/gemini-3.1-flash-tts-preview`, קול Aoede, פלט PCM 24kHz (אותם בייטים, אותה עטיפת WAV). ברירת מחדל: `direct` (ללא שינוי). דורש `OPENROUTER_API_KEY`.
- למה: מכסת ה-TTS שנגמרה היא של חשבון Google AI Studio שלנו. ב-OpenRouter מודלים בתשלום הם ללא תקרת בקשות קבועה (עד הקרדיט ומה שהספק למעלה מאפשר). המחיר שם: $1/M input, $20/M output tokens למודל ה-TTS.
- לא דרך OpenRouter עדיין: תמונות (Gemini image, מודל אחר ומבנה תשובה אחר ב-OpenRouter).
- בדיקה: `TTS_PROVIDER=openrouter OPENROUTER_API_KEY=... tools/tts_check.py --n 5` — משפט אחד, מדפיס latency, שומר WAV להאזנה ב-/var/log/iakids/.
- לא נבדק עדיין מול OpenRouter אמיתי (אין מפתח על השרת). נבדק אופליין: prefix מודלים, WAV, ריטריי, ראוט חי.

### רישום עלות לכל קריאת AI (2026-09-14)

- `supabase/migrations/20260914_ai_calls.sql` — טבלת `ai_calls`: שורה לכל קריאה: service, provider, model, purpose, user/kid/unit_lesson, טוקנים, שניות אודיו, תמונות, latency, status, cost_usd, cost_source (provider / estimated / unknown / pending), generation_id. views: `ai_costs_daily`, `ai_costs_per_kid`, `ai_costs_per_lesson`. שמירה שנה. נבדק על Postgres זמני: טבלאות קיימות לא נגעו, אידמפוטנטי, anon חסום. **טרם הורץ בפרוד.**
- `backend-ai-tutor-he/ai_costs.py` — עוטף את הלקוחות עצמם (OpenAI sync+async, Gemini generate_content sync+async, interactions.create) כך שכל 17 נקודות הקריאה נרשמות בלי לגעת בהן. contextvar עם purpose/kid/lesson נקבע בכל ראוט (`ai_context`) וב-worker לכל עבודה; עובר גם דרך ה-ThreadPoolExecutor של עבודת המדיה (`run_in_context`).
- עלות: OpenRouter צ'אט — מדויק מ-`usage.cost`; OpenRouter TTS — generation_id ואז `/generation?id=` (thread רקע, `ai_calls_set_cost`); OpenAI/Gemini ישיר — הערכה מטבלת מחירים (`MODEL_PRICING_USD`, `AI_PRICES_JSON`, `AI_IMAGE_PRICES_JSON`); בלי מחיר — `unknown` (ה-view סופר אותם).
- נמדד היום: קטע TTS של 6 שניות דרך OpenRouter = ~$0.0033 (165 טוקני פלט × $20/M). שיעור של 17-19 קטעים ≈ $0.06 אודיו.
- לפני זה היו רק סיכומים: usage_summary (למשתמש) ו-tutor_sessions.estimated_cost_usd (לסשן), רק מצ'אט ו-TTS חי, בלי מודל/ספק. הם נשארו כמו שהיו.

### סיום היום (2026-09-14, 13:35)

- בדיקת קריסה יזומה: PASS. SIGKILL 20 שניות לתוך עבודת מדיה; worker חדש, reaper החזיר אחרי 60 שניות, ניסיון 2 השלים (hero + 6 תמונות מה-cache, 8 תמונות + 14 קטעי TTS מחדש, 183 שניות). מה שאבד: 4 קטעי TTS של הניסיון הראשון (~$0.013) — אין cache לקטע.
- תוקן בדרך: `get_unit_lesson` לא החזיר `updated_at`, אז "generating" תמיד נחשב תקוע (age 601). עכשיו הגבול של 10 דקות עובד.
- חיובים: OpenRouter היום $0.267 מתוך $10 קרדיט, ~80 קריאות TTS. OpenAI/Gemini ישיר: לא נמדד בלוגים; `usage_summary` של המשתמש מחזיק את ההערכה; מהמיגרציה `ai_calls` והלאה — לכל קריאה.
- דוח PDF מעודכן: `tools/iakids-tutor-report.pdf` (7 עמודים, כולל עלויות).

### עלות אמיתית של יחידת שיעור אחת (שיעור 11, 17:45, ai_calls)

| רכיב | קריאות | עלות | חלק |
|---|---|---|---|
| תמונות, gemini-3.1-flash-lite-image ($0.0336/תמונה, ai.google.dev) | 20 | $0.672 | 82% |
| אודיו, OpenRouter (מדויק) | 19, 164 שניות אודיו | $0.083 | 10% |
| ייצור שיעור, gpt-5.6-sol ×3 + gpt-4o-mini ×2 | 5 | $0.060 | 7% |
| **סה"כ ליחידה** | 44 | **$0.82** | |

זמן: ייצור 81 ש׳ + מדיה 339 ש׳ (TTS ממוצע 12 ש׳ לקריאה הערב, 23 קריאות תמונה = 108 ש׳).

### הקוריקולום (מה-DB, 2026-09-14)

- `learning_lessons`: 1,893 (כיתה א׳ 314, ב׳ 286, ג׳ 286, ד׳ 313, ה׳ 336, ו׳ 358), 5-7 מקצועות לכיתה, 38-50 קטגוריות לכיתה.
- `lesson_units_content`: 150 יחידות בלבד, כולן לכיתה ה׳ מדעים, 6 שיעורי-אב × ~25 יחידות (4 units × 6-8 sub-lessons). 10 נוצרו, 8 עם אודיו.
- אם כל שיעור-אב מקבל 25 יחידות: ~47,300 יחידות × $0.82 ≈ $39k, ו-4,450 שעות worker (concurrency 1) במסלול הנוכחי.
- ילדים: 133, גילאים 1-15 (רוב 5-11). הראוט משווה `age` לכיתה 1-6 → ילדים עם age 7-15 (82 מתוך 133) חסומים משיעורי יחידה.

### 2026-09-15: פריסה מקומית + OpenRouter + אודיו פרוגרסיבי

- **הבקאנד רץ על המכונה הזו**: systemd `iakids-tutor-web` (uvicorn, 127.0.0.1:8011) ו-`iakids-tutor-worker`, משתמש `iakids`, `APP_ENV=prod AI_PROVIDER=openrouter TTS_PROVIDER=openrouter MEDIA_JOBS_MODE=queue`. קבצים + `install.sh` אידמפוטנטי ב-`/opt/iakids-deploy/tutor/` (להריץ אחרי `git pull` כדי לאתחל עם קוד חדש; הגיבוי של קובץ ה-nginx נשמר שם ולא ב-sites-enabled). nginx: `location ^~ /tutor-api/` ב-`smarts-brains.online` → 8011, timeout 300 ש׳. הפרונט (5 קבצים חיים + game-sdk) בוחר `/tutor-api` רק בדומיין smarts-brains.online; iakids.app נשאר מול Render.
- **שיעור 31 (11:17, הילד הראשון שפתח)**: 47 קריאות + 13 TTS חי, $0.85. טקסט דרך OpenRouter $0.024 מדויק (הטבלה בקוד מנפחת פי 2.5), TTS $0.09 + $0.033 חי, תמונות Gemini ישיר 21 × $0.0336 (הערכה). ייצור טקסט 100 ש׳ (5 קריאות עוקבות, האחרונה 39 ש׳), מדיה 134 ש׳.
- **מה באמת קרה לילד**: אחרי הטקסט ה-workspace נכנס ל-`live_tts` ושלח 11 קריאות TTS במקביל (חלק 1) בזמן שה-worker יצר את אותם קטעים לאחסון — TTS כפול לכל שיעור חדש, והפרץ הזה הפיל את ה-worker ל-429 של OpenRouter (`new-account-rpm`: 20 בקשות/דקה למודל ה-TTS, לא מתועד; retry עם backoff עבד, 23 ש׳ עיכוב). חלק 2+ תמיד היה TTS חי גם בשיעורים שמורים (`runUniversalLessonPart` שלח `lesson_audio: null`).
- **אודיו פרוגרסיבי (בוצע, לא נבדק עדיין בדפדפן)**: ה-worker שומר `lesson_audio_json` חלקי אחרי כל קטע (`partial: true`, `complete` לכל חלק, סטטוס נשאר `generating`); `/unit-lesson/audio` ו-`/unit-lesson` מחזירים את החלקי (`source: partial` / `audio_mode: stored_progressive`). ב-workspace: `pickLessonAudioPart` בוחר את החלק הנוכחי מ-`parts`, `createProgressiveLessonAudio` מושך כל 2.5 ש׳ ומחזיר לכל פסקה את הקובץ השמור ברגע שקיים; TTS חי רק לפסקה שלא הגיעה תוך 8 ש׳ מרגע שצריך אותה. חלק 2+ משתמש ב-`window.CURRENT_STORED_LESSON_AUDIO`. צפוי: 0 קריאות TTS חי בשיעור חדש, בלי פרץ, בלי 429.
- **פתוח**: בדיקת שיעור חדש בדפדפן אחרי restart; `CRITICAL VISUAL COUNT MISMATCH` בלוג הוא אזעקת שווא (משווה קטעי חלק 1 מול כל הוויזואלים); בדיקת cache של ה-Hero מנסה 404 שלוש פעמים (2 ש׳); `ai_costs_per_lesson.media_cost_usd` לא כולל `purpose='media'`.
