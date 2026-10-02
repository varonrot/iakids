create table if not exists public."2027_media_cleanup_queue" (
 id uuid primary key default gen_random_uuid(),
 bucket_id text not null check (bucket_id in ('2027-eng-lesson-media','2027-eng-lesson-audio')),
 object_path text not null,
 status text not null default 'pending' check (status in ('pending','completed')),
 created_at timestamptz not null default now(), completed_at timestamptz,
 unique(bucket_id,object_path)
);
alter table public."2027_media_cleanup_queue" enable row level security;
revoke all on public."2027_media_cleanup_queue" from anon, authenticated;
grant all on public."2027_media_cleanup_queue" to service_role;
