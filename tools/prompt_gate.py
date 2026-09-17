#!/usr/bin/env python3
"""Prompt gate — checks that ALWAYS run when a prompt file changes.

Why: on 2026-09-01 the {lesson_text} placeholder was dropped from
lesson_director_prompt.txt and nobody noticed for two weeks; every lesson's part 1
became the question chopped into sentences. This gate would have failed that commit.

    backend/.venv/bin/python tools/prompt_gate.py               # prompts changed vs HEAD
    backend/.venv/bin/python tools/prompt_gate.py --all         # every live prompt
    backend/.venv/bin/python tools/prompt_gate.py --staged      # git pre-commit (staged prompts)
    backend/.venv/bin/python tools/prompt_gate.py --hook        # Claude Code PostToolUse (stdin JSON)
    backend/.venv/bin/python tools/prompt_gate.py --pre-edit    # Claude Code PreToolUse: auto-backup
    backend/.venv/bin/python tools/prompt_gate.py --check-file X --as lesson_director_prompt.txt

Checks, per live prompt (the files main.py loads):
  1. file exists, UTF-8, not tiny, no merge markers / NUL bytes
  2. REQUIRED placeholders present (e.g. {lesson_text} in the director prompt) and every
     {placeholder} in the file is one main.py actually fills (string "{name}" in main.py)
  3. REQUIRED sections present (gender rule, shared-lesson neutrality, immutable question...)
  4. a backup exists: the HEAD version of a changed prompt is byte-identical to a copy in
     some V<N>_BACKUP/ (proves the backup was taken BEFORE the edit)
  5. render smoke (unless --fast): import main, build each prompt with sample data, and
     make sure no {placeholder} survives unresolved
Exit 0 = pass, 1 = fail (2 in --hook mode so Claude Code shows the reason).
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "backend-ai-tutor-he" / "prompts"
MAIN = ROOT / "backend-ai-tutor-he" / "main.py"
PY = ROOT / "backend" / ".venv" / "bin" / "python"

# every prompt main.py loads + what must never disappear from it
REQUIRED = {
    "iakids_ai_tutor_system_prompt.txt": {
        "placeholders": ["{child_name}", "{grade}", "{learning_interests}", "{usage_goals}", "{kids_memory}"],
        "sections": [],
    },
    "iakids_structured_lesson_prompt.txt": {
        "placeholders": [],
        "sections": ["RUNTIME_CONTEXT", "ADDRESSING THE CHILD", "Always communicate with the child in Hebrew",
                     "A HINT IS NEVER THE ANSWER"],
    },
    "iakids_lesson_expansion_prompt.txt": {
        "placeholders": ["{grade}", "{subject}", "{parent_lesson}", "{lesson_name}", "{learning_objective}",
                         "{lesson_complexity}", "{max_duration_seconds}", "{part_number}", "{previous_parts}"],
        "sections": ["השיעור משותף לכל הילדים", "answer:", "התשובה הנכונה והמלאה"],
    },
    "iakids_lesson_initial_prompt.txt": {
        "placeholders": ["{grade}", "{subject}", "{lesson_name}", "{learning_objective}"],
        "sections": ["השיעור משותף לכל הילדים", "עברית תקנית", "answer:", "התשובה הנכונה והמלאה"],
    },
    "lesson_director_prompt.txt": {
        "placeholders": ["{lesson_text}"],
        "sections": ["THE QUESTION IS IMMUTABLE", "lesson", "question", "מה אסור בתוך lesson"],
    },
    "iakids_lesson_transition_prompt.txt": {"placeholders": [], "sections": []},
    "iakids_lesson_closing_prompt.txt": {
        "placeholders": [],
        "sections": ["מה חייב להיות בסיכום", "spoken:", "learned:", "did_well:",
                     "to_strengthen:", "parent_note:", "אסור לשאול שאלה"],
    },
    "learning_coach_system_prompt.txt": {
        "placeholders": [],
        "sections": ["RUNTIME_DATA.child.gender", "אין להסיק את המגדר לפי שם הילד",
                     "רמז או דוגמה לעולם אינם התשובה", "correct_answer", "is_final_round", "הסבב האחרון: לתת את התשובה ולהמשיך", "התשובה הנכונה נתונה לך"],
    },
    "iakids_curriculum_builder_system_prompt.txt": {
        "placeholders": ["{child_name}", "{gender}", "{grade}", "{subject}"],
        "sections": [],
    },
    "iakids_homework_vision_prompt.txt": {"placeholders": [], "sections": []},
    "iakids_visual_director_prompt.txt": {"placeholders": [], "sections": ["NO TEXT INSIDE IMAGES", "READING DIRECTION", "CHILD SAFETY", "IMAGE COUNT IS DYNAMIC", "reuse_previous"]},
}
FEMALE_VOICES = {"Aoede", "Kore", "Leda", "Zephyr", "Autonoe", "Callirrhoe", "Despina", "Erinome", "Laomedeia", "Achernar", "Gacrux", "Pulcherrima", "Sulafat", "Vindemiatrix"}


def persona_checks(main_src: str) -> list:
    """The teacher persona in text is feminine ("אני שמחה"); the configured voice must match."""
    m = re.search(r'TTS_VOICE = os\.getenv\("TTS_VOICE", "([A-Za-z]+)"\)', main_src)
    voice = os.environ.get("TTS_VOICE") or (m.group(1) if m else "")
    if voice and voice not in FEMALE_VOICES:
        return [f"TTS_VOICE={voice} is not a female Gemini voice but the teacher texts are feminine (אני שמחה, מורה פרטית)"]
    return []
PLACEHOLDER = re.compile(r"\{[a-z_]+\}")


def sh(*cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True).stdout


def live_prompt_names():
    return list(REQUIRED.keys())


def check_file(path: Path, name: str, main_src: str, head_text: str | None, verbose=True):
    """Return list of failures (strings)."""
    fails = []
    if not path.exists():
        return [f"{name}: file missing"]
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return [f"{name}: not valid UTF-8"]
    if b"\x00" in raw:
        fails.append(f"{name}: NUL byte")
    if len(text.strip()) < 200:
        fails.append(f"{name}: suspiciously short ({len(text.strip())} chars)")
    if re.search(r"^(<<<<<<< |=======$|>>>>>>> )", text, re.M):
        fails.append(f"{name}: git conflict markers")
    req = REQUIRED.get(name, {"placeholders": [], "sections": []})
    for ph in req["placeholders"]:
        if ph not in text:
            fails.append(f"{name}: REQUIRED placeholder {ph} is missing")
    for sec in req["sections"]:
        if sec not in text:
            fails.append(f"{name}: REQUIRED section/text missing: {sec!r}")
    for ph in sorted(set(PLACEHOLDER.findall(text))):
        if f'"{ph}"' not in main_src and f"'{ph}'" not in main_src and ph not in main_src:
            fails.append(f"{name}: placeholder {ph} is not filled anywhere in main.py (typo?)")
    # 4. backup discipline: the pre-change (HEAD) content must live in some V<N>_BACKUP
    if head_text is not None and head_text != text:
        backups = sorted(ROOT.glob("V*_BACKUP"), key=lambda p: int(re.sub(r"\D", "", p.name) or 0))
        found = None
        for b in reversed(backups):
            c = b / "backend-ai-tutor-he" / "prompts" / name
            if c.exists() and c.read_text(encoding="utf-8") == head_text:
                found = b.name
                break
        if not found:
            fails.append(f"{name}: changed vs HEAD but no V<N>_BACKUP holds the previous version — run "
                         f"`bash .claude/skills/backup/backup.sh` BEFORE editing prompts")
        elif verbose:
            print(f"   backup ok: previous version of {name} is in {found}")
    return fails


def coverage_checks(main_src: str) -> list:
    """Every prompt file main.py loads must have gate rules (REQUIRED); a loaded file that
    is not listed fails the gate — that is how a NEW prompt is forced through review."""
    fails = []
    loaded = set(re.findall(r'"prompts/([A-Za-z0-9_\-]+\.txt)"', main_src))
    for name in sorted(loaded - set(REQUIRED)):
        fails.append(f"NEW PROMPT {name} is loaded by main.py but has no gate rules: add it to REQUIRED in tools/prompt_gate.py "
                     f"(placeholders it needs, sections that must never disappear) in the same commit")
    for name in sorted(set(REQUIRED) - loaded):
        fails.append(f"gate lists {name} but main.py no longer loads it: remove it from REQUIRED or restore the load")
    for f in sorted(PROMPTS.glob("*.txt")):
        if f.name not in loaded:
            fails.append(f"orphan prompt file {f.name}: not loaded by main.py — delete it (old versions live in V<N>_BACKUP)")
    return fails


_CHILD_PROMPT_MARKERS = ("את מורה פרטית", "מורה פרטית מצוינת", "עזרי לילד", "הסבירי לילד", "למדי אותו")


def child_prompt_gender_checks(main_src: str) -> list:
    """Every route in main.py that builds a Hebrew system prompt for the child must carry the
    gender + Hebrew-correctness block. Added after 2026-09-17, when two routes that arrived
    from another branch (openai_clean_chat, homework_coach_v2) spoke to a girl in masculine."""
    fails = []
    blocks = re.split(r"\n(?=(?:async )?def )", main_src)
    for b in blocks:
        head = b.split("(", 1)[0].replace("async def", "").replace("def", "").strip()
        if not any(m in b for m in _CHILD_PROMPT_MARKERS):
            continue
        if "hebrew_child_prompt_block(" in b or "hebrew_gender_rule(" in b or "gender_rule" in b:
            continue
        fails.append(f"main.py: {head}() builds a Hebrew prompt for the child without a gender rule — "
                     f"start the prompt with hebrew_child_prompt_block(child)")
    return fails


def prompt_usage_checks(main_src: str) -> list:
    """A prompt file that is loaded but whose TEMPLATE is never used is dead: a rule added to it
    never reaches a child (2026-09-17: the shared-lesson neutrality rule sat in an unused file)."""
    fails = []
    for m in re.finditer(r"([A-Z_]+_PROMPT_TEMPLATE)\s*=", main_src):
        name = m.group(1)
        if len(re.findall(r"\b" + name + r"\b", main_src)) < 2:
            fails.append(f"main.py: {name} is loaded but never used — wire it in or delete its prompt file")
    return fails


WORKSPACE = ROOT / "he" / "workspace" / "index.html"
COMPLETION = ROOT / "he" / "workspace" / "lesson-completion-core.js"


LOG_MODE_PAGES = (
    "he/workspace/index.html",
    "he/games/workspace/index.html",
    "he/parent-panel/index.html",
    "he/index.html",
    "he/add-subject/index.html",
    "frontend-v2/homework.html",
)


def log_mode_checks() -> list:
    """Every page that prints must load the log switch, and load it FIRST.

    2026-09-17: the pages are static files served by nginx and GitHub Pages, so the
    prints cannot be stripped on the way out. One shim replaces the console methods
    instead - prod is silent apart from console.error, test prints everything. It only
    works if nothing runs before it, so the check is on the order, not just presence.
    """
    shim = ROOT / "assets" / "js" / "iakids-log-mode.js"
    if not shim.exists():
        return ["assets/js/iakids-log-mode.js is missing - every page would print in production"]
    text = shim.read_text(encoding="utf-8", errors="replace")
    bad = []
    if '"error"' in text:
        bad.append("console.error is in the silenced list - real failures would disappear "
                   "from production")
    for name in ("log", "warn", "table"):
        if '"%s"' % name not in text:
            bad.append("console.%s is no longer switched off in production" % name)
    for page in LOG_MODE_PAGES:
        path = ROOT / page
        if not path.exists():
            continue
        src = path.read_text(encoding="utf-8", errors="replace")
        at = src.find("iakids-log-mode.js")
        first = src.find("<script")
        if at < 0:
            bad.append("%s does not load the log switch - it would print in production" % page)
        elif first >= 0 and first < src.rfind("<script", 0, at):
            bad.append("%s loads a script before the log switch; anything it prints escapes "
                       "the switch" % page)
    return bad


def completion_screen_checks() -> list:
    """The end-of-lesson card: one clear next step, and a score that is not scraped."""
    if not COMPLETION.exists():
        return ["he/workspace/lesson-completion-core.js is missing"]
    src = COMPLETION.read_text(encoding="utf-8", errors="replace")
    bad = []
    if "lesson-completion-primary-next" not in src:
        bad.append("the completion screen has no single next-lesson button; the child is "
                   "back to picking from a grid of equal cards")
    if "LESSON_SIDEBAR_PROGRESS_ROWS" not in src or "mastery_score" not in src:
        bad.append("the completion score is read from the screen again instead of from the "
                   "progress row, so it can show the previous part's score")
    return bad


def workspace_checks() -> list:
    """The lesson screen regressions we actually shipped, each pinned by a rule.

    Every bug the user reports in the chat or in the prompt mechanism is added here
    or next to it, so the same failure cannot come back silently.
    """
    if not WORKSPACE.exists():
        return ["he/workspace/index.html is missing"]
    src = WORKSPACE.read_text(encoding="utf-8", errors="replace")
    bad = []

    # 2026-09-17: the whole lesson layout is scoped to body.lesson-theme-science and
    # the class was added only for the subject "מדעים", so a Hebrew or maths lesson
    # opened with no layout and its pictures were not shown in the middle.
    if "setLessonBackgroundForSubject" not in src:
        bad.append("setLessonBackgroundForSubject is gone - nothing marks the lesson screen")
    else:
        body = src.split("function setLessonBackgroundForSubject", 1)[1][:4000]
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)          # comments mention both classes
        body = re.sub(r"//[^\n]*", "", body)
        add_at = body.find("lesson-theme-science")
        cond_at = body.find("מדעים")
        if add_at < 0:
            bad.append("the lesson-screen class lesson-theme-science is no longer set")
        elif 0 <= cond_at < add_at:
            bad.append("the lesson layout is behind a subject condition again; it must "
                       "apply to every subject (only the background is science-only), "
                       "otherwise a Hebrew or maths lesson opens with no layout and no images")
        if "classList.toggle(" not in body:
            bad.append("the science background is no longer toggled by subject")
    if "lesson-subject-science" not in src:
        bad.append("lesson-subject-science is gone - the science background lost its own class")

    # 2026-09-17: a failing image could freeze the screen ~300 s per segment, and the
    # opening buffer waits for three images one after another.
    if "LESSON_VISUALS_GIVE_UP" not in src:
        bad.append("the visual wait has no give-up flag - a failed image can freeze the lesson again")
    if "LESSON_VISUAL_WAIT_BUDGET_MS" not in src:
        bad.append("waitForLessonVisual has no wait budget - images can block the lesson again")

    # 2026-09-17: a deploy restart takes ~16 s and nginx answers 502. A child who sent
    # her answer in that window got an error bubble and the lesson ended - in Spanish,
    # on a Hebrew page ("Algo salió mal").
    if "GATEWAY_STATUSES" not in src or "LEARNING COACH GATEWAY RETRY" not in src:
        bad.append("the lesson chat no longer retries a 502/503/504; a server restart "
                   "would end a child's lesson with an error")
    for foreign in ("Algo salió mal", "Intenta más tarde", "Something went wrong"):
        if foreign in src:
            bad.append("a non-Hebrew error message is shown to the child on the Hebrew "
                       "workspace: %r" % foreign)

    # 2026-09-17: the avatar URL was built straight from avatar_key, so a child whose
    # key has no file (avatar_key="dog") saw a broken image.
    if "iakidsAvatarUrl" not in src:
        bad.append("the avatar URL helper is gone - an unknown avatar_key would show a broken image")
    if re.search(r"avatars/\$\{", src):
        bad.append("an avatar URL is built straight from the key again, with no fallback "
                   "to an avatar that exists")

    # 2026-09-17 (second time): saving the child's details left the dialog open. The
    # profile was saved and then an element that does not exist on every screen threw,
    # so closeSettings() was never reached. After a successful save the dialog must
    # close no matter what the screen refresh does.
    if "async function saveSettings" in src:
        body = src.split("async function saveSettings", 1)[1][:9000]
        tail = body.split("kids_profiles", 1)[-1]
        if "finally" not in tail or "closeSettings()" not in tail:
            bad.append("saveSettings does not close the child-details dialog in a finally; "
                       "a failed screen refresh would leave it open after a successful save")
        for unguarded in ('document.getElementById(\n    "heroGreeting"\n  ).textContent',
                          'document.getElementById(\n    "rightbarName"\n  ).textContent'):
            if unguarded in tail:
                bad.append("saveSettings writes to an element that does not exist on every "
                           "screen without checking it first")

    # the closing must reach the child: fetched, rendered and spoken
    if "fetchLessonClosing" not in src or "renderLessonClosingCard" not in src:
        bad.append("the lesson closing is no longer fetched or rendered - the child would "
                   "get a video and three numbers with no summary")
    if "LESSON_CLOSING_VIDEO_MAX_MS" not in src:
        bad.append("the closing video is no longer cut short - a 20 s identical film would "
                   "again sit between the child and the summary")

    # the build stamp is read by the user; its two places must agree
    stamp = re.search(r"IAKIDS • build (\d+\.\d+\.\d+)", src)
    var = re.search(r'IAKIDS_BUILD_VERSION = "(\d+\.\d+\.\d+)"', src)
    if not stamp or not var:
        bad.append("the build stamp or IAKIDS_BUILD_VERSION is missing from the workspace")
    elif stamp.group(1) != var.group(1):
        bad.append("build stamp %s does not match IAKIDS_BUILD_VERSION %s" % (stamp.group(1), var.group(1)))
    return bad


def media_failure_checks(main_src: str) -> list:
    """A lesson whose images all failed must say so, not log DONE.

    2026-09-17: every image of lesson 152 failed on a corrupted API key and the media
    job still reported success, so the logs looked healthy while the child had a
    lesson with no pictures.
    """
    bad = []
    if "LESSON PART VISUAL GENERATION FAILED" not in main_src:
        bad.append("a part whose images all failed no longer logs an explicit FAILED line")
    if '"images_ok"' not in main_src or '"images_planned"' not in main_src:
        bad.append("the visual DONE line no longer reports images_ok / images_planned")
    if "def require_api_key" not in main_src:
        bad.append("require_api_key is gone - a corrupted key would again produce a "
                   "whole lesson with no images instead of refusing to start")
    return bad


# 2026-09-17: this list started as the Hebrew site only, and the same avatar bug was
# then found sitting untouched in the Spanish and Portuguese workspaces because they
# were never scanned. Every folder that serves a page belongs here.
BROWSER_FILES = ("he", "frontend-v2", "assets/js", "workspace", "pt", "de",
                 "games", "admin", "contact", "support", "support-dashboard",
                 "parent-dashboard", "onboarding")


# 2026-09-17: 178 when the rule was set, then 167 as screens shipped — but that count
# only ever looked at part of the site. Widening the scan to every folder that serves a
# page showed the true figure is 230. The number only moves down from here.
DB_CALL_BUDGET = 230


def browser_db_calls() -> tuple[int, list]:
    """Every direct database call left in a browser file."""
    found = []
    backupish = re.compile(r"(index2|_back_?up|_v\d+|_old|copy)", re.I)
    for folder in BROWSER_FILES + ("games", "admin", "contact", "support", "support-dashboard",
                                   "workspace", "pt", "de", "onboarding", "parent-dashboard"):
        base = ROOT / folder
        if not base.exists():
            continue
        for path in list(base.rglob("*.html")) + list(base.rglob("*.js")):
            rel = path.relative_to(ROOT).as_posix()
            if backupish.search(rel):
                continue
            try:
                src = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
            src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
            for m in re.finditer(r"\.from\(\s*[`\"\']([a-z_][a-z0-9_]*)[`\"\']\s*\)", src):
                found.append((rel, m.group(1)))
    # the root index.html is not inside any folder above
    root_index = ROOT / "index.html"
    if root_index.exists():
        src = root_index.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\.from\(\s*[`\"\']([a-z_][a-z0-9_]*)[`\"\']\s*\)", src):
            found.append(("index.html", m.group(1)))
    return len(found), found


def browser_db_budget_checks() -> list:
    """The count of direct database calls in browser files may only go down.

    Decision 2026-09-17: the UI talks to the backend and nothing else. Getting there is a
    staged job (see docs/MIGRATION_TO_BACKEND.md), so the gate does not demand zero today - it
    demands that nobody adds one. Lower DB_CALL_BUDGET as the stages land.
    """
    count, found = browser_db_calls()
    if count > DB_CALL_BUDGET:
        extra = count - DB_CALL_BUDGET
        sample = ", ".join("%s -> %s" % f for f in found[:3])
        return ["%d new direct database call(s) in browser files (%d, budget %d). The UI "
                "talks to the backend: add an endpoint instead. Examples: %s"
                % (extra, count, DB_CALL_BUDGET, sample)]
    return []


def client_secrets_checks() -> list:
    """Nothing the browser holds is hidden, so nothing worth hiding may be in it.

    2026-09-17: the lesson-review page carried the five admin email addresses in plain
    source. It protected nothing - the backend checks ADMIN_EMAILS on every route and
    answers 403 - but it handed anyone a list of the accounts worth phishing.
    """
    bad = []
    for folder in BROWSER_FILES:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in list(base.rglob("*.html")) + list(base.rglob("*.js")):
            rel = path.relative_to(ROOT).as_posix()
            if re.search(r"(^|/)(index2|.*_back_?up|.*_v\d+|.*_old)\.", rel):
                continue
            try:
                src = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
            src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
            if re.search(r"ALLOWED_ADMIN_EMAILS\s*=\s*\[", src):
                bad.append("%s hard-codes an admin email allowlist; let the backend "
                           "answer 403 instead of publishing who the admins are" % rel)
            if re.search(r"\bsk-(or-v1-|proj-)?[A-Za-z0-9]{20}", src):
                bad.append("%s contains what looks like a secret API key" % rel)
            if "service_role" in src:
                bad.append("%s mentions service_role - that key must never be in a page" % rel)
    return bad


def migration_rollback_checks() -> list:
    """Every migration ships with the file that undoes it.

    2026-09-17: asked for after the answer-key migration. A migration that cannot be
    undone in one paste is a migration nobody dares run at three in the morning.
    """
    folder = ROOT / "supabase" / "migrations"
    if not folder.exists():
        return []
    bad = []
    for path in sorted(folder.glob("*.sql")):
        name = path.name
        if "rollback" in name or name == "APPLY_NOW.sql":
            continue
        mate = folder / (name[:-4] + "_rollback.sql")
        if not mate.exists():
            bad.append("supabase/migrations/%s has no %s - write the undo in the same "
                       "commit as the change" % (name, mate.name))
            continue
        body = mate.read_text(encoding="utf-8", errors="replace")
        live = [l.strip() for l in body.splitlines()
                if l.strip() and not l.strip().startswith("--")]
        if not live:
            bad.append("%s has no runnable statement - an empty rollback is not a rollback"
                       % mate.name)
    return bad


def answer_key_checks(main_src: str) -> list:
    """The correct answer is for the teacher. It must not reach the browser.

    2026-09-17: question.answer was added so the coach stops inventing the answer it
    grades the child against. The unit-lesson route returns the structured lesson
    verbatim, so without stripping, any child with the network tab open could read the
    answer before answering. Silencing the console protects nothing here - a page that
    holds the data can always be made to show it. What is not sent cannot be read.
    """
    bad = []

    if "def public_structured_lesson" not in main_src:
        bad.append("public_structured_lesson is gone - the answer key would be returned "
                   "to the browser with the lesson")

    # every place that hands a structured lesson to a client must go through it
    for marker in ('"structured_lesson":\n                public_structured_lesson(',
                   '"structured_lesson":\n                public_structured_lesson('):
        pass
    returns = main_src.count('"structured_lesson":')
    stripped = main_src.count("public_structured_lesson(")
    if returns and stripped < 2:
        bad.append("a route returns structured_lesson without public_structured_lesson(); "
                   "the answer key would travel to the browser")

    # no browser file may pull the whole lesson row or the generated JSON
    for folder in BROWSER_FILES:
        base = ROOT / folder
        if not base.exists():
            continue
        for path in list(base.rglob("*.html")) + list(base.rglob("*.js")):
            try:
                src = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rel = path.relative_to(ROOT).as_posix()
            # comments explain the rule and must not trip it
            src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
            src = re.sub(r"<!--.*?-->", "", src, flags=re.S)
            src = re.sub(r"^\s*//[^\n]*", "", src, flags=re.M)
            if "generated_lesson_json" in src:
                bad.append("%s reads generated_lesson_json in the browser - that JSON "
                           "carries the answer of every question" % rel)
            if 'from("lesson_units_content")' in src and 'select("*")' in src:
                idx = src.find('from("lesson_units_content")')
                if 0 <= idx and 'select("*")' in src[idx:idx + 400]:
                    bad.append("%s selects * from lesson_units_content in the browser; "
                               "that pulls the answer key with it" % rel)
    return bad


def lesson_closing_checks(main_src: str) -> list:
    """A lesson must end with something said to the child, and be marked as finished.

    2026-09-17: a lesson ended with a 20 s video identical for every lesson and child,
    then a card with three numbers. Nothing ever told the child what they had learned,
    and kid_lesson_progress stayed "in_progress" with no completed_at, xp_earned or
    stars_earned - the very columns the child's and the parent's dashboards read, which
    is why those tiles showed zero for every unit lesson.
    """
    bad = []
    if "/api/tutor/unit-lesson/closing" not in main_src:
        bad.append("the lesson closing route is gone - a lesson would end with a generic "
                   "video and no summary of what the child learned")
    if "class LessonClosingResponse" not in main_src:
        bad.append("LessonClosingResponse is gone - the closing has no shape")
    if "find_cached_lesson_closing" not in main_src:
        bad.append("the closing is no longer cached - re-entering a finished lesson would "
                   "pay for a new model call every time")
    if '"completed_at": now_iso' not in main_src or '"xp_earned": lesson_xp_reward' not in main_src:
        bad.append("a finished unit lesson no longer writes completed_at / xp_earned / "
                   "stars_earned, so the child's and the parent's dashboards go back to zero")
    return bad


def learning_coach_checks(main_src: str) -> list:
    """The coach must get the real answer and the real round limit.

    2026-09-17, two defects found together on lessons 151-153:
      * RUNTIME_DATA.lesson.correct_answer was the literal string "Derive from the
        lesson explanation and lesson goal", so gpt-4o-mini judged the child's answer
        against an answer it invented. It marked the complete answer "המורה, ארנב,
        תלמידה" as partial and sent the child to look for a word she had said.
      * coach_state.maximum_rounds was the constant 5 while the server ended the
        session after 1-4 rounds, so the model's "last round" never arrived and the
        rule "on the last round explain the correct answer" never fired.
    """
    bad = []
    if '"answer": answer' not in main_src:
        bad.append("direct_lesson_part no longer stores the question's answer "
                   "(question dict must be {text, answer}) - the coach would judge "
                   "the child against an answer it invents")
    if "class UniversalLessonResponse" in main_src:
        block = main_src.split("class UniversalLessonResponse", 1)[1][:400]
        fields = [l.strip() for l in block.splitlines() if l.strip() and not l.strip().startswith("#")]
        if not any(f.startswith("answer:") for f in fields):
            bad.append("UniversalLessonResponse has no `answer` field - the teacher "
                       "would write a question with no correct answer")
    if "def learning_coach_round_plan" not in main_src:
        bad.append("learning_coach_round_plan is gone - the round limit the model is "
                   "told and the one the server enforces can drift apart again")
    if '"maximum_rounds":\n                LEARNING_COACH_MAX_ROUNDS' in main_src:
        bad.append("the coach is told the constant LEARNING_COACH_MAX_ROUNDS again; "
                   "it must receive the enforced limit from learning_coach_round_plan")
    if main_src.count("get_learning_coach_round_limit(understanding_score)"):
        bad.append("the round limit is computed from the NEW score in run_learning_coach; "
                   "it must come from learning_coach_round_plan so the model and the "
                   "server agree on which round is the last")
    if '"is_final_round"' not in main_src:
        bad.append("coach_state no longer carries is_final_round - the prompt cannot "
                   "know when to give the answer and stop asking")
    return bad


def code_rule_checks(main_src: str) -> list:
    """Rules that live in main.py rather than in a prompt file (inline prompts, prefixes)."""
    fails = []
    rules = [
        ("hebrew_gender_rule(", 5, "gender rule must be applied by tutor chat, lesson dialogue, homework coach, homework turn and curriculum builder"),
        ("ABSOLUTELY NO WRITTEN TEXT IN THE IMAGE", 1, "reference-image prompt lost its no-text rule"),
        ("READING DIRECTION", 1, "reference-image prompt lost the right-to-left rule"),
        ("Some words carry nikud", 1, "TTS_STYLE_PREFIX lost the nikud instruction"),
        ("Words written in Latin letters are English", 1, "TTS_STYLE_PREFIX lost the Latin-words instruction"),
        ("- no written text", 2, "hero image prompt builder lost its no-text rule"),
        ("warn_if_gendered_lesson_text(", 2, "shared-lesson gender check is no longer called for explanation and question"),
        ("ensure_no_text_in_image(", 2, "image text check is no longer applied to visuals and hero"),
        ("lq.normalize_for_tts(", 2, "TTS normalisation is no longer applied (worker + live route)"),
        ("build_curriculum_builder_prompt(", 2, "curriculum builder prompt is not rendered through its builder"),
        ("lq.sanitize_generation_prompt(final_generation_prompt)", 1, "visual generation prompts are no longer sanitized (labels/captions requests)"),
        ("lq.second_person_nikud(", 1, "gender-aware nikud is not applied: the voice will read בשבילך/הצלחת in masculine to a girl"),
        ("hebrew_child_prompt_block(", 4, "the Hebrew gender + correctness block is missing from a child-facing prompt"),
        ("tts_cache_key(text, _gender)", 1, "the TTS cache key ignores gender: a girl would get the boy's recording"),
        ("vocalize_for_tts, text, _gender, _child_name", 1, "the live voice no longer gets the child's name: it will mispronounce it"),
        ("def vocalize_name(", 1, "child-name pronunciation was removed"),
        ("do not render the lesson title", 1, "hero prompt lost its strict no-text block"),
    ]
    for needle, min_count, why in rules:
        n = main_src.count(needle)
        if n < min_count:
            fails.append(f"main.py: {why} (found {n}, need >= {min_count} of {needle!r})")
    return fails


def pure_function_tests() -> list:
    """Free unit tests of lesson_quality (no network). A regression here breaks every lesson."""
    sys.path.insert(0, str(ROOT / "backend-ai-tutor-he"))
    try:
        import lesson_quality as lq
    except Exception as e:
        return [f"lesson_quality import failed: {e!r}"]
    bad = []
    def expect(cond, msg):
        if not cond: bad.append("lesson_quality: " + msg)
    n = lq.normalize_for_tts
    expect("📚" not in n("📚 שיעור"), "emoji not removed")
    expect("←" not in n("שמש ← עשב") and "שמש" in n("שמש ← עשב"), "arrow not replaced")
    expect("כפול" in n("5 × 3") and "חלקי" in n("10 ÷ 2"), "math symbols not spelled out")
    expect("קילומטר" in n('3 ק"מ'), "unit ק\"מ not expanded")
    expect("חצי" in n("1/2 מהכיתה") and "שלושת רבעי" in n("3/4"), "fractions not spelled out")
    expect(all(len(c) <= 350 for c in lq.split_for_tts("משפט. " * 200)), "split_for_tts chunk too long")
    expect(lq.question_segment_problem("הסבירו את המסלול.") == "directive_to_student", "directive not caught")
    expect(lq.question_segment_problem("מה קורה כשהחגב נעלם?") in ("ends_with_question_mark", "directive_to_student"), "short question not caught")
    expect(lq.question_segment_problem("הזחל גדל, נכון?") == "ends_with_question_mark", "short trailing question not caught")
    expect(lq.question_segment_problem("לכן, כדי לחקור שינוי סביבתי, שואלים: מה השתנה תחילה, על אילו גורמים השינוי השפיע, ואילו השפעות נוספות נוצרו בעקבותיו?") is None, "rhetorical question wrongly rejected")
    expect(lq.question_segment_problem("הצמח קיבל אנרגיה מהשמש.") is None, "plain sentence rejected")
    expect(lq.display_first_name("Alison Damaris Alvarenga Guerra") == "Alison" and lq.display_first_name("נועה") == "נועה", "display_first_name")
    sg = lq.sanitize_generation_prompt("A clearly labeled diagram with captions and a title: food chain.")
    expect(lq.is_allowed_scientific_text("CO2") and lq.is_allowed_scientific_text("H2O → O2") and not lq.is_allowed_scientific_text("Growth Thinking") and not lq.is_allowed_scientific_text("Food, Decomposition") and lq.is_allowed_scientific_text("sin x + cos y = 1") and lq.is_allowed_scientific_text("√2 · π"), "is_allowed_scientific_text")
    sp = lq.second_person_nikud
    expect("\u05d1\u05b4\u05bc\u05e9\u05c1\u05b0\u05d1\u05b4\u05d9\u05dc\u05b5\u05da\u05b0" in sp("אני כאן בשבילך", "female"), "second_person_nikud feminine בשבילך")
    expect("\u05d1\u05b4\u05bc\u05e9\u05c1\u05b0\u05d1\u05b4\u05d9\u05dc\u05b0\u05da\u05b8" in sp("אני כאן בשבילך", "male"), "second_person_nikud masculine בשבילך")
    expect(sp("אני כאן בשבילך", "unknown") == "אני כאן בשבילך", "second_person_nikud unknown gender untouched")
    expect(sp("כל הכבוד, הצלחת!", "female") != sp("כל הכבוד, הצלחת!", "male"), "past tense must differ by gender")
    expect(lq.has_second_person("ראית את התשובה שלך") and not lq.has_second_person("הצמח גדל במדבר"), "has_second_person")
    ents = [{"order": i + 1, "generation_prompt": t} for i, t in enumerate(["puddle plants insects", "puddle plants insects organisms", "plant roots soil water", "plant roots soil drying", "thermometer light animals", "roots anchor soil erosion"])]
    out = lq.enforce_image_budget(ents, 0.5, 3, [False] * 6)
    expect(out[0]["reuse_of"] is None and sum(1 for e in out if not e.get("reuse_of")) == 3 and all((e.get("reuse_of") or 0) < e["order"] for e in out), "enforce_image_budget")
    body = sg.split("No written text")[0].lower()
    expect("labeled" not in body and "caption" not in body and "title" not in body and "No written text" in sg, "sanitize_generation_prompt")
    e, w, st = lq.text_checks({"parts": [{"part_number": 1, "lesson": [{"text": "נסי לחשוב מה אתה רואה."}], "question": {"text": "הסבירו."}}]})
    expect(any("gendered" in x for x in e), "gendered 2nd person in shared lesson not caught")
    e, w, st = lq.visual_plan_checks({"parts": [{"part_number": 1, "lesson": [{"text": "א"}, {"text": "ב"}], "question": {"text": "ג"}}]},
                                     {"parts": [{"visuals": [{"part_number": 1, "order": 1, "trigger_text": "א"}]}]})
    expect(any("visuals for" in x for x in e), "visual count mismatch not caught")
    return bad


ENV_KEYS = ("OPENAI_API_KEY", "GEMINI_API_KEY", "SUPABASE_SERVICE_ROLE_KEY", "OPENROUTER_API_KEY")


def env_file_checks() -> list:
    """
    The env file a DEPLOY will use must hold usable keys. 2026-09-17: an append to
    .env.prod with no trailing newline glued a second variable onto the end of
    GEMINI_API_KEY. The service started, text and voice worked, and every image of
    the lesson died inside the SDK ("ascii codec can't encode character") — a whole
    lesson was generated with no pictures. Catch that in the file, before the restart.
    Not part of the commit gate: a commit must not depend on the health of a secrets
    file that is not in git.
    """
    name = ".env.%s" % os.environ.get("APP_ENV", "prod")
    path = ROOT / "backend-ai-tutor-he" / name
    if not path.exists():
        return []
    bad = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() not in ENV_KEYS:
            continue
        v = value.strip()
        if not v:
            bad.append("%s: %s is empty" % (name, key))
        elif not v.isascii():
            bad.append("%s: %s has non-ASCII characters (length %d) - the value is corrupted, "
                       "most likely a line appended to a file with no trailing newline" % (name, key, len(v)))
        elif "_KEY=" in v or "_URL=" in v:
            bad.append("%s: %s has another variable glued into its value (length %d) - "
                       "the file is missing a newline" % (name, key, len(v)))
    return bad


def learning_coach_round_tests() -> list:
    """The adaptive limit must stay monotonic and must never reach zero rounds."""
    code = r'''
import os, sys, io, contextlib
os.chdir("backend-ai-tutor-he"); sys.path.insert(0, ".")
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import main
bad = []
f = main.get_learning_coach_round_limit
for score in range(0, 101):
    if f(score) < 1:
        bad.append("round limit %d for score %d - a child would get no turn" % (f(score), score))
        break
for lo, hi in ((0, 39), (40, 69), (70, 89), (90, 100)):
    if f(lo) != f(hi):
        bad.append("round limit not constant inside band %d-%d" % (lo, hi))
if not (f(0) >= f(50) >= f(80) >= f(95)):
    bad.append("round limit must not grow with the score")
plan = main.learning_coach_round_plan
r, limit, final = plan({"total_rounds": 0, "final_understanding_score": 0})
if r != 1 or final:
    bad.append("round 1 of a fresh session must not be the final round (got %s, %s)" % (r, final))
r, limit, final = plan({"total_rounds": limit - 1, "final_understanding_score": 0})
if not final:
    bad.append("the last allowed round must report is_final_round=True")
r, limit, final = plan({"total_rounds": 0, "final_understanding_score": 95})
if not final:
    bad.append("a child already at mastery must close on the first round")
print("\n".join(bad) if bad else "COACH_OK")
'''
    r = subprocess.run([str(PY), "-c", code], cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, APP_ENV=os.environ.get("APP_ENV", "prod"),
                                **{k: "gate-dummy-key" for k in ENV_KEYS}), timeout=180)
    if r.returncode != 0:
        return ["learning coach round tests crashed: %s" % (r.stderr or r.stdout)[-400:]]
    lines = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    if lines and lines[-1].endswith("COACH_OK"):
        return []
    return ["learning coach rounds: " + l for l in lines if not l.endswith("COACH_OK")]


def render_smoke() -> list:
    """
    Render every builder with sample data. The keys passed in are dummies on purpose:
    this checks prompts, not secrets. main.py keeps env vars that are already set and
    only falls back to the env file, so a commit never depends on a real key.
    """
    code = r'''
import os, re, sys, io, contextlib
os.chdir("backend-ai-tutor-he"); sys.path.insert(0, ".")
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import main
PH = re.compile(r"\{[a-z_]+\}")
child = {"id": "k", "child_name": "נועה", "age": 5, "gender": "female", "avatar_key": "cat",
         "learning_interests": ["חיות"], "usage_goals": ["מדעים"]}
unit = {"id": 1, "unit_name": "יחידה", "lesson_name": "שיעור", "learning_objective": "מטרה",
        "lesson_complexity": 3, "max_duration_seconds": 150, "lesson_parts_count": 2}
parent = {"id": 9, "grade": 5, "subject": "מדעים", "lesson_name": "נושא"}
out = {}
with contextlib.redirect_stdout(buf):
    out["universal"] = main.build_universal_unit_lesson_prompt(unit_lesson=unit, parent_lesson=parent)
    out["expansion"] = main.build_lesson_expansion_prompt(unit_lesson=unit, parent_lesson=parent, part_number=2,
                        previous_parts=[{"part_number": 1, "explanation": "x", "question": "y"}])
    out["director"] = main.build_lesson_director_prompt(lesson_text="הסבר לדוגמה.")
    out["tutor"] = main.build_tutor_prompt(child, "")
    out["lesson"] = main.build_structured_lesson_prompt(child, {"id": 1, "lesson_name": "x"}, {}, "lesson")
    out["curriculum"] = main.build_curriculum_builder_prompt(child, {"id": "s", "subject_name": "שחמט", "status": "draft"},
                        {"subject": "שחמט"}, [{"role": "user", "content": "רוצה שחמט"}])
bad = []
for k, v in out.items():
    left = sorted(set(PH.findall(v)))
    if left: bad.append(f"{k}: unresolved placeholders {left}")
    if k == "director" and "הסבר לדוגמה." not in v: bad.append("director: lesson_text was not injected")
    if k == "lesson" and "ADDRESSING THE CHILD" not in v: bad.append("lesson: gender instruction missing in rendered prompt")
    if k == "curriculum" and "נועה" not in v: bad.append("curriculum: child_name not injected")
print("\n".join(bad) if bad else "RENDER_OK")
'''
    env = dict(os.environ, APP_ENV=os.environ.get("APP_ENV", "prod"))
    for k in ENV_KEYS:
        env[k] = "gate-dummy-key"
    env["SUPABASE_URL"] = env.get("SUPABASE_URL") or "https://gate.supabase.co"
    r = subprocess.run([str(PY), "-c", code], cwd=ROOT, capture_output=True, text=True, env=env, timeout=180)
    if r.returncode != 0:
        return [f"render smoke crashed: {(r.stderr or r.stdout)[-400:]}"]
    # main.py's print prefix (media_trace) may precede our markers: match by suffix
    lines = [l.strip() for l in r.stdout.strip().splitlines() if l.strip()]
    if lines and lines[-1].endswith("RENDER_OK"):
        return []
    return ["render smoke: " + l for l in lines if not l.endswith("RENDER_OK")]


def changed_prompts(staged: bool) -> list:
    args = ["git", "diff", "--cached", "--name-only"] if staged else ["git", "diff", "--name-only", "HEAD"]
    names = sh(*args).split()
    out = []
    for n in names:
        if not (n.startswith("backend-ai-tutor-he/prompts/") and n.endswith(".txt")):
            continue
        if not (PROMPTS / Path(n).name).exists():
            # deleted on purpose; coverage_checks fails if main.py still loads it
            print(f"note: {Path(n).name} was deleted (coverage check decides if that is allowed)")
            continue
        out.append(Path(n).name)
    return out


def head_version(name: str) -> str | None:
    out = subprocess.run(["git", "show", f"HEAD:backend-ai-tutor-he/prompts/{name}"], cwd=ROOT,
                         capture_output=True, text=True)
    return out.stdout if out.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--staged", action="store_true")
    ap.add_argument("--hook", action="store_true", help="Claude Code PostToolUse: read tool_input from stdin")
    ap.add_argument("--pre-edit", action="store_true", help="Claude Code PreToolUse: auto-backup before a prompt edit")
    ap.add_argument("--pre-bash", action="store_true",
                    help="Claude Code PreToolUse on Bash: block a tutor service restart/deploy unless the gate passes")
    ap.add_argument("--fast", action="store_true", help="skip the render smoke (no main import)")
    ap.add_argument("--check-file"); ap.add_argument("--as", dest="as_name")
    a = ap.parse_args()
    main_src = MAIN.read_text(encoding="utf-8")

    if a.pre_bash:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        cmd = str((payload.get("tool_input") or {}).get("command") or "")
        deploy = re.search(r"systemctl\s+(restart|start|reload|reload-or-restart)\s+[^\n;&|]*iakids-tutor", cmd) \
            or re.search(r"tools/deploy_tutor\.sh", cmd)
        if not deploy or "tools/deploy_tutor.sh" in cmd:
            return 0          # not a deploy, or the deploy script (it runs the gate itself)
        fails = []
        for name in live_prompt_names():
            fails += check_file(PROMPTS / name, name, main_src, None, verbose=False)
        fails += render_smoke()
        if fails:
            print("DEPLOY BLOCKED — prompt/import gate failed:\n - " + "\n - ".join(fails)
                  + "\nFix it, or deploy with `bash tools/deploy_tutor.sh` (which runs the same gate).", file=sys.stderr)
            return 2
        print("deploy gate: prompts + import smoke OK, restart allowed")
        return 0

    if a.pre_edit or a.hook:
        try:
            payload = json.load(sys.stdin)
        except Exception:
            payload = {}
        fp = str((payload.get("tool_input") or {}).get("file_path") or "")
        if "/backend-ai-tutor-he/prompts/" not in fp.replace("\\", "/") or not fp.endswith(".txt"):
            return 0                                             # not a prompt: nothing to do
        name = Path(fp).name
        if a.pre_edit:
            # auto-backup: only if no backup already holds the current content
            cur = Path(fp).read_text(encoding="utf-8") if Path(fp).exists() else None
            for b in sorted(ROOT.glob("V*_BACKUP"), key=lambda p: int(re.sub(r"\D", "", p.name) or 0), reverse=True):
                c = b / "backend-ai-tutor-he" / "prompts" / name
                if cur is not None and c.exists() and c.read_text(encoding="utf-8") == cur:
                    print(f"prompt gate: {name} already backed up in {b.name}")
                    return 0
            r = subprocess.run(["bash", ".claude/skills/backup/backup.sh", f"auto: before editing {name}"],
                               cwd=ROOT, capture_output=True, text=True)
            print("prompt gate auto-backup:", (r.stdout or r.stderr).strip()[-200:])
            return 0
        fails = check_file(Path(fp), name, main_src, head_version(name))
        if not a.fast:
            fails += render_smoke()
        if fails:
            print("PROMPT GATE FAILED for " + name + ":\n - " + "\n - ".join(fails), file=sys.stderr)
            return 2
        print(f"prompt gate: {name} OK")
        return 0

    if a.check_file:
        fails = check_file(Path(a.check_file), a.as_name or Path(a.check_file).name, main_src, None)
        print("\n".join(fails) if fails else "OK")
        return 1 if fails else 0

    names = live_prompt_names() if a.all else changed_prompts(a.staged)
    changed_files = sh("git", "diff", "--cached" if a.staged else "HEAD", "--name-only").split()
    main_changed = "backend-ai-tutor-he/main.py" in changed_files
    workspace_changed = "he/workspace/index.html" in changed_files
    if not names and not main_changed and not workspace_changed:
        print("prompt gate: no prompt, main.py or workspace changes")
        return 0
    if not names and (main_changed or workspace_changed):
        # No prompt changed, but the code that carries the rules did. Run the rules that
        # live in code (the lesson screen, the coach handover, the media failure signal)
        # plus, for main.py, the render smoke that doubles as an import smoke — a route
        # decorator on the wrong function took prod down for 4 minutes on 2026-09-15.
        cf = (learning_coach_checks(main_src) + media_failure_checks(main_src) + workspace_checks()
              + lesson_closing_checks(main_src) + completion_screen_checks() + log_mode_checks()
          + answer_key_checks(main_src) + migration_rollback_checks()
          + client_secrets_checks() + browser_db_budget_checks())
        print(("FAIL " if cf else "ok   ") + "code rules (lesson screen, coach handover, media failures)")
        rf = [] if (a.fast or not main_changed) else render_smoke()
        if main_changed:
            print(("FAIL " if rf else "ok   ") + "render/import smoke for main.py")
        if cf or rf:
            print("\nPROMPT GATE FAILED:\n - " + "\n - ".join(cf + rf), file=sys.stderr)
            return 1
        print("\nPROMPT GATE PASSED")
        return 0
    all_fails = []
    if a.all:
        print("coverage: %d prompt files loaded by main.py, %d with gate rules" % (
            len(set(re.findall(r'"prompts/([A-Za-z0-9_\-]+\.txt)"', main_src))), len(REQUIRED)))
    for name in names:
        fails = check_file(PROMPTS / name, name, main_src, head_version(name))
        print(("FAIL " if fails else "ok   ") + name)
        all_fails += fails
    pf = (pure_function_tests() + persona_checks(main_src) + coverage_checks(main_src)
          + code_rule_checks(main_src) + child_prompt_gender_checks(main_src) + prompt_usage_checks(main_src)
          + learning_coach_checks(main_src) + media_failure_checks(main_src) + workspace_checks()
          + lesson_closing_checks(main_src) + completion_screen_checks() + log_mode_checks()
          + answer_key_checks(main_src) + migration_rollback_checks()
          + client_secrets_checks() + browser_db_budget_checks())
    print(("FAIL " if pf else "ok   ") + "lesson_quality unit tests (TTS normaliser, validators)")
    all_fails += pf
    if not a.fast:
        rf = render_smoke()
        print(("FAIL " if rf else "ok   ") + "render smoke (all builders, no unresolved placeholders)")
        all_fails += rf
        cr = learning_coach_round_tests()
        print(("FAIL " if cr else "ok   ") + "learning coach rounds (limit, final round, answer handover)")
        all_fails += cr
    if a.all:
        ef = env_file_checks()
        print(("FAIL " if ef else "ok   ") + "env file keys (present, clean ASCII, no glued variable)")
        all_fails += ef
    if all_fails:
        print("\nPROMPT GATE FAILED:\n - " + "\n - ".join(all_fails), file=sys.stderr)
        return 1
    print("\nPROMPT GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
