alter table public."2027_eng_lesson_visuals"
  add column if not exists review_status text not null default 'pending'
  check (review_status in ('pending', 'approved'));
