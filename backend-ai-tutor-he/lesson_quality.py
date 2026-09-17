"""Edge-case hardening for lessons: text → speech normalisation, validators, and the
per-lesson QUALITY GATE that runs after every media job (report stored in
generated_lesson_json["quality"], no migration needed).

Pure functions (no network) are at the top so tools/prompt_gate.py can unit-test them
for free. The two functions that talk to Storage / Gemini are at the bottom.
"""
import re
import json
import time
from datetime import datetime, timezone

# ----------------------------------------------------------------------------- TTS text
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF⭐⬆✅❌✔✖"
    "✨✳✴⬛⬜️‍]"
)
_ARROWS = re.compile(r"\s*[←-⇿⟵-⟿⬅⮕>]+\s*")   # ← → ↔ ⟵ ⟶ and ascii '>'
_UNITS = {
    'ק"מ/ש': "קילומטר לשעה", 'קמ"ש': "קילומטר לשעה", 'ק"מ': "קילומטר", 'ס"מ': "סנטימטר", 'מ"מ': "מילימטר",
    'ק"ג': "קילוגרם", 'מ"ג': "מיליגרם", 'מ"ל': "מיליליטר", 'מ"ר': "מטר רבוע", 'קמ"ר': "קילומטר רבוע",
    'סמ"ק': "סנטימטר מעוקב", 'מ"ק': "מטר מעוקב", 'ד"ר': "דוקטור", 'יו"ר': "יושב ראש", 'ת"א': "תל אביב",
    'ארה"ב': "ארצות הברית", 'בי"ס': "בית ספר", 'ז"א': "זאת אומרת", 'עמ\'': "עמוד", 'לפנה"ס': "לפני הספירה",
}
_FRACTIONS = {"½": "חצי", "¼": "רבע", "¾": "שלושת רבעי", "⅓": "שליש", "⅔": "שני שליש"}
_FRACTION_WORDS = {(1, 2): "חצי", (1, 3): "שליש", (2, 3): "שני שליש", (1, 4): "רבע", (3, 4): "שלושת רבעי",
                   (1, 5): "חמישית", (1, 10): "עשירית"}


