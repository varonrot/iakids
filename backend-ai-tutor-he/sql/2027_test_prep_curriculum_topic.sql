alter table public."2027_eng_test_prep_sessions" add column if not exists curriculum_topic_id text references public."2027_curriculum_map"(id);
