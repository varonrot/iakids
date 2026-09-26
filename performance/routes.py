"""Every route of the tutor API (backend-ai-tutor-he/main.py), and how to load-test it.

The gate (tools/prompt_gate.py, performance_checks) fails when main.py has a route that is
not listed here, so a new endpoint cannot ship without a performance test.

Fields
  method, path   as declared in main.py; {kid} {ul} {ll} {bank} are filled at run time
  body           JSON body, same placeholders
  kind           health | read | write | model | media | admin
                   read   database reads only
                   write  writes rows (progress, sessions, uploads)
                   model  calls a language / speech model (faked in every run)
                   media  may start image / video / audio generation (queued, faked)
                   admin  admin-only page, measured once, never ramped
  p95_ms         the latency budget at the tested concurrency with the FAKE model delays
                 at --scale 1 (production medians). Over it = the route is not keeping up.
  ramp           False: measured with a single request only (admin, destructive, one-off)
  db_max         database calls per request, warm (the gate fails above it). Set from the
                 2026-09-25 measurement after the request caches; raise it only with a reason.
Whether a route is safe to run against production is not declared here: run.py measures it
on the fake database (no writes, no model calls = prod-safe) and writes it into the results.
"""

UL = "{ul}"
KID = "{kid}"

ROUTES = {
    # ---------------------------------------------------------------- health
    "health":               dict(method="GET",  path="/", kind="health", p95_ms=200, db_max=0),

    # ---------------------------------------------------------------- lesson screen (the hot path)
    "units":                dict(method="GET",  path="/api/learning-lessons/{ll}/units", kind="read", p95_ms=800, db_max=1),
    "active-lesson-state":  dict(method="POST", path="/api/tutor/active-lesson-state", body={"kid_id": KID}, kind="read", p95_ms=800, db_max=1),
    "lesson-intro":         dict(method="POST", path="/api/tutor/lesson-intro", body={"kid_id": KID, "unit_lesson_id": UL}, kind="read", p95_ms=1000, db_max=9),
    "unit-lesson":          dict(method="POST", path="/api/tutor/unit-lesson", body={"kid_id": KID, "unit_lesson_id": UL}, kind="media", p95_ms=1500, db_max=3),
    "unit-lesson-closing":  dict(method="POST", path="/api/tutor/unit-lesson/closing", body={"kid_id": KID, "unit_lesson_id": UL}, kind="model", p95_ms=30000, db_max=2),
    "regenerate-transition": dict(method="POST", path="/api/tutor/unit-lesson/regenerate-transition", body={"kid_id": KID, "unit_lesson_id": UL}, kind="media", p95_ms=30000, ramp=False, db_max=3),
    "hero-image":           dict(method="POST", path="/api/tutor/unit-lesson/hero-image", body={"kid_id": KID, "unit_lesson_id": UL}, kind="media", p95_ms=1500, db_max=1),
    "visuals":              dict(method="POST", path="/api/tutor/unit-lesson/visuals", body={"kid_id": KID, "unit_lesson_id": UL}, kind="read", p95_ms=800, db_max=1),
    "audio":                dict(method="POST", path="/api/tutor/unit-lesson/audio", body={"kid_id": KID, "unit_lesson_id": UL}, kind="media", p95_ms=800, db_max=1),
    "shared-transition":    dict(method="GET",  path="/api/tutor/shared-transition/middle", kind="read", p95_ms=800, db_max=0),
    "structured-lesson":    dict(method="POST", path="/api/tutor/lesson", body={"kid_id": KID, "lesson_id": "{ll}", "unit_lesson_id": UL, "message": "אני חושב שהתשובה היא שלוש"}, kind="model", p95_ms=30000, db_max=10),
    "reset-unit-lesson":    dict(method="POST", path="/api/tutor/reset-unit-lesson", body={"kid_id": KID, "lesson_id": "{ll}", "unit_lesson_id": UL}, kind="write", p95_ms=1500, ramp=False, db_max=6),

    # ---------------------------------------------------------------- chat / homework (model routes)
    "tutor-chat":           dict(method="POST", path="/api/tutor/chat", body={"kid_id": KID, "message": "מה זה מערכת אקולוגית?"}, kind="model", p95_ms=9000, db_max=6),
    "openai-clean-chat":    dict(method="POST", path="/api/tutor/openai-clean-chat", body={"kid_id": KID, "message": "תסביר לי מה זה שבר", "history": []}, kind="model", p95_ms=9000, db_max=0),
    "homework-coach":       dict(method="POST", path="/api/tutor/homework-coach", body={"kid_id": KID, "source_text": "1. 3+4=?\n2. 5+6=?", "current_question": "3+4=?", "message": "לא הבנתי"}, kind="model", p95_ms=30000, db_max=0),
    "homework-coach-v2":    dict(method="POST", path="/api/tutor/homework-coach-v2", body={"kid_id": KID, "source_text": "1. 3+4=?", "current_question": "3+4=?", "message": "לא הבנתי"}, kind="model", p95_ms=30000, db_max=0),
    "homework-turn":        dict(method="POST", path="/api/tutor/homework-turn", body={"kid_id": KID, "current_question_number": 1, "current_question": "3+4=?", "answer": "7", "source_text": "1. 3+4=?\n2. 5+6=?"}, kind="model", p95_ms=30000, db_max=3),
    "homework-session-start": dict(method="POST", path="/api/tutor/homework-session/start", body={"kid_id": KID, "subject": "math", "total_questions": 2}, kind="write", p95_ms=1500, db_max=1),
    "homework-analyze":     dict(method="POST", path="/api/tutor/homework-analyze", body={"kid_id": KID, "storage_path": "perf/test.jpg"}, kind="model", p95_ms=40000, db_max=0),
    "curriculum-chat":      dict(method="POST", path="/api/curriculum/chat", body={"kid_id": KID, "message": "אני רוצה ללמוד על חלל"}, kind="model", p95_ms=30000, db_max=5),
    "curriculum-approve":   dict(method="POST", path="/api/curriculum/approve", body={"kid_id": KID, "custom_subject_id": "1", "curriculum_id": "1"}, kind="write", p95_ms=1500, ramp=False, db_max=1),

    # ---------------------------------------------------------------- speech
    "tts":                  dict(method="POST", path="/api/tutor/tts", body={"kid_id": KID, "text": "שלום, איזה כיף שבאת ללמוד היום!"}, kind="model", p95_ms=8000, db_max=0),
    "stt":                  dict(method="POST", path="/api/tutor/stt", body={"kid_id": KID, "audio_base64": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=", "mime_type": "audio/wav"}, kind="model", p95_ms=6000, db_max=0),

    # ---------------------------------------------------------------- checks (בדיקות ומעקב)
    "check-set":            dict(method="GET",  path="/api/tutor/checks/comprehension/set?kid_id={kid}&grade=%D7%91", kind="read", p95_ms=800, db_max=0),
    "check-score":          dict(method="POST", path="/api/tutor/checks/score", body={"kid_id": KID, "bank": "comprehension", "unit_id": "g1A", "answers": {"q1": "א"}}, kind="read", p95_ms=800, db_max=0),
    "check-tts":            dict(method="POST", path="/api/tutor/checks/tts", body={"kid_id": KID, "text": "קראו את המשפט הבא בקול."}, kind="model", p95_ms=8000, db_max=0),
    "exam-practice-start":  dict(method="POST", path="/api/tutor/exam-practice/start", body={"kid_id": KID, "subject": "math", "topic": "שברים"}, kind="model", p95_ms=30000, db_max=0),
    "exam-practice-answer": dict(method="POST", path="/api/tutor/exam-practice/answer", body={"kid_id": KID, "set_id": "perf", "index": 0, "answer": 0}, kind="read", p95_ms=800, db_max=0),

    # ---------------------------------------------------------------- parent / kid pages
    "kid-list":             dict(method="GET",  path="/api/kid/list", kind="read", p95_ms=800, db_max=1),
    "kid-lessons":          dict(method="GET",  path="/api/kid/lessons?kid_id={kid}", kind="read", p95_ms=1000, db_max=3),
    "kid-achievements":     dict(method="GET",  path="/api/kid/achievements?kid_id={kid}", kind="read", p95_ms=1000, db_max=3),
    "kid-files":            dict(method="GET",  path="/api/kid/files?kid_id={kid}", kind="read", p95_ms=1000, db_max=2),
    "kid-get":              dict(method="GET",  path="/api/kid/{kid}", kind="read", p95_ms=800, db_max=0),
    "kid-update":           dict(method="POST", path="/api/kid/update", body={"kid_id": KID, "child_name": "ילד בדיקה"}, kind="write", p95_ms=1000, db_max=2),
    "kid-create":           dict(method="POST", path="/api/kid/create", body={"child_name": "ילד בדיקה", "age": 8}, kind="write", p95_ms=1000, ramp=False, db_max=3),

    # ---------------------------------------------------------------- English voice tutor (english_tutor.py, 2026-09-25)
    # {english_session} is the session_id the start route returned in this run
    "english-allowance":    dict(method="GET",  path="/api/english/allowance?kid_id={kid}", kind="read", p95_ms=800, db_max=1),
    "english-start":        dict(method="POST", path="/api/english/session/start", body={"kid_id": KID, "topic": "animals"}, kind="model", p95_ms=9000, db_max=4),
    "english-turn":         dict(method="POST", path="/api/english/turn", body={"kid_id": KID, "session_id": "{english_session}", "message": "I like dog"}, kind="model", p95_ms=9000, db_max=3),
    "english-end":          dict(method="POST", path="/api/english/session/end", body={"kid_id": KID, "session_id": "{english_session}"}, kind="write", p95_ms=1000, ramp=False, db_max=1),
    "english-sessions":     dict(method="GET",  path="/api/english/sessions?kid_id={kid}", kind="read", p95_ms=1000, db_max=1),

    # ---------------------------------------------------------------- English Test Prep (test_prep_2027.py): cached per diagnostic, one model call on a new one
    "test-prep-lesson":     dict(method="POST", path="/api/eng/test-prep/lesson", body={"kid_id": KID}, kind="model", p95_ms=9000, ramp=False, db_max=4),

    # ---------------------------------------------------------------- admin (measured once)
    "admin-whoami":         dict(method="GET",  path="/api/admin/whoami", kind="admin", p95_ms=800, ramp=False, db_max=0),
    "admin-lessons-quality": dict(method="GET", path="/api/admin/lessons/quality", kind="admin", p95_ms=3000, ramp=False, db_max=2),
    "admin-lesson-approve": dict(method="POST", path="/api/admin/lessons/{ul}/approve", body={"note": "perf"}, kind="admin", p95_ms=3000, ramp=False, db_max=2),
    "admin-lesson-recheck": dict(method="POST", path="/api/admin/lessons/{ul}/recheck", kind="admin", p95_ms=60000, ramp=False, db_max=4),
    "admin-lesson-regenerate": dict(method="POST", path="/api/admin/lessons/{ul}/regenerate", kind="admin", p95_ms=60000, ramp=False, db_max=5),
    "admin-image-approve":  dict(method="POST", path="/api/admin/lessons/{ul}/images/approve", body={"path": "perf.png"}, kind="admin", p95_ms=3000, ramp=False, db_max=2),
    "admin-image-regenerate": dict(method="POST", path="/api/admin/lessons/{ul}/images/regenerate", body={"path": "perf.png"}, kind="admin", p95_ms=60000, ramp=False, db_max=3),
    "admin-locks":          dict(method="GET",  path="/api/admin/security/locks", kind="admin", p95_ms=1000, ramp=False, db_max=0),
    "admin-lock-release":   dict(method="POST", path="/api/admin/security/locks/release", body={"ip": "203.0.113.9"}, kind="admin", p95_ms=1000, ramp=False, db_max=0),
    "admin-links":          dict(method="GET",  path="/api/admin/links", kind="admin", p95_ms=1000, ramp=False, db_max=0),
    "admin-qbank-summary":  dict(method="GET",  path="/api/admin/qbank/summary", kind="admin", p95_ms=3000, ramp=False, db_max=1),
    "admin-qbank-items":    dict(method="GET",  path="/api/admin/qbank/items?status=pending&limit=20", kind="admin", p95_ms=3000, ramp=False, db_max=1),
    "admin-qbank-review":   dict(method="POST", path="/api/admin/qbank/items/perf-missing/review", body={"status": "rejected", "note": "perf"}, kind="admin", p95_ms=3000, ramp=False, db_max=1),
    "admin-lesson-media":   dict(method="GET",  path="/api/admin/lessons/{ul}/media", kind="admin", p95_ms=3000, ramp=False, db_max=2),
}

# What one child in a lesson does per minute, used to turn requests/second into "children at once".
# From the workspace code: the lesson opens once (~every 8 min), audio + visuals are polled with backoff
# while media is generated, a chat message about every 40 s while working, TTS for each teacher reply.
# Re-derive from request_log (docs/PERFORMANCE.md queries) when the workspace changes.
CHILD_MIX_PER_MINUTE = {
    "active-lesson-state": 0.25,
    "unit-lesson": 0.125,
    "lesson-intro": 0.125,
    "visuals": 1.0,
    "audio": 1.0,
    "hero-image": 0.125,
    "structured-lesson": 1.0,
    "openai-clean-chat": 0.5,
    "tts": 1.5,
    "kid-get": 0.1,
}