def normalize_for_tts(text: str) -> str:
    """What the voice should actually say: no emoji, arrows become pauses, math symbols,
    fractions and common gershayim abbreviations are spelled out."""
    s = str(text or "")
    s = _EMOJI.sub("", s)
    # gershayim in Hebrew text is often written with a plain quote or ״
    s = s.replace("״", '"').replace("׳", "'")
    for k in sorted(_UNITS, key=len, reverse=True):
        # allow a one-letter Hebrew prefix (מ, ב, ל, ו, ה, ש, כ) glued to the abbreviation: מבי"ס -> מבית ספר
        s = re.sub(r"(?<![\w\u0590-\u05FF])([ובלמהשכ]?)" + re.escape(k) + r"(?![\w\u0590-\u05FF])",
                   lambda m, v=_UNITS[k]: m.group(1) + v, s)
    for k, v in _FRACTIONS.items():
        s = s.replace(k, " " + v + " ")
    def frac(m):
        a, b = int(m.group(1)), int(m.group(2))
        return " " + _FRACTION_WORDS.get((a, b), f"{a} חלקי {b}") + " "
    s = re.sub(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", frac, s)
    s = re.sub(r"(?<=\d)\s*×\s*(?=\d)", " כפול ", s)
    s = re.sub(r"(?<=\d)\s*[÷:]\s*(?=\d)", " חלקי ", s)
    s = re.sub(r"(?<=\d)\s*\+\s*(?=\d)", " ועוד ", s)
    s = re.sub(r"(?<=\d)\s*[-−]\s*(?=\d)", " פחות ", s)
    s = re.sub(r"(?<=\d)\s*=\s*(?=\d)", " שווה ", s)
    s = re.sub(r"(?<=\d)\s*%", " אחוז", s)
    s = re.sub(r"(?<=\d)\s*°C?", " מעלות", s)
    s = _ARROWS.sub(", ", s)
    s = re.sub(r"[•●▪◦★☆✦]+", " ", s)
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def split_for_tts(text: str, max_chars: int = 350) -> list:
    """Sentence chunks each ≤ max_chars (the TTS model answers 400 INVALID_ARGUMENT on long
    or odd text; shorter calls also fail less)."""
    s = str(text or "").strip()
    if len(s) <= max_chars:
        return [s] if s else []
    parts = re.split(r"(?<=[.!?:;])\s+", s)
    out, cur = [], ""
    for p in parts:
        if len(cur) + len(p) + 1 <= max_chars:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                out.append(cur)
            while len(p) > max_chars:                 # a single monster sentence: hard cut on a comma/space
                cut = max(p.rfind(",", 0, max_chars), p.rfind(" ", 0, max_chars), 1)
                out.append(p[:cut].strip()); p = p[cut:].strip()
            cur = p
    if cur:
        out.append(cur)
    return out


_TEXT_REQUESTS = re.compile(
    r"\b(clearly\s+)?(labeled|labelled|with labels?|label(s|ed|ling)?|captioned|captions?|annotated|annotations?|"
    r"with (the )?words?|the word\s*\"[^\"]*\"|text (reading|saying|that says)[^.,;]*|sign(s)? (that )?(say|read)s?[^.,;]*|"
    r"titled? ?:? ?[^.,;]*|subtitles?|written (words|text|hebrew|english)|arrows? with (text|words)|speech bubbles?)\b",
    re.I,
)
NO_TEXT_TAIL = " No written text, letters, numbers, labels, captions, titles or signs anywhere in the image."


def sanitize_generation_prompt(prompt: str) -> str:
    """The visual director sometimes asks for 'a labeled diagram' although the rules forbid
    text; the image model then renders words. Strip such requests and end with the rule."""
    p = str(prompt or "")
    cleaned = _TEXT_REQUESTS.sub("", p)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).replace(" ,", ",").replace(" :", ":").strip()
    cleaned = re.sub(r"\bwith\s*:", "with", cleaned)
    if not cleaned.rstrip().endswith(NO_TEXT_TAIL.strip()):
        cleaned = cleaned.rstrip() + NO_TEXT_TAIL
    return cleaned


# ----------------------------------------------------------------------------- lesson text
_DIRECTIVE = ("הסבירו", "הסבר", "הסבירי", "תארו", "תאר", "תארי", "כיצד", "איך", "מדוע", "למה", "חשבו", "חשוב", "חשבי",
              "ענו", "ענה", "עני", "נסו", "נסה", "נסי", "כתבו", "כתוב", "כתבי", "סדרו", "מצאו", "ציינו", "הציעו", "בדקו",
              "מה ", "מי ", "איזה", "אילו", "האם")
_CONNECTIVE = ("לכן", "כלומר", "למשל", "לדוגמה", "אבל", "כך", "כדי", "אם ", "כאשר", "כש", "וכך", "ובכל", "זאת", "מכאן")


def question_segment_problem(text: str) -> str | None:
    """None if this explanation segment is fine, else why it reads as a question to the child.
    A rhetorical question inside an explanation ("לכן שואלים: מה השתנה?") is allowed."""
    t = str(text or "").strip()
    if not t:
        return "empty"
    if t.startswith(_DIRECTIVE):
        return "directive_to_student"
    if t.rstrip().endswith("?"):
        rhetorical = len(t) >= 90 and (":" in t or t.startswith(_CONNECTIVE))
        if not rhetorical:
            return "ends_with_question_mark"
    return None


def display_first_name(name: str) -> str:
    """Name as the voice greets it: first token when the profile holds a long full name."""
    n = re.sub(r"[^\w\s'֐-׿-]", " ", str(name or "")).strip()
    n = re.sub(r"\s+", " ", n)
    toks = n.split(" ")
    if len(toks) >= 3 or len(n) > 20:
        return toks[0]
    return n


_GENDERED = re.compile(
    r"(?<![\w֐-׿])(אתה|שלך|שלךְ|תוכל|תוכלי|נסי|חשבי|כתבי|תארי|הסבירי|תנסה|תנסי|תחשוב|תחשבי|"
    r"תסתכל|תסתכלי|תזכור|תזכרי|בעצמך|מוכנה)(?![\w֐-׿])"
)
_PLACEHOLDER = re.compile(r"\{[a-z_]+\}")
MAX_SEGMENT_CHARS = 400


