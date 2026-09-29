"""Short, reviewed English practice packs. Answers stay on the server."""

from uuid import UUID

from fastapi import Header, HTTPException
from pydantic import Field
from starlette.concurrency import run_in_threadpool

from main import LimitedRequest, app, authenticate_user, get_child_by_id, sb


def question(key, prompt, options, answer, explanation):
    assert len(options) == 4 and 0 <= answer < 4
    return {"key": key, "prompt": prompt, "options": options,
            "answer_index": answer, "explanation": explanation}


PACKS = {
    "g1-number-sense": (1, "Number sense", [
        question("add", "What is 7 + 5?", ["10", "11", "12", "13"], 2, "Seven and five make twelve."),
        question("compare", "Which number is greater?", ["28", "38", "18", "8"], 1, "Thirty-eight has three tens, more than the others."),
        question("tens", "What is 10 + 10?", ["2", "10", "20", "100"], 2, "Two groups of ten make twenty."),
    ]),
    "g2-place-value": (2, "Place value and sums", [
        question("tens", "How many tens are in 430?", ["3", "4", "43", "430"], 2, "Four hundred thirty is forty-three tens."),
        question("add", "What is 46 + 27?", ["63", "73", "74", "83"], 1, "Six plus seven is thirteen; carry one ten to get seventy-three."),
        question("subtract", "What is 100 − 35?", ["55", "65", "75", "85"], 1, "One hundred minus thirty-five is sixty-five."),
    ]),
    "g3-multiply": (3, "Multiply and divide", [
        question("six-four", "What is 6 × 4?", ["10", "20", "24", "28"], 2, "Six groups of four make twenty-four."),
        question("thirty-six", "What is 36 ÷ 6?", ["5", "6", "7", "9"], 1, "Six groups of six make thirty-six."),
        question("seven-eight", "What is 7 × 8?", ["48", "54", "56", "64"], 2, "Seven groups of eight make fifty-six."),
    ]),
    "g4-equivalent": (4, "Equivalent fractions", [
        question("half", "Which fraction equals 1/2?", ["1/4", "2/4", "3/4", "2/3"], 1, "Two of four equal parts are one half."),
        question("three-sixths", "What is 3/6 in simplest form?", ["1/3", "1/2", "2/3", "3/4"], 1, "Divide the top and bottom by three: 3/6 = 1/2."),
        question("two-thirds", "Which fraction equals 2/3?", ["2/6", "3/6", "4/6", "5/6"], 2, "Multiply the top and bottom by two: 2/3 = 4/6."),
    ]),
    "g5-dividing-fractions": (5, "Dividing fractions", [
        question("three-quarters", "How many halves fit into 3/4?", ["1", "1½", "2", "3"], 1, "Two quarters make one half. The extra quarter is half of another half: 1½."),
        question("two-thirds", "How many one-third groups fit into 2/3?", ["1", "2", "3", "4"], 1, "Two one-third groups make two thirds."),
        question("half-quarters", "How many quarters fit into 1/2?", ["1", "2", "3", "4"], 1, "A half contains two quarters."),
    ]),
    "g5-percentages": (5, "Percentages", [
        question("twenty-five", "25 out of 100 is what percent?", ["5%", "20%", "25%", "50%"], 2, "Percent means out of one hundred, so 25 out of 100 is 25%."),
        question("half-twenty", "What is 50% of 20?", ["5", "10", "15", "20"], 1, "Fifty percent is one half; half of twenty is ten."),
        question("quarter", "What percent is one quarter?", ["10%", "20%", "25%", "40%"], 2, "One quarter is 25 out of 100, or 25%."),
    ]),
    "g6-ratios": (6, "Ratios", [
        question("red-blue", "There are 2 red and 3 blue marbles. What is the red-to-blue ratio?", ["2:3", "3:2", "2:5", "5:3"], 0, "Red to blue compares two red marbles with three blue marbles: 2:3."),
        question("simplify", "What is the simplest form of the ratio 12:6?", ["1:2", "2:1", "3:1", "6:1"], 1, "Divide both parts by six to get 2:1."),
        question("total", "A red-to-blue ratio is 3:1. If there are 12 marbles, how many are red?", ["3", "6", "9", "12"], 2, "Four equal parts make twelve, so each part is three. Red takes three parts: nine."),
    ]),
}


class StartPractice(LimitedRequest):
    kid_id: str
    pack_id: str | None = Field(default=None, max_length=50)


class AnswerPractice(LimitedRequest):
    kid_id: str
    pack_id: str = Field(max_length=50)
    session_id: UUID
    question_key: str = Field(max_length=50)
    option_index: int = Field(ge=0, le=3)


def _learner(authorization, kid_id):
    user = authenticate_user(authorization)
    child = get_child_by_id(str(user.id), kid_id)
    grade = int(child.get("age") or 0)
    if grade not in range(1, 7):
        raise HTTPException(status_code=409, detail="Choose a learner in Grades 1–6.")
    return str(user.id), child, grade


def _public_pack(pack_id, pack):
    grade, title, questions = pack
    return {"id": pack_id, "grade": grade, "subject": "Math", "title": title,
            "questions": [{"key": q["key"], "prompt": q["prompt"], "options": q["options"]}
                          for q in questions]}


@app.post("/api/eng/practice/start")
async def start_practice(body: StartPractice, authorization: str = Header(None)):
    _, child, grade = await run_in_threadpool(_learner, authorization, body.kid_id)
    available = {key: value for key, value in PACKS.items() if value[0] == grade}
    if body.pack_id and body.pack_id not in available:
        raise HTTPException(status_code=422, detail="Choose a practice set for this learner’s grade.")
    return {"learner": child["child_name"], "grade": grade,
            "packs": [{"id": key, "title": value[1], "subject": "Math"} for key, value in available.items()],
            "pack": _public_pack(body.pack_id, available[body.pack_id]) if body.pack_id else None}


def _grade_answer(user_id, body: AnswerPractice, grade: int):
    pack = PACKS.get(body.pack_id)
    if not pack or pack[0] != grade:
        raise HTTPException(status_code=422, detail="This practice set does not match the learner.")
    item = next((q for q in pack[2] if q["key"] == body.question_key), None)
    if not item:
        raise HTTPException(status_code=422, detail="This question is not in the practice set.")
    correct = body.option_index == item["answer_index"]
    sb.table("2027_eng_practice_attempts").insert({
        "user_id": user_id, "child_id": body.kid_id, "session_id": str(body.session_id),
        "pack_id": body.pack_id, "question_key": body.question_key,
        "option_index": body.option_index, "is_correct": correct
    }).execute()
    return {"correct": correct, "correct_index": item["answer_index"],
            "explanation": item["explanation"]}


@app.post("/api/eng/practice/answer")
async def answer_practice(body: AnswerPractice, authorization: str = Header(None)):
    user_id, _, grade = await run_in_threadpool(_learner, authorization, body.kid_id)
    return await run_in_threadpool(_grade_answer, user_id, body, grade)
