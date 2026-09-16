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
        "sections": ["RUNTIME_CONTEXT", "ADDRESSING THE CHILD", "Always communicate with the child in Hebrew"],
    },
    "iakids_universal_unit_lesson_prompt.txt": {
        "placeholders": ["{grade}", "{subject}", "{parent_lesson}", "{lesson_name}", "{learning_objective}",
                         "{lesson_complexity}", "{max_duration_seconds}"],
        "sections": ["השיעור משותף לכל הילדים"],
    },
    "iakids_lesson_expansion_prompt.txt": {
        "placeholders": ["{grade}", "{subject}", "{parent_lesson}", "{lesson_name}", "{learning_objective}",
                         "{lesson_complexity}", "{max_duration_seconds}", "{part_number}", "{previous_parts}"],
        "sections": ["השיעור משותף לכל הילדים"],
    },
    "iakids_lesson_initial_prompt.txt": {
        "placeholders": ["{grade}", "{subject}", "{lesson_name}", "{learning_objective}"],
        "sections": [],
    },
    "lesson_director_prompt.txt": {
        "placeholders": ["{lesson_text}"],
        "sections": ["THE QUESTION IS IMMUTABLE", "lesson", "question", "מה אסור בתוך lesson"],
    },
    "iakids_lesson_transition_prompt.txt": {"placeholders": [], "sections": []},
    "learning_coach_system_prompt.txt": {
        "placeholders": [],
        "sections": ["RUNTIME_DATA.child.gender", "אין להסיק את המגדר לפי שם הילד"],
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


def render_smoke() -> list:
    """Import main (needs .env.prod) and render every builder with sample data."""
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
    return [Path(n).name for n in names if n.startswith("backend-ai-tutor-he/prompts/") and n.endswith(".txt")]


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
    main_changed = "backend-ai-tutor-he/main.py" in sh("git", "diff", "--cached" if a.staged else "HEAD", "--name-only").split()
    if not names and not main_changed:
        print("prompt gate: no prompt or main.py changes")
        return 0
    if not names and main_changed:
        # main.py changed: the render smoke doubles as an import smoke (a route decorator on the
        # wrong function, a missing package...) — it must pass before the service is restarted
        rf = [] if a.fast else render_smoke()
        print(("FAIL " if rf else "ok   ") + "render/import smoke for main.py")
        if rf:
            print("\nPROMPT GATE FAILED:\n - " + "\n - ".join(rf), file=sys.stderr)
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
    pf = pure_function_tests() + persona_checks(main_src) + coverage_checks(main_src) + code_rule_checks(main_src)
    print(("FAIL " if pf else "ok   ") + "lesson_quality unit tests (TTS normaliser, validators)")
    all_fails += pf
    if not a.fast:
        rf = render_smoke()
        print(("FAIL " if rf else "ok   ") + "render smoke (all builders, no unresolved placeholders)")
        all_fails += rf
    if all_fails:
        print("\nPROMPT GATE FAILED:\n - " + "\n - ".join(all_fails), file=sys.stderr)
        return 1
    print("\nPROMPT GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