def text_checks(structured_lesson: dict) -> tuple[list, list, dict]:
    """(errors, warnings, stats) for the shared lesson text."""
    errors, warnings = [], []
    parts = (structured_lesson or {}).get("parts") or []
    stats = {"parts": len(parts), "segments": 0, "questions": 0}
    if not parts:
        return ["no parts"], [], stats
    for p in parts:
        n = p.get("part_number")
        segs = [str(s.get("text") or "") for s in (p.get("lesson") or []) if isinstance(s, dict)]
        q = str((p.get("question") or {}).get("text") or "").strip()
        stats["segments"] += len(segs)
        stats["questions"] += 1 if q else 0
        if not segs:
            errors.append(f"part {n}: lesson[] is empty")
        if not q:
            errors.append(f"part {n}: question is missing")
        for i, s in enumerate(segs, 1):
            if not s.strip():
                errors.append(f"part {n} segment {i}: empty"); continue
            if len(s) > MAX_SEGMENT_CHARS:
                warnings.append(f"part {n} segment {i}: {len(s)} chars (> {MAX_SEGMENT_CHARS}, split for TTS)")
            why = question_segment_problem(s)
            if why:
                errors.append(f"part {n} segment {i}: reads as a question to the child ({why}): {s[:60]}")
            g = _GENDERED.findall(s)
            if g:
                errors.append(f"part {n} segment {i}: gendered 2nd person in shared lesson {g[:3]}")
            if _PLACEHOLDER.search(s):
                errors.append(f"part {n} segment {i}: unresolved placeholder")
            if _EMOJI.search(s):
                warnings.append(f"part {n} segment {i}: emoji in spoken text")
        if q and _GENDERED.findall(q):
            errors.append(f"part {n} question: gendered 2nd person {_GENDERED.findall(q)[:3]}")
    return errors, warnings, stats


def visual_plan_checks(structured_lesson: dict, visual_plan) -> tuple[list, list, dict]:
    """Every part needs one visual per segment + one for the question; trigger_text must be
    found in that part's text (that is how the player switches images)."""
    errors, warnings = [], []
    parts = {int(p.get("part_number") or 0): p for p in (structured_lesson or {}).get("parts") or []}
    visuals = []
    def walk(o):
        if isinstance(o, dict):
            if "generation_prompt" in o or "trigger_text" in o:
                visuals.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(visual_plan)
    stats = {"visuals": len(visuals), "images_generated": sum(1 for v in visuals if not v.get("reuse_of")),
             "images_reused": sum(1 for v in visuals if v.get("reuse_of"))}
    by_part = {}
    for v in visuals:
        by_part.setdefault(int(v.get("part_number") or 0), []).append(v)
    for n, p in parts.items():
        segs = [str(s.get("text") or "") for s in (p.get("lesson") or []) if isinstance(s, dict)]
        q = str((p.get("question") or {}).get("text") or "")
        expected = len(segs) + (1 if q else 0)
        got = len(by_part.get(n, []))
        if got != expected:
            errors.append(f"part {n}: {got} visuals for {len(segs)} segments + question (expected {expected})")
        text_all = " ".join(segs + [q])
        norm = re.sub(r"\s+", " ", text_all)
        for v in by_part.get(n, []):
            trig = re.sub(r"\s+", " ", str(v.get("trigger_text") or "").strip())
            if trig and trig not in norm:
                warnings.append(f"part {n} visual {v.get('order')}: trigger_text not found in text: {trig[:40]!r}")
    return errors, warnings, stats


