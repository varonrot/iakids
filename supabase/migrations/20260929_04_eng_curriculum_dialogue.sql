-- Keep the English planning conversation and each previous plan for revision.
alter table public."2027_eng_curriculum_plans"
  add column if not exists dialogue jsonb not null default '[]'::jsonb
    check (jsonb_typeof(dialogue) = 'array'),
  add column if not exists revision integer not null default 0
    check (revision >= 0),
  add column if not exists plan_history jsonb not null default '[]'::jsonb
    check (jsonb_typeof(plan_history) = 'array'),
  add column if not exists updated_at timestamptz not null default now();

update public."2027_eng_curriculum_plans"
set dialogue = jsonb_build_array(jsonb_build_object(
  'role', 'assistant',
  'text', 'Your plan is ready. Tell me what you already know, ask for more practice questions, or tell me what you would like to change.'
))
where dialogue = '[]'::jsonb;
