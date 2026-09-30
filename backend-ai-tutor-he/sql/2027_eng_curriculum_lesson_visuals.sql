create table public."2027_eng_curriculum_lesson_visuals" (
 id uuid primary key default gen_random_uuid(),
 lesson_id uuid not null references public."2027_eng_curriculum_lessons"(id) on delete cascade,
 section_index smallint not null check(section_index between 0 and 6),
 prompt_version integer not null,
 content jsonb not null,
 image_path text,
 created_at timestamptz not null default now(),
 unique(lesson_id, section_index, prompt_version)
);
alter table public."2027_eng_curriculum_lesson_visuals" enable row level security;
revoke all on public."2027_eng_curriculum_lesson_visuals" from anon, authenticated;
grant select,insert,update,delete on public."2027_eng_curriculum_lesson_visuals" to service_role;
comment on table public."2027_eng_curriculum_lesson_visuals" is 'Saved English lesson diagram specifications and illustration paths. Backend-only access verifies lesson, parent, child and current approved plan.';