def audio_checks(structured_lesson: dict, lesson_audio_json) -> tuple[list, list, dict]:
    errors, warnings = [], []
    parts = {int(p.get("part_number") or 0): p for p in (structured_lesson or {}).get("parts") or []}
    aj = lesson_audio_json or {}
    aparts = {int(a.get("part_number") or 0): a for a in (aj.get("parts") or []) if isinstance(a, dict)}
    stats = {"audio_parts": len(aparts), "audio_seconds": 0.0}
    if not aparts:
        return ["no audio parts"], [], stats
    for n, p in parts.items():
        segs = [s for s in (p.get("lesson") or []) if isinstance(s, dict) and str(s.get("text") or "").strip()]
        a = aparts.get(n)
        if not a:
            errors.append(f"part {n}: no audio"); continue
        got = len(a.get("segments") or [])
        if got != len(segs):
            errors.append(f"part {n}: {got} audio segments for {len(segs)} text segments")
        if (p.get("question") or {}).get("text") and not (a.get("question") or {}).get("path"):
            errors.append(f"part {n}: question audio missing")
        if not a.get("complete", True):
            warnings.append(f"part {n}: audio marked incomplete")
        stats["audio_seconds"] += float(a.get("total_duration_seconds") or 0)
    return errors, warnings, stats


# ----------------------------------------------------------------------------- network bits
# Universally readable scientific notation is language-neutral and allowed in a shared
# image (product decision 2026-09-16): chemical formulas, gas symbols, units, plain numbers.
_FORMULA = re.compile(r"^(?:[A-Z][a-z]?\d{0,2}){1,3}$")          # case-sensitive: CO2, H2O, NaCl, C6H12O6
_NUMBER = re.compile(r"^\d+(?:[.,]\d+)?$")
_UNIT = re.compile(r"^(?:%|°C|°|km|kg|m|cm|mm|ml|l|g|kmh|km/h)$", re.I)
_ALLOWED_WORDS = {"co2", "h2o", "o2", "n2", "ph", "dna", "rna", "atp", "nacl", "ch4", "co",
                  "sin", "cos", "tan", "cot", "log", "ln", "exp", "π", "pi", "√", "sqrt", "x", "y", "z", "n", "a", "b", "c",
                  "x²", "x2", "y²", "∞", "≠", "≤", "≥", "α", "β", "θ", "δ", "%", "°"}


def is_allowed_scientific_text(text: str) -> bool:
    """True when every token of the detected text is a chemical formula (must contain a digit or be
    in the allowlist), a plain number or a unit. Words like 'Growth' never qualify."""
    t = str(text or "").replace("₂", "2").replace("₃", "3").replace("₄", "4").strip()
    if not t:
        return False
    tokens = [x for x in re.split(r"[\s,;/+→←↔=\-–×÷·()\[\]]+", t) if x]
    def ok(x):
        x = x.lstrip("√")                                   # √2, √x
        if not x or x.lower() in _ALLOWED_WORDS or _NUMBER.match(x) or _UNIT.match(x):
            return True
        if re.fullmatch(r"[a-z]\^?[0-9²³]?", x, re.I):         # x, y², a^2
            return True
        return bool(_FORMULA.match(x)) and any(ch.isdigit() for ch in x)
    return all(ok(x) for x in tokens)


IMAGE_TEXT_CHECK_PROMPT = (
    "Look at this educational illustration for children. Does it contain READABLE written text: "
    "words, letters, numbers, labels, captions, signs, titles or watermarks, in any language? "
    "Rules: quote the text VERBATIM (the exact characters you can read, max 80 characters), never "
    "describe the picture. Symbols, icons, arrows, color bars or scribbles that are not readable "
    "characters are NOT text. Answer ONLY with JSON: "
    '{"has_text": true|false, "text": "<verbatim readable text or empty>", '
    '"kind": "words"|"letters"|"numbers"|"formula"|"none", "confidence": "high"|"low"}. '
    "Use kind=formula for chemical formulas, math notation (sin, cos, π, √, x², 3+4=7) or units such as CO2, H2O, °C."
)


