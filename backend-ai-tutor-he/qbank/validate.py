"""Item validation for the question bank. Pure functions: the gate (tools/prompt_gate.py, qbank_checks) and the
generators use the same rules, so an item that reaches the review queue already passed them.

    problems = validate_item(item, topic=None, sources=None)   # [] = fine

What is checked (research 2026-09-25: Haladyna et al. item-writing guidelines + this project's Hebrew rules):
  shape        required fields, grade 1-6, purpose, difficulty 1-3, exactly 4 different options, key in range
  distractors  every wrong option has its own explanation (why_wrong), and there is an explanation of the key
  licence      the source exists and is class A; an adapted item names its source and carries attribution
  reading load the stem (and the passage) fit the grade: a question a 7-year-old cannot read tests reading
  Hebrew       no slash forms (נסה/י), no singular male/female address (the bank is shared by boys and girls:
               plural or infinitive, like the lessons), no gershayim abbreviations
  key leak     the key's text is not written in the stem
  maths        a numeric item carries `solution_expr` (arithmetic only) and it evaluates to the key; no
               distractor equals the key's value
  copy risk    near-duplicates (5-word shingles) of another item in the lake or of a blocked text are refused
"""
import ast
import hashlib
import operator
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
try:
    from lesson_quality import _GENDERED            # the same singular-address rule the lessons use
except Exception:                                    # pragma: no cover - lesson_quality always ships with the service
    _GENDERED = re.compile(r"$^")

# the imperatives a question uses, singular male and female (the lessons' list covers other words); חשוב and כתוב
# are left out on purpose: they are also "important" and "written"
_SINGULAR_Q = re.compile(
    r"(?<![\w\u0590-\u05FF])(בחר|בחרי|תבחר|תבחרי|נסה|ענה|עני|תענה|תעני|מצא|מצאי|תמצא|תמצאי|בדוק|בדקי|סמן|סמני|"
    r"הקף|הקיפי|השלם|השלימי|חשבי|קרא|קראי|ספור|ספרי|שים לב|שימי לב)(?![\w\u0590-\u05FF])")

SUBJECTS = {"math", "science", "english", "hebrew", "moledet", "geography", "history", "tanakh"}
PURPOSES = {"practice", "exam_prep", "gifted"}
# words a child of the grade can be asked to read in one question stem / one passage
STEM_MAX_WORDS = {1: 25, 2: 35, 3: 50, 4: 70, 5: 90, 6: 110}
PASSAGE_MAX_WORDS = {1: 60, 2: 110, 3: 180, 4: 260, 5: 330, 6: 400}
SLASH = re.compile(r"[֐-׿]+/[֐-׿]{1,3}\b")
GERSHAYIM = re.compile(r"[֐-׿]+\"[֐-׿]\b")
NIKUD = re.compile(r"[֑-ׇ]")


def plain(text) -> str:
    """Hebrew without vowel points, for comparisons and word counts."""
    return NIKUD.sub("", str(text or ""))


def words(text) -> int:
    return len(plain(text).split())


# ------------------------------------------------------------------ safe arithmetic for solution_expr
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos}


def safe_eval(expr: str):
    """Evaluate +, -, *, /, //, %, parentheses and numbers only. Anything else raises ValueError."""
    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError(f"not arithmetic: {ast.dump(node)[:60]}")
    if len(str(expr)) > 200:
        raise ValueError("expression too long")
    return ev(ast.parse(str(expr), mode="eval"))


def _as_number(v):
    if isinstance(v, (int, float)):
        return v
    m = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?)\s*(?:[֐-׿₪%°].*)?", plain(v))
    return float(m.group(1)) if m else None


