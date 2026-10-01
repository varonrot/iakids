create table public."2027_eng_test_prep_sessions" (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 child_id uuid not null,
 grade smallint not null check (grade between 1 and 6),
 mode text not null check (mode in ('topics','photo','file')),
 subject text not null default '', topic text not null default '',
 source_name text not null default '', source_text text not null default '',
 content jsonb, dialogue jsonb not null default '[]',
 answers jsonb not null default '{}',
 revision integer not null default 0 check (revision >= 0),
 approved_at timestamptz,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
create index on public."2027_eng_test_prep_sessions"(user_id, child_id, updated_at desc);
alter table public."2027_eng_test_prep_sessions" enable row level security;
revoke all on public."2027_eng_test_prep_sessions" from anon, authenticated;
grant all on public."2027_eng_test_prep_sessions" to service_role;