def image_text_check(gemini_client, types, model: str, image_bytes: bytes, mime_type: str = "image/png") -> dict:
    """{'has_text': bool, 'text': str, 'ms': int}. Raises on API failure (caller decides)."""
    t0 = time.perf_counter()
    resp = gemini_client.models.generate_content(
        model=model,
        contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), IMAGE_TEXT_CHECK_PROMPT],
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json"),
    )
    raw = str(getattr(resp, "text", "") or "").strip()
    try:
        data = json.loads(raw)
    except Exception:
        data = {"has_text": "true" in raw.lower(), "text": raw[:80]}
    text = str(data.get("text") or "")[:120].strip()
    has_text = bool(data.get("has_text")) and bool(text)
    # a long "text" without spaces/letters pattern of a sentence is a description, not a quote -> low confidence
    looks_like_description = len(text.split()) > 8 and not any(ch.isdigit() for ch in text) and text[:1].isupper() and text.endswith((".", "…"))
    confidence = str(data.get("confidence") or "high").lower()
    if looks_like_description:
        confidence = "low"
    return {"has_text": has_text, "text": text, "kind": str(data.get("kind") or ("none" if not has_text else "words")),
            "confidence": confidence, "ms": round((time.perf_counter() - t0) * 1000)}


def build_quality_report(structured_lesson, visual_plan, lesson_audio_json, content_version,
                         media_paths: list, audio_paths: list, image_text_results: dict | None,
                         image_overrides: dict | None = None) -> dict:
    """Combine all checks + storage consistency into one report."""
    errors, warnings, stats = [], [], {"content_version": content_version}
    for fn, arg in ((text_checks, (structured_lesson,)),
                    (visual_plan_checks, (structured_lesson, visual_plan)),
                    (audio_checks, (structured_lesson, lesson_audio_json))):
        e, w, s = fn(*arg)
        errors += e; warnings += w; stats.update(s)
    # storage: files of another content_version are stale and may get served by mistake
    vtag = f"/v{content_version}/"
    stale = [p for p in media_paths + audio_paths if "/v" in p and vtag not in p and "hero_v" not in p]
    if stale:
        errors.append(f"{len(stale)} stale media files from another content_version (delete or bump): {stale[:3]}")
    stats["media_files"] = len(media_paths)
    stats["audio_files"] = len(audio_paths)
    # every audio path in the json must exist in storage
    aj = lesson_audio_json or {}
    wanted = []
    for a in aj.get("parts") or []:
        wanted += [s.get("path") for s in (a.get("segments") or []) if isinstance(s, dict)]
        if (a.get("question") or {}).get("path"):
            wanted.append(a["question"]["path"])
    missing = [p for p in wanted if p and p not in set(audio_paths)]
    if missing:
        errors.append(f"{len(missing)} audio files referenced but not in storage: {missing[:3]}")
    images = {}
    if image_text_results is not None:
        overrides = image_overrides or {}
        stats["images_checked"] = len(image_text_results)
        n_err = 0
        for k, v in image_text_results.items():
            entry = dict(v)
            if k in overrides:
                entry["verdict"] = "approved_by_human"
            elif v.get("has_text") and (v.get("kind") == "formula" or is_allowed_scientific_text(v.get("text", ""))):
                entry["verdict"] = "formula_ok"          # CO2 / H2O / numbers: language-neutral, allowed
            elif v.get("has_text") and v.get("confidence", "high") == "high":
                entry["verdict"] = "text"; n_err += 1
                errors.append(f"readable text in image {k}: {v.get('text', '')[:60]!r}")
            elif v.get("has_text"):
                entry["verdict"] = "possible_text"
                warnings.append(f"possible text in image {k} (low confidence): {v.get('text', '')[:60]!r}")
            else:
                entry["verdict"] = "clean"
            images[k] = entry
        stats["images_with_text"] = n_err
    return {
        "images": images,
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "stats": stats,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
    }


# ----------------------------------------------------------------------------- image budget
_STOP = {"the", "a", "an", "of", "and", "with", "in", "on", "at", "to", "for", "showing", "illustration",
         "image", "scene", "visual", "educational", "children", "child", "style", "same", "that", "this",
         "its", "into", "from", "by", "as", "is", "are", "or", "their", "it", "be", "no", "not", "text"}


def _content_words(prompt: str) -> set:
    return {w for w in re.findall(r"[a-zA-Z\u0590-\u05FF]{3,}", str(prompt or "").lower()) if w not in _STOP}


def prompt_similarity(a: str, b: str) -> float:
    """Jaccard similarity of the content words of two generation prompts (0..1)."""
    x, y = _content_words(a), _content_words(b)
    if not x or not y:
        return 0.0
    return len(x & y) / len(x | y)


