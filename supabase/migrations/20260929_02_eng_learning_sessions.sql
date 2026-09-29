-- English My Learning System: parent-owned lesson conversations.
create table if not exists public."2027_eng_learning_sessions" (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  child_id uuid not null references public.kids_profiles(id) on delete cascade,
  language text not null default 'en' check (language = 'en'),
  grade smallint not null check (grade between 1 and 6),
  subject text not null,
  unit_id text not null,
  skill_id text not null,
  turns jsonb not null default '[]'::jsonb check (jsonb_typeof(turns) = 'array'),
  turn_count integer not null default 0 check (turn_count >= 0),
  started_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists "2027_eng_learning_child_recent_idx"
  on public."2027_eng_learning_sessions" (child_id, updated_at desc);
alter table public."2027_eng_learning_sessions" enable row level security;
revoke all on public."2027_eng_learning_sessions" from anon, authenticated;
grant select on public."2027_eng_learning_sessions" to authenticated;
create policy "2027_eng_learning_read_own_child" on public."2027_eng_learning_sessions"
  for select to authenticated using (
    user_id = (select auth.uid()) and exists (
      select 1 from public.kids_profiles k
      where k.id = child_id and k.user_id = (select auth.uid())
    )
  );
