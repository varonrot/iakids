-- Rollback for 20260927_03_eng_visual_review.sql. The check constraint can go; the column holds the review
-- decisions (approved images reach children only through it), so dropping it is left commented.
alter table public."2027_eng_lesson_visuals" drop constraint if exists "2027_eng_lesson_visuals_review_status_check";

-- DATA LOSS: alter table public."2027_eng_lesson_visuals" drop column if exists review_status;
