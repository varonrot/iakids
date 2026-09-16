#!/usr/bin/env python3
"""LIVE prompt check: every prompt really works against the real providers, in the three
configurations the product uses. Costs money (about $0.05-0.10 per configuration), so it is
NOT part of the free gate — run it after changing a prompt or a provider setting:

    cd backend-ai-tutor-he
    ../backend/.venv/bin/python tools/prompt_live_check.py                 # all three configurations
    ../backend/.venv/bin/python tools/prompt_live_check.py --config openrouter
    ../backend/.venv/bin/python tools/prompt_live_check.py --no-image     # skip the $0.034 hero image

Configurations (each runs in its own process because main.py reads the provider at import):
  openai      AI_PROVIDER=direct     TTS_PROVIDER=direct       text: OpenAI direct,  voice: Gemini direct
  openrouter  AI_PROVIDER=openrouter TTS_PROVIDER=openrouter   text: OpenRouter,     voice: OpenRouter
  gemini      (images + vision are always Gemini direct)       hero image + no-text check + TTS Gemini direct

Per prompt the check is: the model answers, the answer has the required shape, and the
rules we defined hold (neutral shared lesson, question immutable, feminine address for a
girl, greeting name, no text in the image, audio produced).
"""
import argparse, json, os, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
CONFIGS = {
    "openai":     {"AI_PROVIDER": "direct",     "TTS_PROVIDER": "direct"},
    "openrouter": {"AI_PROVIDER": "openrouter", "TTS_PROVIDER": "openrouter"},
    "gemini":     {"AI_PROVIDER": "direct",     "TTS_PROVIDER": "direct", "ONLY_GEMINI": "1"},
}