def enforce_image_budget(entries: list, new_ratio: float = 0.5, min_new: int = 3, model_flags: list | None = None) -> list:
    """Decide which segment entries get a NEW image and which reuse the previous one.

    entries: the part's visual entries in order (dicts with 'generation_prompt').
    model_flags: the director's reuse_previous per entry (unreliable: it swings between
    0% and 90%), used only as a tie-breaker. Deterministic rule:
      budget = clamp(ceil(S * new_ratio), min_new, S); the first entry is always new;
      the remaining new slots go to the entries whose prompt differs MOST from the
      previous entry's prompt (lowest similarity). Returns the same list with 'reuse_of'
      set (None = new image, k = show image of order k).
    """
    import math
    S = len(entries)
    if S == 0:
        return entries
    budget = max(min(min_new, S), min(S, math.ceil(S * new_ratio)))
    flags = list(model_flags or [False] * S)
    sims = [0.0] + [prompt_similarity(entries[i - 1].get("generation_prompt", ""), entries[i].get("generation_prompt", ""))
                    for i in range(1, S)]
    # candidates for NEW: index 0 forced; others ranked by (dissimilarity, model said new)
    order_idx = sorted(range(1, S), key=lambda i: (sims[i], 1 if flags[i] else 0))
    new_idx = {0} | set(order_idx[:max(0, budget - 1)])
    last_new = None
    for i, e in enumerate(entries):
        if i in new_idx:
            e["reuse_of"] = None
            last_new = int(e.get("order") or (i + 1))
        else:
            e["reuse_of"] = last_new
            src = next((x for x in entries if int(x.get("order") or 0) == last_new), None)
            if src:
                e["generation_prompt"] = src.get("generation_prompt") or e.get("generation_prompt")
    return entries