# ------------------------------------------------------------------ fingerprints and copy risk
def normalise(text) -> str:
    t = plain(text).lower()
    t = re.sub(r"[^\w֐-׿ ]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def fingerprint(item) -> str:
    body = normalise(item.get("stimulus") or "") + "|" + normalise(item.get("stem")) + "|" + \
        "|".join(normalise(o) for o in item.get("options") or [])
    return hashlib.sha1(body.encode("utf-8")).hexdigest()[:20]


def shingles(text, n: int = 5) -> set:
    w = normalise(text).split()
    return {hashlib.sha1(" ".join(w[i:i + n]).encode()).hexdigest()[:12] for i in range(max(0, len(w) - n + 1))}


def item_shingles(item) -> set:
    return shingles((item.get("stimulus") or "") + " " + str(item.get("stem") or ""))


def copy_risk(item, corpus: dict, threshold: float = 0.5) -> list:
    """corpus: {name: shingle set}. A stem/passage sharing half its 5-word runs with another text is a copy."""
    mine = item_shingles(item)
    if len(mine) < 3:
        return []
    out = []
    for name, other in corpus.items():
        if other and len(mine & other) / len(mine) >= threshold:
            out.append(f"{item.get('id')}: {round(100 * len(mine & other) / len(mine))}% of its text repeats {name}: a copy, not an original item")
    return out


# ------------------------------------------------------------------ the item
def validate_item(item: dict, topic: dict | None = None, sources: dict | None = None) -> list:
    iid = item.get("id") or "?"
    bad = []

    def b(msg):
        bad.append(f"{iid}: {msg}")

    for f in ("id", "topic_code", "subject", "grade", "purpose", "difficulty", "stem", "options", "answer", "why_wrong", "explain", "origin"):
        if item.get(f) in (None, "", []):
            b(f"missing {f}")
    if bad:
        return bad
    if item["subject"] not in SUBJECTS:
        b(f"unknown subject {item['subject']!r}")
    if not isinstance(item["grade"], int) or not 1 <= item["grade"] <= 6:
        b(f"grade {item['grade']!r} is not 1-6")
    if item["purpose"] not in PURPOSES:
        b(f"purpose {item['purpose']!r} is not one of {sorted(PURPOSES)}")
    if item["difficulty"] not in (1, 2, 3):
        b("difficulty must be 1, 2 or 3")
    if topic is not None:
        if topic.get("code") != item["topic_code"]:
            b("topic_code does not match its topic")
        if topic.get("grade") != item["grade"] or topic.get("subject") != item["subject"]:
            b(f"item says grade {item['grade']} {item['subject']}, its topic is grade {topic.get('grade')} {topic.get('subject')}")
    opts, ans = item["options"], item["answer"]
    if not isinstance(opts, list) or len(opts) != 4:
        return bad + [f"{iid}: needs exactly 4 options"]
    if len({normalise(o) for o in opts}) != 4 or any(not normalise(o) for o in opts):
        b("the 4 options must be different and non-empty")
    if not isinstance(ans, int) or not 0 <= ans <= 3:
        return bad + [f"{iid}: answer index out of range"]
    ww = item["why_wrong"]
    if not isinstance(ww, dict) or sorted(ww) != sorted(str(i) for i in range(4) if i != ans) or any(not str(v).strip() for v in ww.values()):
        b("why_wrong must explain each of the 3 wrong options (keys '0'..'3' except the answer)")
    if len(str(item["explain"]).strip()) < 15:
        b("the explanation of the answer is missing or too short")
    # licence
    src = item.get("source_id") or "original"
    if sources is not None:
        s = sources.get(src)
        if s is None:
            b(f"source {src!r} is not in qbank/sources.json")
        elif s["licence_class"] != "A":
            b(f"source {src!r} is class {s['licence_class']}: only class-A sources may feed items")
    if item["origin"] == "adapted_open":
        if src == "original":
            b("an adapted item must name its open source")
        if not item.get("attribution"):
            b("an adapted item must carry its attribution line")
    if item.get("purpose") == "gifted" and item["origin"] == "adapted_open":
        b("gifted items are original only (no open source exists for them)")
    # reading load
    g = item["grade"] if isinstance(item["grade"], int) and 1 <= item["grade"] <= 6 else 6
    if words(item["stem"]) > STEM_MAX_WORDS[g]:
        b(f"the question has {words(item['stem'])} words, too long to read in grade {g} (max {STEM_MAX_WORDS[g]})")
    if item.get("stimulus") and words(item["stimulus"]) > PASSAGE_MAX_WORDS[g]:
        b(f"the passage has {words(item['stimulus'])} words, too long for grade {g} (max {PASSAGE_MAX_WORDS[g]})")
    # Hebrew
    texts = [item["stem"], item.get("stimulus") or "", item["explain"]] + [str(o) for o in opts] + [str(v) for v in ww.values()]
    if item.get("language", "he") == "he":
        for t in texts:
            if SLASH.search(plain(t)):
                b(f"slash form {SLASH.search(plain(t)).group(0)!r}: read aloud as gibberish; write for boys and girls together")
                break
        for t in [item["stem"], item.get("stimulus") or "", item["explain"]]:
            hits = _GENDERED.findall(plain(t)) + _SINGULAR_Q.findall(plain(t))
            if hits:
                b(f"singular male/female address {hits[:3]}: the bank is shared, use plural or infinitive (בחרו, לבחור)")
                break
        for t in texts:
            if GERSHAYIM.search(plain(t)):
                b(f"abbreviation {GERSHAYIM.search(plain(t)).group(0)!r}: write the words in full")
                break
    # key leak
    key = opts[ans]
    if isinstance(key, str) and len(normalise(key)) >= 4 and item["subject"] not in ("math",) and normalise(key) in normalise(item["stem"]):
        b("the correct answer is written in the question")
    # maths
    if item["subject"] == "math":
        kv = _as_number(key)
        if kv is not None:
            if not item.get("solution_expr"):
                b("a numeric maths item needs solution_expr (the arithmetic that gives the answer)")
            else:
                try:
                    val = safe_eval(item["solution_expr"])
                    if abs(val - kv) > 1e-9:
                        b(f"solution_expr gives {val}, the key says {key}: the item is wrong")
                except Exception as e:
                    b(f"solution_expr cannot be computed ({e})")
            if any(_as_number(o) == kv for i, o in enumerate(opts) if i != ans):
                b("a wrong option has the same value as the answer")
    return bad