CHILD_CODE = r'''
import os, sys, json, time, re, io, contextlib
sys.path.insert(0, "."); os.chdir(".")
buf = io.StringIO()
with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
    import main, lesson_quality as lq
    from google.genai import types
ONLY_GEMINI = os.environ.get("ONLY_GEMINI") == "1"
NO_IMAGE = os.environ.get("NO_IMAGE") == "1"
results = []
def run(name, fn):
    t = time.perf_counter()
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            detail = fn()
        results.append({"prompt": name, "ok": True, "ms": round((time.perf_counter()-t)*1000), "detail": str(detail)[:90]})
    except Exception as e:
        results.append({"prompt": name, "ok": False, "ms": round((time.perf_counter()-t)*1000), "detail": f"{type(e).__name__}: {str(e)[:160]}"})

girl = {"id": "gate", "child_name": "נועה", "age": 5, "gender": "female", "avatar_key": "cat",
        "learning_interests": ["חיות"], "usage_goals": ["מדעים"]}
unit = {"id": 0, "unit_name": "מבוא לשרשרת המזון", "lesson_name": "מהי שרשרת מזון?",
        "learning_objective": "להבין מהי שרשרת מזון ומי אוכל את מי", "lesson_complexity": 2,
        "max_duration_seconds": 60, "lesson_parts_count": 2}
parent = {"id": 0, "grade": 5, "subject": "מדעים", "lesson_name": "שרשרת המזון"}
state = {}

if not ONLY_GEMINI:
    def teacher():
        c = main.client.beta.chat.completions.parse(
            model=main.UNIVERSAL_LESSON_MODEL,
            messages=[{"role": "system", "content": main.build_universal_unit_lesson_prompt(unit_lesson=unit, parent_lesson=parent)},
                      {"role": "user", "content": "צרו עכשיו שיעור קצר מאוד (עד 5 משפטים) ושאלה אחת. החזירו לפי מבנה התגובה."}],
            response_format=main.UniversalLessonResponse)
        d = c.choices[0].message.parsed
        assert d.explanation.strip() and d.question.strip(), "empty explanation/question"
        g = main.warn_if_gendered_lesson_text(d.explanation, "gate")
        assert not g, f"shared lesson addresses one child: {g}"
        state["expl"], state["q"] = d.explanation, d.question
        return f"{len(d.explanation)} chars, question ok, neutral"
    run("universal_unit_lesson (teacher)", teacher)

    def director():
        expl = state.get("expl") or "החגב אוכל עשב. הצפרדע אוכלת את החגב. כך עוברת אנרגיה מיצור ליצור."
        q = state.get("q") or "הסבירו מי אוכל את מי בשרשרת."
        import asyncio
        part, comp = asyncio.run(main.direct_lesson_part(explanation=expl, question=q, part_number=1, unit_lesson_id=0))
        segs = [s["text"] for s in part["lesson"]]
        assert segs, "no segments"
        assert part["question"]["text"] == q, "question was rewritten"
        assert not main.find_invalid_lesson_segments(segs, q, expl), "invalid segments"
        state["segs"] = segs
        return f"{len(segs)} segments, question immutable"
    run("lesson_director", director)

    def expansion():
        c = main.client.beta.chat.completions.parse(
            model=main.UNIVERSAL_LESSON_MODEL,
            messages=[{"role": "system", "content": main.build_lesson_expansion_prompt(unit_lesson=unit, parent_lesson=parent, part_number=2,
                        previous_parts=[{"part_number": 1, "explanation": state.get("expl", "x"), "question": state.get("q", "y")}])},
                      {"role": "user", "content": "Create a VERY short next lesson part now (max 4 sentences)."}],
            response_format=main.UniversalLessonResponse)
        d = c.choices[0].message.parsed
        assert d.explanation.strip() and d.question.strip()
        assert not main.warn_if_gendered_lesson_text(d.explanation, "gate"), "gendered"
        return f"{len(d.explanation)} chars, neutral"
    run("lesson_expansion", expansion)

    def visual_director():
        segs = state.get("segs") or ["החגב אוכל עשב.", "הצפרדע אוכלת את החגב."]
        sl = {"parts": [{"part_number": 1, "lesson": [{"text": s} for s in segs], "question": {"text": state.get("q", "?")}}]}
        prompt = main.build_visual_director_prompt(unit_lesson=unit, parent_lesson=parent, lesson_text="\n".join(segs), structured_lesson=sl)
        c = main.client.beta.chat.completions.parse(model=main.DEFAULT_OPENAI_MODEL,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "Create the visual plan."}],
            response_format=main.VisualDirectorResponse)
        d = c.choices[0].message.parsed.model_dump()
        items = [v for v in (d.get("visuals") or d.get("items") or d.get("plan") or []) ]
        assert items, f"no visuals in plan: {list(d.keys())}"
        gp = " ".join(lq.sanitize_generation_prompt(str(v.get("generation_prompt", ""))).split("No written text")[0] for v in items).lower()
        asks_text = re.findall(r"\b(labeled|labelled|caption|captions|with text|written words|the word \"|reads \"|sign that says)\b", gp)
        assert not asks_text, f"generation prompts ask for text/labels: {asks_text[:3]}"
        assert all(str(v.get("trigger_text", "")).strip() for v in items), "a visual has no trigger_text"
        state["gen_prompt"] = str(items[0].get("generation_prompt") or "")
        return f"{len(items)} visuals"
    run("visual_director", visual_director)

    def tutor_chat():
        c = main.client.chat.completions.create(model=main.DEFAULT_OPENAI_MODEL, temperature=0,
            messages=[{"role": "system", "content": main.build_tutor_prompt(girl, "")},
                      {"role": "user", "content": "היי, אני לא מבינה מה זה שרשרת מזון"}])
        t = c.choices[0].message.content or ""
        assert t.strip(), "empty"
        masc = re.findall(r"(?<![\w֐-׿])(אתה|תרצה|נסה|תחשוב|מוכן|יודע)(?![\w֐-׿])", t)
        assert not masc, f"masculine forms to a girl: {masc}"
        return f"{len(t)} chars, feminine ok"
    run("ai_tutor_system (chat, girl)", tutor_chat)

    def lesson_dialogue():
        p = main.build_structured_lesson_prompt(girl, {"id": 0, "lesson_name": "שרשרת המזון", "subject": "מדעים", "lesson_goal": "x"}, {}, "lesson")
        c = main.client.chat.completions.create(model=main.DEFAULT_OPENAI_MODEL, temperature=0,
            messages=[{"role": "system", "content": p}, {"role": "user", "content": "אני מוכנה להתחיל"}])
        t = c.choices[0].message.content or ""
        assert t.strip()
        masc = re.findall(r"(?<![\w֐-׿])(אתה|תרצה|נסה|תחשוב|מוכן|יודע)(?![\w֐-׿])", t)
        assert not masc, f"masculine forms to a girl: {masc}"
        return f"{len(t)} chars, feminine ok"
    run("structured_lesson (dialogue, girl)", lesson_dialogue)

    def curriculum():
        p = main.build_curriculum_builder_prompt(girl, None, {}, [{"role": "user", "content": "אני רוצה להוסיף שחמט"}])
        assert "{child_name}" not in p and "נועה" in p, "placeholders not filled"
        c = main.client.chat.completions.create(model=main.DEFAULT_OPENAI_MODEL, temperature=0,
            messages=[{"role": "system", "content": p}, {"role": "user", "content": "אני רוצה להוסיף שחמט"}])
        assert (c.choices[0].message.content or "").strip()
        return "answered, placeholders filled"
    run("curriculum_builder", curriculum)

    def nikud():
        out = main.vocalize_for_tts("הצמח גדל במדבר.")
        assert "ִ" in out or "ּ" in out, f"no nikud added: {out}"
        return out
    run("tts nikud (gpt-4o-mini)", nikud)

# voice (provider per TTS_PROVIDER) — always
def tts():
    wav, dur = main.generate_tts_wav_bytes("היי נועה! כיף שבאת ללמוד איתי. הזחל אכל עלה ← ואז עלה על הענף. 5 × 3 = 15.")
    assert len(wav) > 5000 and dur > 1, "no audio"
    return f"{dur:.1f}s audio via {main.TTS_PROVIDER}"
run(f"tts_style_prefix ({main.TTS_PROVIDER})", tts)

if ONLY_GEMINI:
    def vision():
        img = main.sb.storage.from_("lesson-media").download("unit_lessons/29/v1/part_1/visual_1.png")
        r = lq.image_text_check(main.gemini_client, types, main.IMAGE_TEXT_CHECK_MODEL, img, "image/png")
        return f"has_text={r['has_text']} {r['text'][:30]!r}"
    run("image_text_check (vision)", vision)
    if not NO_IMAGE:
        def hero():
            prompt = main.build_lesson_hero_image_prompt(unit_lesson=unit, parent_lesson=parent)
            img, mime = main.generate_lesson_hero_image_bytes(prompt)
            first = lq.image_text_check(main.gemini_client, types, main.IMAGE_TEXT_CHECK_MODEL, img, mime)
            # production path: one strict retry when text is found
            img, mime = main.ensure_no_text_in_image(img, mime, "hero", lambda extra: main.generate_lesson_hero_image_bytes(prompt + extra), unit_lesson_id=0)
            final = lq.image_text_check(main.gemini_client, types, main.IMAGE_TEXT_CHECK_MODEL, img, mime)
            assert len(img) > 10000, "no image"
            assert not final["has_text"], f"text in hero even after retry: {final['text']!r}"
            return f"{len(img)//1024} KB, no text" + (" (first attempt had text, retry fixed it)" if first["has_text"] else "")
        run("hero_image_prompt (gemini image)", hero)

print("RESULTS_JSON " + json.dumps(results, ensure_ascii=False))
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", action="append", choices=list(CONFIGS), help="default: all three")
    ap.add_argument("--no-image", action="store_true")
    a = ap.parse_args()
    py = str(HERE.parent / "backend" / ".venv" / "bin" / "python")
    all_ok = True
    for name in (a.config or list(CONFIGS)):
        env = dict(os.environ, APP_ENV="prod", **CONFIGS[name])
        env["ONLY_GEMINI"] = CONFIGS[name].get("ONLY_GEMINI", "0")
        if a.no_image:
            env["NO_IMAGE"] = "1"
        t = time.time()
        r = subprocess.run([py, "-c", CHILD_CODE], cwd=HERE, env=env, capture_output=True, text=True, timeout=900)
        line = next((l for l in r.stdout.splitlines() if "RESULTS_JSON" in l), None)
        print(f"\n=== configuration: {name}  ({time.time()-t:.0f}s)")
        if not line:
            all_ok = False
            print("  CRASHED:", (r.stderr or r.stdout)[-600:])
            continue
        for row in json.loads(line.split("RESULTS_JSON ", 1)[1]):
            all_ok &= row["ok"]
            print(f"  {'ok  ' if row['ok'] else 'FAIL'} {row['prompt']:<40} {row['ms']:>6} ms  {row['detail']}")
    print("\nLIVE PROMPT CHECK:", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
