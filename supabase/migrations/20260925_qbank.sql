-- IAKIDS: question bank ("data lake") by curriculum topic.  2026-09-25
--
-- Practice, exam-prep and gifted-familiarisation questions, each tied to a curriculum topic of a
-- grade and subject, with where it came from and under which licence (research 2026-09-25,
-- performance/../question-datalake): no Israeli official or commercial prep item is copied; items
-- are ORIGINAL (written by us, with or without a model) or ADAPTED from an open source whose
-- licence allows commercial reuse (class A: CC-BY, CC-BY-SA, CC0, MIT, Apache).
--
--   qbank_source       every source we read, with its licence and class (A usable / B inspiration only /
--                      C not usable). A class-C source can be recorded but never linked to an item.
--   curriculum_topics  topic codes per grade and subject, from the Ministry's curriculum documents
--                      (backend-ai-tutor-he/data/curriculum/*.json is the reviewed copy in the repo).
--   qbank_item         the items. review_status 'pending' until a person approves; only 'approved'
--                      items are ever served. Answers never leave the server (like the check banks).
--
-- Access: service role only (RLS on, no policies, browser grants revoked).
-- Idempotent: safe to paste more than once. Nothing existing is changed.

create table if not exists public.qbank_source (
    id              text        primary key,
    title           text        not null,
    url             text,
    licence         text        not null,
    licence_class   char(1)     not null check (licence_class in ('A', 'B', 'C')),
    attribution     text,
    notes           text,
    created_at      timestamptz not null default now()
);

create table if not exists public.curriculum_topics (
    code            text        primary key,
    subject         text        not null,
    grade           int         not null check (grade between 1 and 6),
    strand          text,
    title_he        text        not null,
    title_en        text,
    skills          jsonb       not null default '[]'::jsonb,
    meta            jsonb       not null default '{}'::jsonb,
    source_id       text        references public.qbank_source(id),
    source_ref      text,
    inferred        boolean     not null default false,
    updated_at      timestamptz not null default now()
);
create index if not exists curriculum_topics_subject_grade_idx on public.curriculum_topics (subject, grade);

create table if not exists public.qbank_item (
    id              text        primary key,
    topic_code      text        not null references public.curriculum_topics(code),
    subject         text        not null,
    grade           int         not null check (grade between 1 and 6),
    purpose         text        not null check (purpose in ('practice', 'exam_prep', 'gifted')),
    format          text        not null default 'mcq4' check (format in ('mcq4')),
    difficulty      int         not null check (difficulty between 1 and 3),
    language        text        not null default 'he',
    stimulus        text,
    stem            text        not null,
    options         jsonb       not null,
    answer          int         not null check (answer between 0 and 3),
    why_wrong       jsonb       not null,
    explain         text        not null,
    origin          text        not null check (origin in ('original_llm', 'original_human', 'adapted_open')),
    source_id       text        references public.qbank_source(id),
    source_item_ref text,
    licence_class   char(1)     not null default 'A' check (licence_class = 'A'),
    attribution     text,
    generator       jsonb       not null default '{}'::jsonb,
    verification    jsonb       not null default '{}'::jsonb,
    fingerprint     text        not null unique,
    review_status   text        not null default 'pending' check (review_status in ('pending', 'approved', 'rejected')),
    reviewer        text,
    review_note     text,
    reviewed_at     timestamptz,
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now(),
    -- an adapted item must name its (class A) source; an original item may not pretend to have one
    constraint qbank_item_origin_source check (
        (origin = 'adapted_open' and source_id is not null) or (origin <> 'adapted_open')
    )
);
create index if not exists qbank_item_lookup_idx on public.qbank_item (subject, grade, topic_code, review_status);

-- an item may only point at a class-A source (a CHECK cannot look at another table)
create or replace function public.qbank_item_source_is_open() returns trigger
language plpgsql as $$
begin
    if new.source_id is not null and
       (select licence_class from public.qbank_source where id = new.source_id) is distinct from 'A' then
        raise exception 'qbank_item %: source % is not class A (only open, commercially reusable sources may feed items)',
            new.id, new.source_id;
    end if;
    return new;
end $$;
drop trigger if exists qbank_item_source_is_open on public.qbank_item;
create trigger qbank_item_source_is_open before insert or update on public.qbank_item
    for each row execute function public.qbank_item_source_is_open();

alter table public.qbank_source      enable row level security;
alter table public.curriculum_topics enable row level security;
alter table public.qbank_item        enable row level security;
-- No policies on purpose: anon/authenticated get nothing, the service role bypasses RLS.
revoke all on public.qbank_source, public.curriculum_topics, public.qbank_item from anon, authenticated;
revoke all on function public.qbank_item_source_is_open() from anon, authenticated;
