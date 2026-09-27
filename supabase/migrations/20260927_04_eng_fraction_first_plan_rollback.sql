-- Rollback for 20260927_04_eng_fraction_first_plan.sql (the seeded first Grade 5 dividing-fractions plan).
-- Hides the plan from children (the routes serve only status = 'approved'); the row stays, because
-- children's progress rows reference it.
update public."2027_eng_lesson_plans" set status = 'draft'
 where language = 'en' and grade = 5 and subject = 'Math' and topic = 'Dividing fractions'
   and skill_id = 'division-as-groups' and prompt_version = 1;

-- DATA LOSS (fails while progress rows reference it): delete from public."2027_eng_lesson_plans" where skill_id = 'division-as-groups' and prompt_version = 1;
