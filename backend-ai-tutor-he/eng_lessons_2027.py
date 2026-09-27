"""English-only lesson contract. Imported by an API route; no Hebrew tutor changes."""

from __future__ import annotations

from copy import deepcopy

PHASES = ("see_the_idea", "try_together", "your_turn")
INTERACTIONS = {"continue", "multiple_choice"}
SUBJECT_GUIDES = {
    "Math": (
        "Teach one mathematical idea at a time. Begin with a concrete model, "
        "check every arithmetic claim, and give a short specific hint after a mistake. "
        "A three-question quick check is a low-confidence placement hint, not mastery."
    )
}
TOPIC_GUIDES = {
    "Dividing fractions": (
        "Teach division as how many equal groups fit. For this first micro-lesson, "
        "use 3/4 divided by 1/2 = 1 1/2. Show two quarters as one half and the "
        "remaining quarter as half of another half. Check equivalent parts before "
        "introducing any reciprocal shortcut. This is one lesson, not all of fractions."
    )
}


def teacher_messages(*, grade: int, subject: str, topic: str, language: str = "en") -> list[dict]:
    if language != "en" or not isinstance(grade, int) or not 1 <= grade <= 12:
        raise ValueError("An English lesson and a valid grade are required")
    if subject not in SUBJECT_GUIDES or topic not in TOPIC_GUIDES:
        raise ValueError("An approved subject and topic guide are required")
    return [
        {"role": "system", "content": (
            "You are a careful elementary teacher. Return structured JSON only. "
            "Write short English explanations for three steps: see_the_idea, "
            "try_together, your_turn. Choose Continue when a question is unnecessary. "
            "Questions must be multiple choice with two to four distinct options. "
            "Do not include child names, unapproved mathematical examples, or "
            "claims that a quick check establishes mastery."
        )},
        {"role": "developer", "content": (
            f"Subject guide: {SUBJECT_GUIDES[subject]} "
            f"Topic guide: {TOPIC_GUIDES[topic]}"
        )},
        {"role": "user", "content": (
            f"Prepare the first micro-lesson. Grade {grade}. Subject: {subject}. "
            f"Topic: {topic}. Language: {language}. "
            "Each step needs teacher_text, a visual brief or none, and an interaction. "
            "The answer_index must be a zero-based integer for multiple choice."
        )},
    ]


def validate_plan(plan: dict) -> None:
    if not isinstance(plan, dict) or plan.get("version") != 1:
        raise ValueError("Unsupported plan version")
    if not isinstance(plan.get("skill_id"), str) or not plan["skill_id"].strip():
        raise ValueError("Missing skill id")
    steps = plan.get("steps")
    if not isinstance(steps, list) or len(steps) != 3:
        raise ValueError("Exactly three short steps are required")
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or step.get("phase") != PHASES[index]:
            raise ValueError("Steps are out of order")
        if not isinstance(step.get("teacher_text"), str) or not step["teacher_text"].strip() or len(step["teacher_text"]) > 500:
            raise ValueError("A short explanation is required")
        visual = step.get("visual")
        if not isinstance(visual, dict) or visual.get("kind") not in {"none", "generated_image"}:
            raise ValueError("Invalid visual")
        if visual["kind"] == "generated_image" and (not isinstance(visual.get("brief"), str) or not visual["brief"].strip()):
            raise ValueError("A visual brief is required")
        action = step.get("interaction")
        if not isinstance(action, dict) or action.get("type") not in INTERACTIONS:
            raise ValueError("Unsupported interaction")
        if action["type"] == "multiple_choice":
            options = action.get("options")
            answer = action.get("answer_index")
            if (not isinstance(action.get("prompt"), str) or not action["prompt"].strip()
                    or not isinstance(options, list) or not 2 <= len(options) <= 4
                    or any(not isinstance(o, str) or not o.strip() for o in options)
                    or len(set(options)) != len(options)
                    or type(answer) is not int or not 0 <= answer < len(options)):
                raise ValueError("Invalid answer options")


def public_step(plan: dict, index: int, image_url: str | None = None) -> dict:
    """Only the active step reaches the browser; never send answer_index."""
    validate_plan(plan)
    if not isinstance(index, int) or index not in range(len(plan["steps"])):
        raise ValueError("Invalid step")
    step = deepcopy(plan["steps"][index])
    step["interaction"].pop("answer_index", None)
    step["interaction"].pop("hint", None)
    step["visual"].pop("brief", None)
    if image_url:
        step["visual"]["url"] = image_url
    return {"version": 1, "skill_id": plan["skill_id"], "step_index": index,
            "step_count": len(plan["steps"]), "step": step}


def check_answer(plan: dict, index: int, option_index: int | None = None) -> bool:
    """Grade against the server copy before advancing per-child progress."""
    validate_plan(plan)
    if not isinstance(index, int) or index not in range(len(plan["steps"])):
        raise ValueError("Invalid step")
    action = plan["steps"][index]["interaction"]
    if action["type"] == "continue":
        return option_index is None
    return type(option_index) is int and option_index == action["answer_index"]
