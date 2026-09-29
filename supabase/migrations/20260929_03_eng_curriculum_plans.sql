-- English curriculum plans are independent of the Hebrew lesson hierarchy.
create table if not exists public."2027_eng_curriculum_plans" (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  child_id uuid not null references public.kids_profiles(id) on delete cascade,
  language text not null default 'en' check (language = 'en'),
  grade smallint not null check (grade between 1 and 6),
  subject text not null,
  topic text not null,
  request_text text not null default '',
  request_key text not null check (length(request_key) = 64),
  content jsonb not null check (jsonb_typeof(content) = 'object'),
  created_at timestamptz not null default now(),
  unique (child_id, request_key)
);
create index if not exists "2027_eng_curriculum_plans_recent_idx"
  on public."2027_eng_curriculum_plans" (child_id, created_at desc);
alter table public."2027_eng_curriculum_plans" enable row level security;
revoke all on public."2027_eng_curriculum_plans" from anon, authenticated;
grant select on public."2027_eng_curriculum_plans" to authenticated;
create policy "2027_eng_curriculum_read_own_child" on public."2027_eng_curriculum_plans"
  for select to authenticated using (
    user_id = (select auth.uid()) and exists (
      select 1 from public.kids_profiles k
      where k.id = child_id and k.user_id = (select auth.uid())
    )
  );
