create table public."2027_eng_curriculum_paragraph_cache" (
 cache_key text primary key,
 recipe_key text not null,
 grade smallint not null check(grade between 1 and 6),
 language text not null default 'en' check(language='en'),
 prompt_version integer not null,
 paragraph_version integer not null,
 content jsonb not null,
 created_at timestamptz not null default now()
);
create index eng_paragraph_recipe_2027 on public."2027_eng_curriculum_paragraph_cache"(recipe_key,prompt_version,paragraph_version,created_at);
alter table public."2027_eng_curriculum_paragraph_cache" enable row level security;
revoke all on public."2027_eng_curriculum_paragraph_cache" from anon,authenticated;
grant select,insert,update,delete on public."2027_eng_curriculum_paragraph_cache" to service_role;
create table public."2027_eng_curriculum_paragraph_visuals" (
 cache_key text primary key,
 grade smallint not null check(grade between 1 and 6),
 prompt_version integer not null,
 content jsonb not null,
 image_path text,
 created_at timestamptz not null default now()
);
alter table public."2027_eng_curriculum_paragraph_visuals" enable row level security;
revoke all on public."2027_eng_curriculum_paragraph_visuals" from anon,authenticated;
grant select,insert,update,delete on public."2027_eng_curriculum_paragraph_visuals" to service_role;
comment on table public."2027_eng_curriculum_paragraph_cache" is 'Reusable neutral English learning content only. No child profiles, chat, answer history or progress. Backend checks an owned approved curriculum before reuse.';
comment on table public."2027_eng_curriculum_paragraph_visuals" is 'Reusable paragraph-specific diagram specifications and generated image paths. Backend-only access through owned lessons.';
