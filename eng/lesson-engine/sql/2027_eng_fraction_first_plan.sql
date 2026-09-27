-- Reviewed first micro-lesson. The teacher generator can later publish a new
-- prompt_version after content review, without changing a child's old progress.
insert into public."2027_eng_lesson_plans"
  (language, grade, subject, topic, skill_id, prompt_version, status, content)
values (
  'en', 5, 'Math', 'Dividing fractions', 'division-as-groups', 1, 'approved',
  $$
  {
    "version": 1,
    "skill_id": "division-as-groups",
    "steps": [
      {
        "phase": "see_the_idea",
        "teacher_text": "Three quarters means three equal quarter pieces. Two quarters make one half. The last quarter is half of another half, so three quarters contains one and a half halves.",
        "visual": {"kind": "generated_image", "brief": "Two aligned fraction bars. First: three of four equal pieces shaded. Second: two quarters bracketed as one half; remaining quarter bracketed as half of another half. No text or numbers in artwork."},
        "interaction": {"type": "continue"}
      },
      {
        "phase": "try_together",
        "teacher_text": "Let's count the thirds in two thirds. Each of the two shaded pieces is one third.",
        "visual": {"kind": "generated_image", "brief": "A bar divided into three equal parts, first two colored. Clear empty third part. No text or numbers in artwork."},
        "interaction": {"type": "multiple_choice", "prompt": "How many one-third pieces fit into two thirds?", "options": ["1", "2", "3"], "answer_index": 1, "hint": "Count the two shaded one-third pieces."}
      },
      {
        "phase": "your_turn",
        "teacher_text": "Now use the same idea with quarters. One half is the same amount as two quarters.",
        "visual": {"kind": "none"},
        "interaction": {"type": "multiple_choice", "prompt": "How many quarters fit into one half?", "options": ["1", "2", "4"], "answer_index": 1, "hint": "Picture a half split into two equal quarters."}
      }
    ]
  }
  $$::jsonb
)
on conflict (language, grade, subject, topic, skill_id, prompt_version) do nothing;
