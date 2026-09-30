create table public."2027_eng_curriculum_lessons" (
 id uuid primary key default gen_random_uuid(),
 plan_id uuid not null references public."2027_eng_curriculum_plans"(id) on delete cascade,
 user_id uuid not null references auth.users(id) on delete cascade,
 child_id uuid not null,
 grade smallint not null check (grade between 1 and 6),
 content_key text not null,
 prompt_version integer not null,
 unit_index integer not null check (unit_index >= 0),
 lesson_index integer not null check (lesson_index >= 0),
 content jsonb not null,
 completed_at timestamptz,
 created_at timestamptz not null default now(),
 unique (plan_id, content_key, prompt_version, unit_index, lesson_index)
);
create index curriculum_lessons_2027_owner on public."2027_eng_curriculum_lessons"(user_id, child_id);
alter table public."2027_eng_curriculum_lessons" enable row level security;
revoke all on public."2027_eng_curriculum_lessons" from anon, authenticated;
grant select, insert, update, delete on public."2027_eng_curriculum_lessons" to service_role;
comment on table public."2027_eng_curriculum_lessons" is 'English curriculum lessons. Backend-only access verifies parent and child ownership. Content and narration are reused for an unchanged approved plan.';
