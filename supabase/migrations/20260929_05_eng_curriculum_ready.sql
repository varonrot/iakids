alter table public."2027_eng_curriculum_plans"
  add column if not exists ready_at timestamptz;