# ----------------------------------------------------------------------------- 2nd person, by gender
# Hebrew writes many second-person forms IDENTICALLY for a boy and a girl and only the
# vowels differ, so a text that is correct on screen is read in the wrong gender aloud
# ("אני כאן בשבילך" -> bishvilKHA to a girl, 2026-09-17). Deterministic table, no model.
# (masculine, feminine)
_SECOND_PERSON = {
    # -ך suffix: pronouns and prepositions
    "שלך": ("\u05e9\u05b6\u05c1\u05dc\u05bc\u05b0\u05da\u05b8", "\u05e9\u05b6\u05c1\u05dc\u05b8\u05bc\u05da\u05b0"),
    "לך": ("\u05dc\u05b0\u05da\u05b8", "\u05dc\u05b8\u05da\u05b0"),
    "בך": ("\u05d1\u05b0\u05bc\u05da\u05b8", "\u05d1\u05b8\u05bc\u05da\u05b0"),
    "ממך": ("\u05de\u05b4\u05de\u05bc\u05b0\u05da\u05b8", "\u05de\u05b4\u05de\u05bc\u05b5\u05da\u05b0"),
    "אליך": ("\u05d0\u05b5\u05dc\u05b6\u05d9\u05da\u05b8", "\u05d0\u05b5\u05dc\u05b7\u05d9\u05b4\u05da\u05b0"),
    "עליך": ("\u05e2\u05b8\u05dc\u05b6\u05d9\u05da\u05b8", "\u05e2\u05b8\u05dc\u05b7\u05d9\u05b4\u05da\u05b0"),
    "איתך": ("\u05d0\u05b4\u05ea\u05bc\u05b0\u05da\u05b8", "\u05d0\u05b4\u05ea\u05bc\u05b8\u05da\u05b0"),
    "אותך": ("\u05d0\u05d5\u05b9\u05ea\u05b0\u05da\u05b8", "\u05d0\u05d5\u05b9\u05ea\u05b8\u05da\u05b0"),
    "בשבילך": ("\u05d1\u05b4\u05bc\u05e9\u05c1\u05b0\u05d1\u05b4\u05d9\u05dc\u05b0\u05da\u05b8", "\u05d1\u05b4\u05bc\u05e9\u05c1\u05b0\u05d1\u05b4\u05d9\u05dc\u05b5\u05da\u05b0"),
    "אצלך": ("\u05d0\u05b6\u05e6\u05b0\u05dc\u05b0\u05da\u05b8", "\u05d0\u05b6\u05e6\u05b0\u05dc\u05b5\u05da\u05b0"),
    "כמוך": ("\u05db\u05bc\u05b8\u05de\u05d5\u05b9\u05da\u05b8", "\u05db\u05bc\u05b8\u05de\u05d5\u05b9\u05da\u05b0"),
    "עבורך": ("\u05e2\u05b2\u05d1\u05d5\u05bc\u05e8\u05b0\u05da\u05b8", "\u05e2\u05b2\u05d1\u05d5\u05bc\u05e8\u05b5\u05da\u05b0"),
    "שלומך": ("\u05e9\u05c1\u05b0\u05dc\u05d5\u05b9\u05de\u05b0\u05da\u05b8", "\u05e9\u05c1\u05b0\u05dc\u05d5\u05b9\u05de\u05b5\u05da\u05b0"),
    "דעתך": ("\u05d3\u05bc\u05b7\u05e2\u05b0\u05ea\u05bc\u05b0\u05da\u05b8", "\u05d3\u05bc\u05b7\u05e2\u05b0\u05ea\u05bc\u05b5\u05da\u05b0"),
    # 2nd person past tense: -ְתָּ vs -ְתְּ
    "הצלחת": ("\u05d4\u05b4\u05e6\u05b0\u05dc\u05b7\u05d7\u05b0\u05ea\u05bc\u05b8", "\u05d4\u05b4\u05e6\u05b0\u05dc\u05b7\u05d7\u05b0\u05ea\u05bc\u05b0"),
    "אמרת": ("\u05d0\u05b8\u05de\u05b7\u05e8\u05b0\u05ea\u05bc\u05b8", "\u05d0\u05b8\u05de\u05b7\u05e8\u05b0\u05ea\u05bc\u05b0"),
    "כתבת": ("\u05db\u05bc\u05b8\u05ea\u05b7\u05d1\u05b0\u05ea\u05bc\u05b8", "\u05db\u05bc\u05b8\u05ea\u05b7\u05d1\u05b0\u05ea\u05bc\u05b0"),
    "חשבת": ("\u05d7\u05b8\u05e9\u05c1\u05b7\u05d1\u05b0\u05ea\u05bc\u05b8", "\u05d7\u05b8\u05e9\u05c1\u05b7\u05d1\u05b0\u05ea\u05bc\u05b0"),
    "למדת": ("\u05dc\u05b8\u05de\u05b7\u05d3\u05b0\u05ea\u05bc\u05b8", "\u05dc\u05b8\u05de\u05b7\u05d3\u05b0\u05ea\u05bc\u05b0"),
    "הבנת": ("\u05d4\u05b5\u05d1\u05b7\u05e0\u05b0\u05ea\u05bc\u05b8", "\u05d4\u05b5\u05d1\u05b7\u05e0\u05b0\u05ea\u05bc\u05b0"),
    "ידעת": ("\u05d9\u05b8\u05d3\u05b7\u05e2\u05b0\u05ea\u05bc\u05b8", "\u05d9\u05b8\u05d3\u05b7\u05e2\u05b0\u05ea\u05bc\u05b0"),
    "בחרת": ("\u05d1\u05b8\u05bc\u05d7\u05b7\u05e8\u05b0\u05ea\u05bc\u05b8", "\u05d1\u05b8\u05bc\u05d7\u05b7\u05e8\u05b0\u05ea\u05bc\u05b0"),
    "שמעת": ("\u05e9\u05c1\u05b8\u05de\u05b7\u05e2\u05b0\u05ea\u05bc\u05b8", "\u05e9\u05c1\u05b8\u05de\u05b7\u05e2\u05b0\u05ea\u05bc\u05b0"),
    "זכרת": ("\u05d6\u05b8\u05db\u05b7\u05e8\u05b0\u05ea\u05bc\u05b8", "\u05d6\u05b8\u05db\u05b7\u05e8\u05b0\u05ea\u05bc\u05b0"),
    "שאלת": ("\u05e9\u05c1\u05b8\u05d0\u05b7\u05dc\u05b0\u05ea\u05bc\u05b8", "\u05e9\u05c1\u05b8\u05d0\u05b7\u05dc\u05b0\u05ea\u05bc\u05b0"),
    "בדקת": ("\u05d1\u05b8\u05bc\u05d3\u05b7\u05e7\u05b0\u05ea\u05bc\u05b8", "\u05d1\u05b8\u05bc\u05d3\u05b7\u05e7\u05b0\u05ea\u05bc\u05b0"),
    "הגעת": ("\u05d4\u05b4\u05d2\u05bc\u05b7\u05e2\u05b0\u05ea\u05bc\u05b8", "\u05d4\u05b4\u05d2\u05bc\u05b7\u05e2\u05b0\u05ea\u05bc\u05b0"),
    "החלטת": ("\u05d4\u05b6\u05d7\u05b0\u05dc\u05b7\u05d8\u05b0\u05ea\u05bc\u05b8", "\u05d4\u05b6\u05d7\u05b0\u05dc\u05b7\u05d8\u05b0\u05ea\u05bc\u05b0"),
    # -ית endings: masculine adds a final qamats, feminine does not
    "ראית": ("\u05e8\u05b8\u05d0\u05b4\u05d9\u05ea\u05b8", "\u05e8\u05b8\u05d0\u05b4\u05d9\u05ea"),
    "ענית": ("\u05e2\u05b8\u05e0\u05b4\u05d9\u05ea\u05b8", "\u05e2\u05b8\u05e0\u05b4\u05d9\u05ea"),
    "עשית": ("\u05e2\u05b8\u05e9\u05c2\u05b4\u05d9\u05ea\u05b8", "\u05e2\u05b8\u05e9\u05c2\u05b4\u05d9\u05ea"),
    "ניסית": ("\u05e0\u05b4\u05e1\u05bc\u05b4\u05d9\u05ea\u05b8", "\u05e0\u05b4\u05e1\u05bc\u05b4\u05d9\u05ea"),
    "רצית": ("\u05e8\u05b8\u05e6\u05b4\u05d9\u05ea\u05b8", "\u05e8\u05b8\u05e6\u05b4\u05d9\u05ea"),
    "גילית": ("\u05d2\u05bc\u05b4\u05dc\u05bc\u05b4\u05d9\u05ea\u05b8", "\u05d2\u05bc\u05b4\u05dc\u05bc\u05b4\u05d9\u05ea"),
    "בנית": ("\u05d1\u05b8\u05bc\u05e0\u05b4\u05d9\u05ea\u05b8", "\u05d1\u05b8\u05bc\u05e0\u05b4\u05d9\u05ea"),
    "מצאת": ("\u05de\u05b8\u05e6\u05b8\u05d0\u05ea\u05b8", "\u05de\u05b8\u05e6\u05b8\u05d0\u05ea"),
    "קראת": ("\u05e7\u05b8\u05e8\u05b8\u05d0\u05ea\u05b8", "\u05e7\u05b8\u05e8\u05b8\u05d0\u05ea"),
}
_2P_PREFIXES = ("ו", "ש", "ה", "כ", "ל", "מ", "ב")
_2P_RE = re.compile(r"(?<![\w\u0590-\u05FF])([\u05d5\u05e9\u05d4\u05db\u05dc\u05de\u05d1]?)("
                    + "|".join(sorted(_SECOND_PERSON, key=len, reverse=True))
                    + r")(?![\w\u0590-\u05FF])")


def second_person_nikud(text: str, gender: str) -> str:
    """Vocalize the second-person forms that are spelled the same for both genders.
    gender: 'male' | 'female'. Anything else returns the text unchanged."""
    idx = {"male": 0, "female": 1}.get(str(gender or "").lower())
    if idx is None or not text:
        return text
    def sub(m):
        prefix, word = m.group(1), m.group(2)
        if prefix and prefix + word in _SECOND_PERSON:       # the prefixed form is a word of its own
            return _SECOND_PERSON[prefix + word][idx]
        return prefix + _SECOND_PERSON[word][idx]
    return _2P_RE.sub(sub, str(text))


def has_second_person(text: str) -> bool:
    return bool(_2P_RE.search(str(text or "")))
