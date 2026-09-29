-- English Practice stores per-child attempts. The API grades and writes them.
create table if not exists public."2027_eng_practice_attempts" (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  child_id uuid not null references public.kids_profiles(id) on delete cascade,
  session_id uuid not null,
  pack_id text not null,
  question_key text not null,
  option_index smallint not null check (option_index between 0 and 3),
  is_correct boolean not null,
  answered_at timestamptz not null default now()
);
create index if not exists "2027_eng_practice_child_pack_idx"
  on public."2027_eng_practice_attempts" (child_id, pack_id, answered_at desc);
alter table public."2027_eng_practice_attempts" enable row level security;
revoke all on public."2027_eng_practice_attempts" from anon, authenticated;
grant select on public."2027_eng_practice_attempts" to authenticated;
create policy "2027_eng_practice_read_own_child" on public."2027_eng_practice_attempts"
  for select to authenticated using (
    user_id = (select auth.uid()) and exists (
      select 1 from public.kids_profiles k
      where k.id = child_id and k.user_id = (select auth.uid())
    )
  );
