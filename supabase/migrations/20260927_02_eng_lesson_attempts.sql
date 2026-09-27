create table if not exists public."2027_eng_lesson_attempts" (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  child_id uuid not null references public.kids_profiles(id) on delete cascade,
  plan_id uuid not null references public."2027_eng_lesson_plans"(id),
  step_index smallint not null check (step_index between 0 and 2),
  option_index smallint not null check (option_index between 0 and 3),
  is_correct boolean not null,
  hint_used boolean not null default false,
  answered_at timestamptz not null default now()
);
create index if not exists "2027_eng_attempts_child_plan_idx"
  on public."2027_eng_lesson_attempts" (child_id, plan_id, answered_at desc);
alter table public."2027_eng_lesson_attempts" enable row level security;
revoke all on public."2027_eng_lesson_attempts" from anon, authenticated;
grant select on public."2027_eng_lesson_attempts" to authenticated;
create policy "2027_eng_attempts_read_own_child" on public."2027_eng_lesson_attempts"
  for select to authenticated using (
    user_id = (select auth.uid()) and exists (
      select 1 from public.kids_profiles k
      where k.id = child_id and k.user_id = (select auth.uid())
    )
  );
