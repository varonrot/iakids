#!/usr/bin/env python3
"""Static gate for the frontend side of the 2026-09-26 security review.

    python3 tools/security_gate_frontend.py              # run the checks
    python3 tools/security_gate_frontend.py --self-test  # negative tests on scratch copies

`checks(root=None)` returns a list of failure messages (empty = pass). Every rule pins
one sink the review closed: a database or profile value that reached innerHTML, a
redirect or fetch that trusted a URL, sign-in tokens taken from the address bar, an
unpinned third-party script, a log that printed a token or a child id. The pages are
plain static HTML, so the rules read the source; `root` lets the self-test run the
same rules on a scratch copy with one bug put back.
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRATCH = Path("/tmp/claude-0/-opt-iakids/8abfa422-981e-41ae-9fc8-134796ea412a/scratchpad")
TAG = "(2026-09-26 security review)"

SUPABASE_PIN = "@supabase/supabase-js@2.117.2/dist/umd/supabase.js"
CHART_PIN = "chart.js@4.5.1/dist/chart.umd.min.js"
PROJECT_ORIGIN = "https://bxnfzuglfwytiyaguwjj.supabase.co"

LOG_FIRST_PAGES = [
    "he/games/index.html", "he/games/progress/index.html", "games/progress/index.html",
    "he/lesson/index.html", "workspace/index.html", "frontend-v2/index.html",
    "he/onboarding/index.html", "he/onboarding/complete/index.html",
    "he/onboarding/cuenta/index.html", "he/onboarding/intereses/index.html",
    "he/onboarding/perfil/index.html", "he/onboarding/preferencias/index.html",
    "he/onboarding/prepare-user/index.html",
]

PREPARE_USER_PAGES = [
    "he/onboarding/prepare-user/index.html", "he/onboarding/prepare-user/index2.html",
    "he/games-onboarding/prepare-user/index.html", "onboarding/prepare-user/index.html",
    "pt/onboarding/prepare-user/index.html",
]
CUENTA_PAGES = [
    "he/onboarding/cuenta/index.html", "he/onboarding/cuenta/index2.html",
    "he/games-onboarding/cuenta/index.html", "onboarding/cuenta/index.html",
    "pt/onboarding/cuenta/index.html",
]

SRI_PAGES = [
    "he/workspace/index.html", "he/parent-panel/index.html", "he/admin/index.html",
    "he/admin/lessons-review/index.html", "he/admin/questions-review/index.html",
    "he/iakids-admin-dashboard-he/index.html", "support/index.html",
    "support-dashboard/index.html", "admin/dashboard/index.html", "he/tasks/index.html",
    "he/my-lessons/index.html", "he/games/workspace/index.html", "he/add-subject/index.html",
    "frontend-v2/index.html", "frontend-v2/homework.html",
    "he/onboarding/cuenta/index.html", "he/onboarding/prepare-user/index.html",
    "he/onboarding/complete/index.html", "he/games-onboarding/cuenta/index.html",
    "he/games-onboarding/prepare-user/index.html", "he/games-onboarding/complete/index.html",
    "onboarding/cuenta/index.html", "onboarding/prepare-user/index.html",
    "pt/onboarding/cuenta/index.html", "pt/onboarding/prepare-user/index.html",
]

# Every file a rule reads (the self-test copies these).
FILES = sorted(set([
    "support/index.html", "support-dashboard/index.html",
    "he/workspace/lesson-completion-core.js", "he/workspace/index.html",
    "he/parent-panel/index.html", "he/iakids-admin-dashboard-he/index.html",
    "he/admin/questions-review/index.html", "he/admin/lessons-review/index.html",
    "games/game-sdk.js", "he/workspace/homework-remote-capture.js",
    "he/games/index.html", "he/index.html", "index.html", "pt/index.html",
    "games/champions/index.html", "he/lesson/index.html", "he/tasks/index.html",
    "admin/dashboard/index.html",
] + LOG_FIRST_PAGES + PREPARE_USER_PAGES + CUENTA_PAGES + SRI_PAGES))


# ------------------------------------------------------------------ helpers
def _read(root: Path, rel: str):
    p = root / rel
    return p.read_text(encoding="utf-8", errors="replace") if p.is_file() else None


def _func_body(src: str, name: str) -> str:
    """Text of `function name(...) { ... }` (naive brace match; enough for these pages)."""
    m = re.search(r"(?:async\s+)?function\s+%s\s*\(" % re.escape(name), src)
    if not m:
        m = re.search(r"\b%s\s*\([^)]*\)\s*\{" % re.escape(name), src)
    if not m:
        return ""
    i = src.find("{", m.end())
    depth = 0
    for j in range(i, min(len(src), i + 200000)):
        c = src[j]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return src[m.start():j + 1]
    return src[m.start():]


def _placeholders(text: str):
    """Every ${...} expression, nested ones included, as stripped strings."""
    out = []
    i = 0
    while True:
        i = text.find("${", i)
        if i < 0:
            return out
        depth, j = 0, i + 1
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(re.sub(r"\s+", " ", text[i + 2:j]).strip())
        i += 2


def _unescaped(text: str, safe_prefixes, safe_exact=()):
    """Placeholders that are neither wrapped in a safe function nor known-literal.
    A placeholder holding a nested template (a conditional) is skipped: its own
    placeholders are checked separately."""
    bad = []
    for expr in _placeholders(text):
        if "`" in expr:
            continue
        compact = expr.replace(" ", "")
        if compact in {e.replace(" ", "") for e in safe_exact}:
            continue
        if any(compact.startswith(p.replace(" ", "")) for p in safe_prefixes):
            continue
        bad.append(expr)
    return bad


def _missing(root, rel, fails):
    fails.append(f"{rel} is missing - the security rules for it cannot run {TAG}")


# ------------------------------------------------------------------ rules
def support_checks(root):
    fails = []
    rel = "support/index.html"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    for fn in ("renderTickets", "openTicket", "loadMessages", "statusPill"):
        body = _func_body(src, fn)
        if not body:
            fails.append(f"[FE-01] {rel}: {fn}() not found - a ticket subject or message could run as code in a parent's browser {TAG}")
            continue
        bad = _unescaped(body, ("escapeHtml(", "statusPill(", "safeClass("),
                         ("selected?.id===t.id?'active':''",))
        if bad:
            fails.append(f"[FE-01] {rel}: {fn}() puts {bad} into the page unescaped - a ticket subject, status or message can run script in the parent's support page {TAG}")
    if re.search(r'onclick\s*=\s*"openTicket\(', src):
        fails.append(f"[FE-01] {rel}: tickets open through an inline onclick built from the ticket id - a crafted id runs script {TAG}")
    if 'eq("user_id", session.user.id)' not in _func_body(src, "loadTickets"):
        fails.append(f"[FE-01] {rel}: the ticket list is not filtered to the signed-in parent - one family could see another family's support tickets if RLS slips {TAG}")
    return fails


def support_dashboard_checks(root):
    fails = []
    rel = "support-dashboard/index.html"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    body = _func_body(src, "pill")
    if "PILL_CLASSES.includes(" not in body or _unescaped(body, ("escapeHtml(",), ("cls",)):
        fails.append(f"[FE-02] {rel}: pill() puts the ticket status into the class/text unescaped - a parent's ticket can run script in the support agent's dashboard {TAG}")
    if re.search(r'<span class="pill">\$\{(?!escapeHtml\()', src):
        fails.append(f"[FE-02] {rel}: a ticket category or priority reaches innerHTML unescaped - a parent's ticket can run script in the support agent's dashboard {TAG}")
    return fails


def homework_card_checks(root):
    fails = []
    rel = "he/workspace/lesson-completion-core.js"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    body = _func_body(src, "renderHomeworkDetectionCard")
    bad = _unescaped(body, ("escapeHomeworkCardHtml(",))
    if not body or bad:
        fails.append(f"[FE-03] {rel}: the homework card shows {bad or 'its text'} unescaped - text read from a photo of homework can run script in the child's workspace {TAG}")
    if re.search(r"resolvedKid\s*:", src):
        fails.append(f"[FE-08] {rel}: a failed homework turn prints the whole child profile to the console {TAG}")
    return fails


WS_RAW = [r"\$\{\s*topicName\s*\}", r"\$\{\s*unit\.unit_name\s*\}", r"\$\{\s*lesson\.lesson_name\s*\}",
          r"\$\{\s*item\.category\s*\}", r"\$\{\s*subject\s*\}", r"^\s*\$\{\s*part\s*\}\s*$",
          r"\$\{\s*String\(\s*next\.lesson_name"]


def workspace_checks(root):
    fails = []
    rel = "he/workspace/index.html"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    body = _func_body(src, "renderLessonClosingCard")
    bad = _unescaped(body, ("escapeLessonSidebarHtml(", "line("), ("icon", "label"))
    if not body or bad:
        fails.append(f"[FE-04] {rel}: the lesson closing card shows {bad or 'the summary'} unescaped - the teacher's wrap-up text can run script on the child's screen {TAG}")
    lines = src.split("\n")
    for n, line in enumerate(lines):
        for pat in WS_RAW:
            if re.search(pat, line):
                window = "\n".join(lines[max(0, n - 6):n + 1])
                if "textContent" not in window:
                    fails.append(f"[FE-04] {rel}:{n + 1}: a curriculum/catalog name reaches the page as HTML - a subject, unit or lesson name with markup runs script in the child's workspace {TAG}")
    hero = _func_body(src, "showLessonHeroImage")
    guard = _func_body(src, "isSafeLessonImageUrl")
    if ("isSafeLessonImageUrl(" not in hero or 'src="${imageUrl}"' in hero
            or 'protocol === "https:"' not in guard):
        fails.append(f"[FE-04] {rel}: the lesson image src is not limited to https/same-site - a javascript: or foreign image URL reaches the child's lesson {TAG}")
    if not re.search(r'\.eq\("id", activeKidId\)\s*\.eq\("user_id", userId\)', src):
        fails.append(f"[FE-04] {rel}: the child profile is read by id alone - a stale or planted active_kid_id could open another family's child {TAG}")
    return fails


def parent_panel_checks(root):
    fails = []
    rel = "he/parent-panel/index.html"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    for pat in (r"\$\{lesson\?\.lesson_name", r"\$\{lesson\?\.subject", r">\$\{subject\}<",
                r">\$\{label\}<", r">\$\{text\}<"):
        if re.search(pat, src):
            fails.append(f"[FE-05] {rel}: a lesson name, subject or the teacher's parent note reaches the parent panel as HTML - it could run script in the parent's session {TAG}")
            break
    return fails


def admin_dashboard_checks(root):
    fails = []
    rel = "he/iakids-admin-dashboard-he/index.html"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    if re.search(r"<(td|h3|p|strong)>\$\{(?!esc\()", src) or re.search(r'class="avatar">\$\{(?!esc\()', src):
        fails.append(f"[FE-06] {rel}: a child's name or another DB value reaches the admin dashboard as HTML - a family could run script in the admin's session {TAG}")
    return fails


def link_checks(root):
    fails = []
    rel = "he/admin/questions-review/index.html"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
    else:
        guard = _func_body(src, "safeHttpUrl")
        if 'href="${esc(t.source_url)}"' in src or "safeHttpUrl(t.source_url)" not in src \
                or 'x.protocol === "https:"' not in guard:
            fails.append(f"[FE-07] {rel}: a question's source link is not limited to http(s) - a javascript: link runs in the reviewer's admin session {TAG}")
    # every target=_blank link carries rel=noopener, anywhere in the site
    for p in root.rglob("*"):
        if p.suffix not in (".html", ".js") or not p.is_file():
            continue
        parts = p.relative_to(root).parts
        if any(x in (".git", "node_modules") or "BACKUP" in x or "backup" in x.lower() for x in parts):
            continue
        s = p.read_text(encoding="utf-8", errors="replace")
        if "_blank" not in s:
            continue
        for m in re.finditer(r"<a\b[^>]*target\s*=\s*[\"']?_blank[^>]*>", s, re.S | re.I):
            if "noopener" not in m.group(0) and "noreferrer" not in m.group(0):
                line = s.count("\n", 0, m.start()) + 1
                fails.append(f"[FE-07] {p.relative_to(root)}:{line}: a new-tab link without rel=noopener - the opened page can redirect the family's tab to a phishing page {TAG}")
    return fails


def logging_checks(root):
    fails = []
    for rel in LOG_FIRST_PAGES:
        src = _read(root, rel)
        if src is None:
            continue
        at = src.find('<script src="/assets/js/iakids-log-mode.js"')
        if at < 0 or src.find("<script") != at:
            fails.append(f"[FE-08] {rel}: the log switch is not the first script - this page prints to the console in production {TAG}")
    for rel in ("he/games/index.html", "he/index.html", "index.html", "pt/index.html"):
        src = _read(root, rel)
        if src and re.search(r"console\.log\(\s*[\"']Supabase connected", src):
            fails.append(f"[FE-08] {rel}: the page prints the whole session (access and refresh token) to the console {TAG}")
    sdk = _read(root, "games/game-sdk.js")
    if sdk is None:
        _missing(root, "games/game-sdk.js", fails)
        return fails
    for m in re.finditer(r"console\.(log|info|warn|debug)\(", sdk):
        if re.search(r"\b(kidId|kid_id)\s*:", sdk[m.start():m.start() + 400].split(");")[0]):
            fails.append(f"[FE-08] games/game-sdk.js:{sdk.count(chr(10), 0, m.start()) + 1}: a game log prints the child's id {TAG}")
    if re.search(r"postMessage\(\s*msg\s*,\s*['\"]\*['\"]", sdk):
        fails.append(f"[FE-08] games/game-sdk.js: the game result is posted to any parent origin - a site that frames a game reads the child's results {TAG}")
    return fails


def sdk_checks(root):
    fails = []
    sdk = _read(root, "games/game-sdk.js")
    if sdk is None:
        return fails
    if "game_question_mark" in re.sub(r"//[^\n]*", "", sdk):
        fails.append(f"[FE-09] games/game-sdk.js: the SDK still calls game_question_mark - any account could skew the question counters every child's difficulty relies on {TAG}")
    if ("sameSite(new URLSearchParams(location.search).get('from'))" not in sdk
            or "u.origin === location.origin" not in sdk
            or re.search(r"if \(from && /\^", sdk)):
        fails.append(f"[FE-09] games/game-sdk.js: ?from= is not parsed as a same-origin URL - a game link can send the child to another site from the back button {TAG}")
    for m in re.finditer(r"esm\.sh/@supabase/supabase-js@([^'\"/]+)", sdk):
        if not re.fullmatch(r"\d+\.\d+\.\d+", m.group(1)):
            fails.append(f"[FE-12] games/game-sdk.js: the games load supabase-js@{m.group(1)} unpinned - a bad release would run in every child's game {TAG}")
    body = _func_body(sdk, "_paint")
    if re.search(r"\$\{\s*this\._user", body):
        fails.append(f"[FE-13] games/game-sdk.js: the account chip builds HTML from the Google name/photo {TAG}")
    return fails


def remote_capture_checks(root):
    fails = []
    rel = "he/workspace/homework-remote-capture.js"
    src = _read(root, rel)
    if src is None:
        _missing(root, rel, fails)
        return fails
    guard = src.find("isProjectStorageUrl(sess.signed_url)")
    fetch = src.find("fetch(sess.signed_url)")
    if guard < 0 or fetch < 0 or guard > fetch or f"PROJECT_STORAGE_ORIGIN='{PROJECT_ORIGIN}'" not in src:
        fails.append(f"[FE-10] {rel}: the phone-capture photo URL is fetched without checking it is our storage - a planted URL feeds any file into the child's homework {TAG}")
    return fails


def login_csrf_checks(root):
    fails = []
    for rel in PREPARE_USER_PAGES:
        src = _read(root, rel)
        if src is None:
            continue
        ok = ("detectSessionInUrl: false" in src
              and 'localStorage.getItem("iakids_auth_pending")' in src
              and 'localStorage.removeItem("iakids_auth_pending")' in src
              and re.search(r"if \(authIsFresh && access_token && refresh_token\) \{[^}]*setSession", src))
        if not ok or len(re.findall(r"setSession\(", src)) != 1:
            fails.append(f"[FE-11] {rel}: sign-in tokens in the address bar are accepted without a sign-in this browser started - a link can log a parent into an attacker's account {TAG}")
    for rel in CUENTA_PAGES:
        src = _read(root, rel)
        if src is None:
            continue
        flag = src.find('localStorage.setItem("iakids_auth_pending"')
        oauth = src.find("signInWithOAuth")
        if flag < 0 or oauth < 0 or flag > oauth:
            fails.append(f"[FE-11] {rel}: Google sign-in starts without marking this browser - the parent comes back to prepare-user and the login is refused {TAG}")
    return fails


def sri_checks(root):
    fails = []
    for rel in SRI_PAGES:
        src = _read(root, rel)
        if src is None:
            continue
        for m in re.finditer(r"<script\b[^>]*src=\"([^\"]*(?:supabase-js|/npm/chart\.js)[^\"]*)\"[^>]*>", src, re.S):
            tag, url = m.group(0), m.group(1)
            pinned = SUPABASE_PIN in url or CHART_PIN in url
            if not pinned or 'integrity="sha384-' not in tag or 'crossorigin="anonymous"' not in tag:
                fails.append(f"[FE-12] {rel}: {url} is loaded without an exact version and integrity hash - a compromised CDN release would run with the family's session {TAG}")
    return fails


def self_xss_checks(root):
    fails = []
    for rel in ("he/games/index.html", "he/index.html"):
        src = _read(root, rel)
        if src is None:
            continue
        body = _func_body(src, "updateNavbar")
        if "${displayName}" in body or 'src="${avatarUrl}"' in body or "safeAvatarUrl(" not in body:
            fails.append(f"[FE-13] {rel}: the menu builds HTML from the Google name/photo unescaped {TAG}")
    for rel in ("index.html", "pt/index.html"):
        src = _read(root, rel)
        if src and "const avatarUrl = user.user_metadata?.avatar_url || null" in src:
            fails.append(f"[FE-13] {rel}: the avatar src accepts any URL scheme, not only https {TAG}")
    src = _read(root, "games/champions/index.html")
    if src and re.search(r"\$\{\s*best\.player", src):
        fails.append(f"[FE-13] games/champions/index.html: the player name typed by a child is shown as HTML in the champions table {TAG}")
    src = _read(root, "he/lesson/index.html")
    if src:
        err = re.search(r"\$\{\s*error\.(message|code|details)", src)
        dbg_at = src.find('class="lesson-debug-card"')
        dbg = src[dbg_at:src.find("`;", dbg_at)] if dbg_at >= 0 else ""
        if err or _unescaped(_func_body(src, "showLessonError"), ("escapeLessonErrorHtml(",)) \
                or _unescaped(dbg, ("escapeLessonErrorHtml(",)):
            fails.append(f"[FE-13] he/lesson/index.html: the lesson page echoes the URL's lesson id/subject or a DB error as HTML - a crafted link runs script {TAG}")
    src = _read(root, "he/tasks/index.html")
    if src and (re.search(r'onclick="(complete|delete)Task\(', src)
                or re.search(r"(dot|task-icon) \$\{t\.task_type\}", src)):
        fails.append(f"[FE-13] he/tasks/index.html: a task's id or type is built into an inline handler/class - a crafted task runs script in the child's planner {TAG}")
    src = _read(root, "admin/dashboard/index.html")
    if src is not None:
        inline = re.findall(r"<script(?![^>]*\bsrc=)([^>]*)>", src)
        if 'name="robots" content="noindex"' not in src or any('type="text/plain"' not in a for a in inline):
            fails.append(f"[FE-14] admin/dashboard/index.html: the retired admin page is indexable or its script still runs {TAG}")
    return fails


RULES = [support_checks, support_dashboard_checks, homework_card_checks, workspace_checks,
         parent_panel_checks, admin_dashboard_checks, link_checks, logging_checks, sdk_checks,
         remote_capture_checks, login_csrf_checks, sri_checks, self_xss_checks]


def checks(root=None) -> list[str]:
    root = Path(root) if root else ROOT
    fails = []
    for rule in RULES:
        fails.extend(rule(root))
    return fails


# ------------------------------------------------------------------ self-test
# (file, text now in the file, the bug put back, rule id that must fail)
MUTATIONS = [
    ("support/index.html", "<div>${escapeHtml(t.subject)}</div>", "<div>${t.subject}</div>", "FE-01"),
    ("support/index.html", "${escapeHtml(m.message)}", "${m.message}", "FE-01"),
    ("support/index.html", 'data-id="${escapeHtml(t.id)}">', "data-id=\"${escapeHtml(t.id)}\" onclick=\"openTicket('${t.id}')\">", "FE-01"),
    ("support/index.html", '    .eq("user_id", session.user.id)\n', "", "FE-01"),
    ("support/index.html", '<span class="pill ${safeClass(status,STATUS_CLASSES)}">', '<span class="pill ${status}">', "FE-01"),
    ("support-dashboard/index.html", "${escapeHtml(status)}</span>", "${status}</span>", "FE-02"),
    ("support-dashboard/index.html", '<span class="pill">${escapeHtml(t.category)}</span>\n            ', '<span class="pill">${t.category}</span>\n            ', "FE-02"),
    ("he/workspace/lesson-completion-core.js", "${escapeHomeworkCardHtml(topic)}", "${topic}", "FE-03"),
    ("he/workspace/lesson-completion-core.js", 'console.error("HOMEWORK TURN: kid id missing");', 'console.error("HOMEWORK TURN: kid id missing", { resolvedKid: getHomeworkKidObject() });', "FE-08"),
    ("he/workspace/index.html", "${ escapeLessonSidebarHtml( text ) }", "${text}", "FE-04"),
    ("he/workspace/index.html", 'data-topic-name="${escapeLessonSidebarHtml(topicName)}"', 'data-topic-name="${topicName}"', "FE-04"),
    ("he/workspace/index.html", "${escapeLessonSidebarHtml(part)}", "${part}", "FE-04"),
    ("he/workspace/index.html", 'src="${escapeLessonSidebarHtml(imageUrl)}"', 'src="${imageUrl}"', "FE-04"),
    ("he/workspace/index.html", '  .eq("user_id", userId)\n  .single();', "  .single();", "FE-04"),
    ("he/parent-panel/index.html", '<div class="activity-text">${escapeHtml(text)}</div>', '<div class="activity-text">${text}</div>', "FE-05"),
    ("he/iakids-admin-dashboard-he/index.html", "<h3>${esc(u.child_name)}</h3>", "<h3>${u.child_name}</h3>", "FE-06"),
    ("he/admin/questions-review/index.html", 'href="${esc(safeHttpUrl(t.source_url))}"', 'href="${esc(t.source_url)}"', "FE-07"),
    ("he/admin/lessons-review/index.html", 'target="_blank" rel="noopener noreferrer"', 'target="_blank"', "FE-07"),
    ("he/games/index.html", '<script src="/assets/js/iakids-log-mode.js"></script>\n', "", "FE-08"),
    ("he/index.html", "  /* 26/09/2026 security review — never print the session: it holds the access token. */\n",
     '  supabaseClient.auth.getSession().then(({ data, error }) => { console.log("Supabase connected", data, error); });\n', "FE-08"),
    ("games/game-sdk.js", "          gameId:\n            this._gameId,", "          kidId:\n            this._kidId,\n\n          gameId:\n            this._gameId,", "FE-08"),
    ("games/game-sdk.js", "      msg,\n      location.origin\n", "      msg,\n      '*'\n", "FE-08"),
    ("games/game-sdk.js", "      // 26/09/2026 security review: no game_question_mark call.",
     "      c.rpc('game_question_mark', { p_game: cur.slug, p_key: cur.qkey, was_correct: !!correct });\n      // 26/09/2026 security review: no game_question_mark call.", "FE-09"),
    ("games/game-sdk.js", "const from = sameSite(new URLSearchParams(location.search).get('from'));",
     "const from = new URLSearchParams(location.search).get('from');", "FE-09"),
    ("games/game-sdk.js", "esm.sh/@supabase/supabase-js@2.117.2'", "esm.sh/@supabase/supabase-js@2'", "FE-12"),
    ("he/workspace/homework-remote-capture.js", "if(!isProjectStorageUrl(sess.signed_url))throw new Error('signed_url_not_project_storage');", "", "FE-10"),
    ("he/onboarding/prepare-user/index.html", "auth: { detectSessionInUrl: false }", "auth: {}", "FE-11"),
    ("pt/onboarding/prepare-user/index.html", "if (authIsFresh && access_token && refresh_token) {", "if (access_token && refresh_token) {", "FE-11"),
    ("he/onboarding/cuenta/index.html", 'try { localStorage.setItem("iakids_auth_pending", String(Date.now())); } catch (e) {}\n', "", "FE-11"),
    ("support/index.html", SUPABASE_PIN + '" integrity="sha384-', '@supabase/supabase-js@2" data-x="', "FE-12"),
    ("he/iakids-admin-dashboard-he/index.html", CHART_PIN, "chart.js", "FE-12"),
    ("games/game-sdk.js", "      name.textContent = this._user.name || this._user.email || '';",
     "      name.innerHTML = `${this._user.name}`;", "FE-13"),
    ("he/games/index.html", '${escapeNavHtml(displayName)}', "${displayName}", "FE-13"),
    ("index.html", "const avatarUrl = /^https:", "const avatarUrl = user.user_metadata?.avatar_url || null;\n    const _x = /^https:", "FE-13"),
    ("games/champions/index.html", "const cells = [GAME_NAMES[slug] || slug, best.player || 'אורח',",
     "tr.innerHTML = `<td>${best.player}</td>`; const cells = [GAME_NAMES[slug] || slug, best.player || 'אורח',", "FE-13"),
    ("he/lesson/index.html", "${escapeLessonErrorHtml(error.message || \"-\")}", "${error.message || \"-\"}", "FE-13"),
    ("he/tasks/index.html", 'data-action="delete"', "onclick=\"deleteTask('${t.id}')\"", "FE-13"),
    ("admin/dashboard/index.html", '<script type="text/plain" data-disabled="not-in-use">', "<script>", "FE-14"),
]


def self_test() -> int:
    base = checks()
    if base:
        print("security_gate_frontend: the real tree already fails, fix that first:")
        for f in base:
            print("  -", f)
        return 1
    SCRATCH.mkdir(parents=True, exist_ok=True)
    failures = 0
    tmp = Path(tempfile.mkdtemp(prefix="fe_gate_", dir=SCRATCH))
    try:
        for f in FILES:
            src = ROOT / f
            if src.is_file():
                (tmp / f).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, tmp / f)
        if checks(tmp):
            print("FAIL  the scratch copy fails before any mutation")
            return 1
        for rel, now, bug, rule in MUTATIONS:
            original = (tmp / rel).read_text(encoding="utf-8")
            if now not in original:
                print(f"FAIL  {rule} {rel}: mutation anchor not found: {now[:60]!r}")
                failures += 1
                continue
            (tmp / rel).write_text(original.replace(now, bug, 1), encoding="utf-8")
            try:
                got = [f for f in checks(tmp) if f"[{rule}]" in f]
            finally:
                (tmp / rel).write_text(original, encoding="utf-8")
            if got:
                print(f"ok    {rule} {rel}: bug caught -> {got[0][:110]}")
            else:
                print(f"FAIL  {rule} {rel}: bug NOT caught ({bug[:60]!r})")
                failures += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"{len(MUTATIONS) - failures}/{len(MUTATIONS)} negative tests caught")
    return 1 if failures else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    problems = checks()
    for p in problems:
        print("-", p)
    print("security_gate_frontend:", "FAIL" if problems else "PASS")
    sys.exit(1 if problems else 0)
