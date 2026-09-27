-- English lesson engine. Shared teaching plans never contain child data.
-- The browser cannot read plans or answer keys; only the API service role can.
create table if not exists public."2027_eng_lesson_plans" (
  id uuid primary key default gen_random_uuid(),
  language text not null check (language = 'en'),
  grade smallint not null check (grade between 1 and 12),
  subject text not null,
  topic text not null,
  skill_id text not null,
  prompt_version integer not null check (prompt_version > 0),
  status text not null default 'draft' check (status in ('draft', 'approved')),
  content jsonb not null check (jsonb_typeof(content) = 'object'),
  created_at timestamptz not null default now(),
  unique (language, grade, subject, topic, skill_id, prompt_version)
);
alter table public."2027_eng_lesson_plans" enable row level security;
revoke all on public."2027_eng_lesson_plans" from anon, authenticated;

-- A private object path is reused by everyone taking the same approved step.
create table if not exists public."2027_eng_lesson_visuals" (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid not null references public."2027_eng_lesson_plans"(id) on delete cascade,
  step_index smallint not null check (step_index between 0 and 2),
  storage_path text not null,
  alt_text text not null,
  generation_version integer not null check (generation_version > 0),
  created_at timestamptz not null default now(),
  unique (plan_id, step_index, generation_version),
  unique (storage_path)
);
alter table public."2027_eng_lesson_visuals" enable row level security;
revoke all on public."2027_eng_lesson_visuals" from anon, authenticated;

-- This is per-child activity, separate from reusable lesson material.
create table if not exists public."2027_eng_lesson_progress" (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  child_id uuid not null references public.kids_profiles(id) on delete cascade,
  plan_id uuid not null references public."2027_eng_lesson_plans"(id),
  current_step smallint not null default 0 check (current_step between 0 and 3),
  completed_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (child_id, plan_id)
);
create index if not exists "2027_eng_progress_owner_idx"
  on public."2027_eng_lesson_progress" (user_id, child_id);
alter table public."2027_eng_lesson_progress" enable row level security;
create policy "2027_eng_progress_read_own_child" on public."2027_eng_lesson_progress"
  for select to authenticated using (
    user_id = (select auth.uid()) and exists (
      select 1 from public.kids_profiles k
      where k.id = child_id and k.user_id = (select auth.uid())
    )
  );
-- Only the server writes a completed step after validating the child's answer.
revoke insert, update, delete on public."2027_eng_lesson_progress" from anon, authenticated;
grant select on public."2027_eng_lesson_progress" to authenticated;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('2027-eng-lesson-media', '2027-eng-lesson-media', false, 5242880,
        array['image/png', 'image/jpeg', 'image/webp'])
on conflict (id) do nothing;
-- No client storage policies: the server signs a URL for an authenticated child.
